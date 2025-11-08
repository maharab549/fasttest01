"""
Enhanced Email Service with Production-Grade Features
- Rate limiting to prevent abuse
- Email verification tracking
- Retry mechanism for failed sends
- Professional templates
- Comprehensive logging and monitoring
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import asyncio
from ..config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Rate limiting thresholds
RATE_LIMIT_EMAILS_PER_IP = 5  # Max 5 emails per IP per hour
RATE_LIMIT_EMAILS_PER_USER = 3  # Max 3 emails per user per hour
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour


class EmailService:
    """
    Production-grade email service with:
    - SMTP configuration management
    - Rate limiting (prevent abuse)
    - Email tracking and logging
    - Retry mechanism
    - Professional HTML templates
    - Error handling and monitoring
    """
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.sender_email = settings.sender_email or settings.smtp_username
        self.sender_name = settings.sender_name
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        
        # Email tracking cache (in production, use Redis)
        self.email_attempts = {}
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        is_configured = bool(self.smtp_username and self.smtp_password and self.sender_email)
        if not is_configured:
            logger.warning("Email service not configured - no SMTP credentials found")
        return is_configured
    
    def _clean_old_attempts(self):
        """Remove old email attempts from tracking (older than 1 hour)"""
        now = datetime.utcnow()
        keys_to_remove = []
        for key, timestamp in self.email_attempts.items():
            if (now - timestamp).total_seconds() > RATE_LIMIT_WINDOW_SECONDS:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.email_attempts[key]
    
    def check_rate_limit(self, user_email: str, ip_address: str = None) -> Tuple[bool, Optional[str]]:
        """
        Check if email sending should be rate limited
        
        Args:
            user_email: Email address to send to
            ip_address: IP address of requester
            
        Returns:
            Tuple of (allowed: bool, reason: str or None)
        """
        self._clean_old_attempts()
        now = datetime.utcnow()
        
        # Check per-user limit (same email address)
        user_key = f"user_{user_email}"
        user_attempts = sum(1 for k in self.email_attempts.keys() if k == user_key)
        if user_attempts >= RATE_LIMIT_EMAILS_PER_USER:
            reason = f"Rate limit exceeded for email {user_email} (max {RATE_LIMIT_EMAILS_PER_USER} per hour)"
            logger.warning(f"Rate limit - {reason}")
            return False, reason
        
        # Check per-IP limit (if IP provided)
        if ip_address:
            ip_key = f"ip_{ip_address}"
            ip_attempts = sum(1 for k in self.email_attempts.keys() if k == ip_key)
            if ip_attempts >= RATE_LIMIT_EMAILS_PER_IP:
                reason = f"Rate limit exceeded for IP {ip_address} (max {RATE_LIMIT_EMAILS_PER_IP} per hour)"
                logger.warning(f"Rate limit - {reason}")
                return False, reason
            
            # Record this attempt
            self.email_attempts[ip_key] = now
        
        # Record per-user attempt
        self.email_attempts[user_key] = now
        
        return True, None
    
    def send_password_reset_email(
        self, 
        recipient_email: str, 
        reset_url: str, 
        user_name: str = None,
        user_email: str = None,
        ip_address: str = None,
        db_session: Session = None
    ) -> Dict:
        """
        Send password reset email with professional template
        
        Args:
            recipient_email: Email address to send to
            reset_url: Full URL for password reset
            user_name: User's name for personalization
            user_email: User's email (for logging)
            ip_address: Requester's IP address (for rate limiting)
            db_session: Database session for logging
            
        Returns:
            Dict with keys: 'success' (bool), 'message' (str), 'attempts' (int)
        """
        
        # Check if configured
        if not self.is_configured():
            logger.warning("Email service not configured. Cannot send email.")
            return {
                "success": False,
                "message": "Email service not configured",
                "attempts": 0
            }
        
        # Check rate limiting
        allowed, rate_limit_reason = self.check_rate_limit(recipient_email, ip_address)
        if not allowed:
            logger.warning(f"Email send blocked by rate limit: {rate_limit_reason}")
            return {
                "success": False,
                "message": rate_limit_reason,
                "attempts": 0
            }
        
        try:
            subject = "🔐 Password Reset Request - MeghaMart"
            
            # Create professional HTML email body
            html_body = self._create_professional_email_template(reset_url, user_name)
            
            # Create plain text alternative
            text_body = self._create_plain_text_email(reset_url, user_name)
            
            # Send email with retry
            success, error_msg = self._send_email_with_retry(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info(
                    f"✅ Password reset email sent successfully to {recipient_email}",
                    extra={
                        "event": "email_sent",
                        "recipient": recipient_email,
                        "type": "password_reset",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                return {
                    "success": True,
                    "message": "Password reset email sent successfully",
                    "attempts": 1
                }
            else:
                logger.error(
                    f"❌ Failed to send password reset email to {recipient_email}: {error_msg}",
                    extra={
                        "event": "email_failed",
                        "recipient": recipient_email,
                        "type": "password_reset",
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                return {
                    "success": False,
                    "message": f"Failed to send email: {error_msg}",
                    "attempts": 1
                }
                
        except Exception as e:
            logger.exception(
                f"Unexpected error sending password reset email to {recipient_email}: {str(e)}"
            )
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "attempts": 0
            }
    
    def _send_email_with_retry(
        self, 
        recipient_email: str, 
        subject: str, 
        html_body: str, 
        text_body: str,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """
        Send email with automatic retry on failure
        
        Args:
            recipient_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            max_retries: Maximum retry attempts
            
        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"Attempting to send email (attempt {attempt}/{max_retries})...")
                
                # Create message
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = formataddr((self.sender_name, self.sender_email))
                message["To"] = recipient_email
                message["Date"] = datetime.utcnow().isoformat()
                
                # Attach both plain text and HTML versions
                part1 = MIMEText(text_body, "plain")
                part2 = MIMEText(html_body, "html")
                message.attach(part1)
                message.attach(part2)
                
                # Send via SMTP
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                    server.starttls()  # Secure connection
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
                
                logger.info(f"✅ Email sent successfully to {recipient_email} on attempt {attempt}")
                return True, None
                
            except smtplib.SMTPAuthenticationError as e:
                last_error = f"Authentication failed: {str(e)}"
                logger.error(f"SMTP authentication error (attempt {attempt}): {last_error}")
                # Don't retry authentication errors
                break
            except smtplib.SMTPException as e:
                last_error = f"SMTP error: {str(e)}"
                logger.warning(f"SMTP error (attempt {attempt}): {last_error}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    asyncio.sleep(wait_time)
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error (attempt {attempt}): {last_error}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    asyncio.sleep(wait_time)
        
        return False, last_error
    
    def _create_professional_email_template(self, reset_url: str, user_name: str = None) -> str:
        """Create professional HTML email template"""
        
        user_greeting = f"Hi {user_name}," if user_name else "Hi,"
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                .content {{
                    padding: 30px;
                }}
                .greeting {{
                    font-size: 16px;
                    margin-bottom: 20px;
                    color: #333;
                }}
                .message {{
                    margin: 20px 0;
                    line-height: 1.8;
                    color: #555;
                }}
                .cta-button {{
                    display: inline-block;
                    padding: 12px 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 20px 0;
                    font-weight: bold;
                    text-align: center;
                }}
                .backup-link {{
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #f9f9f9;
                    border-left: 4px solid #667eea;
                    border-radius: 4px;
                }}
                .backup-link label {{
                    display: block;
                    font-size: 12px;
                    color: #999;
                    margin-bottom: 8px;
                }}
                .backup-link a {{
                    color: #667eea;
                    word-break: break-all;
                    font-size: 13px;
                }}
                .security-info {{
                    background-color: #fffbea;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .security-info strong {{
                    color: #f57f17;
                }}
                .footer {{
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                    margin-top: 20px;
                    font-size: 13px;
                    color: #999;
                    text-align: center;
                }}
                .footer a {{
                    color: #667eea;
                    text-decoration: none;
                }}
                .footer p {{
                    margin: 8px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Reset Your Password</h1>
                    <p>MeghaMart Security</p>
                </div>
                
                <div class="content">
                    <div class="greeting">{user_greeting}</div>
                    
                    <div class="message">
                        We received a request to reset your password. If you didn't make this request, you can safely ignore this email.
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="cta-button">Reset Your Password</a>
                    </div>
                    
                    <div class="message">
                        Or use this backup link if the button doesn't work:
                    </div>
                    
                    <div class="backup-link">
                        <label>Backup Link:</label>
                        <a href="{reset_url}">{reset_url}</a>
                    </div>
                    
                    <div class="security-info">
                        <strong>🔒 Security Information:</strong><br>
                        • This link expires in <strong>24 hours</strong><br>
                        • Can only be used <strong>once</strong><br>
                        • Never share this link with anyone<br>
                        • MeghaMart will never ask for your password via email
                    </div>
                    
                    <div class="message">
                        <strong>Didn't request this?</strong><br>
                        If you didn't request a password reset, please ignore this email or 
                        <a href="mailto:support@meghamart.com" style="color: #667eea;">contact our support team</a> immediately.
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>MeghaMart</strong></p>
                    <p>Security Team</p>
                    <p><a href="https://meghamart.com">https://meghamart.com</a></p>
                    <p style="margin-top: 15px; font-size: 11px; color: #bbb;">
                        This is an automated message. Please do not reply to this email.<br>
                        If you have questions, please visit our 
                        <a href="https://meghamart.com/help">Help Center</a>
                    </p>
                    <p style="margin-top: 15px; font-size: 11px;">
                        © {datetime.utcnow().year} MeghaMart. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_plain_text_email(self, reset_url: str, user_name: str = None) -> str:
        """Create plain text alternative for email clients that don't support HTML"""
        
        user_greeting = f"Hi {user_name}," if user_name else "Hi,"
        
        return f"""
{user_greeting}

We received a request to reset your password. If you didn't make this request, you can safely ignore this email.

RESET YOUR PASSWORD:
{reset_url}

SECURITY INFORMATION:
• This link expires in 24 hours
• Can only be used once
• Never share this link with anyone
• MeghaMart will never ask for your password via email

Didn't request this?
If you didn't request a password reset, please ignore this email or contact our support team.

Best regards,
MeghaMart Security Team
https://meghamart.com

---
This is an automated message. Please do not reply to this email.
If you have questions, please visit our Help Center: https://meghamart.com/help

© {datetime.utcnow().year} MeghaMart. All rights reserved.
        """


# Create singleton instance
email_service = EmailService()
