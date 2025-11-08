"""
Email service for sending password reset emails and other notifications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.sender_email = settings.sender_email or settings.smtp_username
        self.sender_name = settings.sender_name
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_username and self.smtp_password and self.sender_email)
    
    def send_password_reset_email(self, recipient_email: str, reset_url: str, user_name: str = None) -> bool:
        """
        Send password reset email to user
        
        Args:
            recipient_email: Email address to send to
            reset_url: Full URL for password reset
            user_name: User's name for personalization
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email service not configured. Skipping email send.")
            return False
        
        try:
            subject = "Password Reset Request - MeghaMart"
            
            # Create HTML email body
            html_body = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 0;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background-color: #ffffff;
                            border-radius: 8px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            overflow: hidden;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 30px 20px;
                            text-align: center;
                        }}
                        .header h1 {{
                            margin: 0;
                            font-size: 24px;
                        }}
                        .content {{
                            padding: 30px 20px;
                        }}
                        .greeting {{
                            font-size: 16px;
                            color: #333;
                            margin-bottom: 20px;
                        }}
                        .message {{
                            font-size: 14px;
                            color: #666;
                            line-height: 1.6;
                            margin-bottom: 20px;
                        }}
                        .button-container {{
                            text-align: center;
                            margin: 30px 0;
                        }}
                        .reset-button {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 12px 30px;
                            text-decoration: none;
                            border-radius: 5px;
                            display: inline-block;
                            font-weight: bold;
                            transition: transform 0.3s ease;
                        }}
                        .reset-button:hover {{
                            transform: scale(1.05);
                        }}
                        .link-container {{
                            background-color: #f9f9f9;
                            padding: 15px;
                            border-radius: 5px;
                            margin: 20px 0;
                            word-break: break-all;
                        }}
                        .link {{
                            font-size: 12px;
                            color: #0066cc;
                            font-family: monospace;
                        }}
                        .warning {{
                            background-color: #fff3cd;
                            border: 1px solid #ffc107;
                            color: #856404;
                            padding: 12px;
                            border-radius: 5px;
                            margin: 20px 0;
                            font-size: 13px;
                        }}
                        .footer {{
                            background-color: #f5f5f5;
                            padding: 20px;
                            text-align: center;
                            font-size: 12px;
                            color: #999;
                            border-top: 1px solid #eee;
                        }}
                        .social-links {{
                            margin: 10px 0;
                        }}
                        .social-links a {{
                            color: #667eea;
                            text-decoration: none;
                            margin: 0 10px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🔐 Password Reset Request</h1>
                        </div>
                        
                        <div class="content">
                            <div class="greeting">
                                Hi {user_name or 'there'},
                            </div>
                            
                            <div class="message">
                                We received a request to reset your password for your MeghaMart account. 
                                If you didn't make this request, you can ignore this email and your password will remain unchanged.
                            </div>
                            
                            <div class="button-container">
                                <a href="{reset_url}" class="reset-button">
                                    Reset Your Password
                                </a>
                            </div>
                            
                            <div class="message">
                                Or copy and paste this link in your browser:
                            </div>
                            
                            <div class="link-container">
                                <div class="link">{reset_url}</div>
                            </div>
                            
                            <div class="warning">
                                ⏰ <strong>Important:</strong> This reset link will expire in 24 hours for security reasons. 
                                If the link expires, you can request a new one.
                            </div>
                            
                            <div class="message">
                                <strong>Need help?</strong> Contact our support team at support@meghamart.com
                            </div>
                        </div>
                        
                        <div class="footer">
                            <p>© 2025 MeghaMart. All rights reserved.</p>
                            <div class="social-links">
                                <a href="https://meghamart.com">Website</a> | 
                                <a href="mailto:support@meghamart.com">Support</a>
                            </div>
                            <p style="margin-top: 10px; color: #ccc;">
                                This is an automated message. Please do not reply to this email.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Create plain text fallback
            text_body = f"""
Password Reset Request

Hi {user_name or 'there'},

We received a request to reset your password for your MeghaMart account.
If you didn't make this request, you can ignore this email and your password will remain unchanged.

To reset your password, click the link below:
{reset_url}

This link will expire in 24 hours for security reasons.

Need help? Contact our support team at support@meghamart.com

© 2025 MeghaMart. All rights reserved.
"""
            
            # Send email
            return self._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {recipient_email}: {str(e)}")
            return False
    
    def _send_email(self, recipient_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Internal method to send email via SMTP
        
        Args:
            recipient_email: Recipient's email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = formataddr((self.sender_name, self.sender_email))
            message["To"] = recipient_email
            
            # Attach plain text and HTML parts
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Password reset email sent successfully to {recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check your email and password.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False


# Create a singleton instance
email_service = EmailService()
