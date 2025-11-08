# 📧 Email Configuration Setup Guide

## Overview
This guide shows you how to set up email sending for password reset notifications instead of just logging to console.

---

## Option 1: Gmail SMTP (Recommended for Development)

### Step 1: Enable 2-Factor Authentication on Gmail
1. Go to https://myaccount.google.com/
2. Click "Security" in the left menu
3. Scroll down to "2-Step Verification"
4. Click "Get Started" and follow the steps
5. Verify with your phone

### Step 2: Generate App Password
1. After 2FA is enabled, go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your OS)
3. Click "Generate"
4. Google will show you a 16-character password
5. **Copy this password** (you'll need it)

### Step 3: Update .env File

Create or update `.env` in your backend folder:

```bash
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=MeghaMart
```

**Example**:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=maharab549@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SENDER_EMAIL=maharab549@gmail.com
SENDER_NAME=MeghaMart
```

### Step 4: Install Email Dependencies
```bash
cd backend
pip install -r requirements.txt
```

Or manually install:
```bash
pip install aiosmtplib
```

### Step 5: Restart Backend
```bash
python -m uvicorn app.main:app --reload
```

---

## Option 2: Outlook/Hotmail SMTP

### Configuration

Update `.env`:
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SENDER_EMAIL=your-email@outlook.com
SENDER_NAME=MeghaMart
```

---

## Option 3: SendGrid (Best for Production)

### Step 1: Create SendGrid Account
1. Go to https://sendgrid.com/
2. Sign up for free account
3. Verify your email

### Step 2: Create API Key
1. Go to Settings → API Keys
2. Click "Create API Key"
3. Name it "MeghaMart"
4. Copy the key

### Step 3: Setup in Code
We'll need to modify the email service for SendGrid. For now, use SMTP above.

---

## Option 4: Mailtrap (Testing Only)

### Step 1: Create Mailtrap Account
1. Go to https://mailtrap.io/
2. Sign up (free tier available)
3. Create a new inbox

### Step 2: Get SMTP Credentials
1. Click on inbox
2. Go to "Integrations" → "SMTP"
3. Copy the SMTP settings

### Step 3: Update .env
```bash
SMTP_SERVER=live.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USERNAME=api
SMTP_PASSWORD=your-mailtrap-key
SENDER_EMAIL=your-email@example.com
SENDER_NAME=MeghaMart
```

---

## Testing Your Email Configuration

### 1. Check If Email Service is Configured

```python
# In Python terminal
from app.config import settings
from app.services.email_service import email_service

# Check configuration
print(email_service.is_configured())  # Should return True

# Check settings
print(f"SMTP Server: {settings.smtp_server}")
print(f"SMTP Port: {settings.smtp_port}")
print(f"Sender: {email_service.sender_name} <{email_service.sender_email}>")
```

### 2. Test Email Sending

```python
# Test sending an email
test_url = "http://localhost:5173/reset-password?token=test123"
result = email_service.send_password_reset_email(
    recipient_email="your-test-email@gmail.com",
    reset_url=test_url,
    user_name="Test User"
)
print(f"Email sent: {result}")  # Should return True
```

### 3. Test Through API

```bash
# Terminal
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@gmail.com"}'
```

Then check your email!

---

## Frontend Changes Made

### Before
```jsx
<AlertDescription className="text-sm">
  <strong>💡 Development:</strong> Check your backend console for the reset link.
</AlertDescription>
```

### After
```jsx
<AlertDescription className="text-sm">
  <strong>✓ Email Sent:</strong> Please check your email inbox for the password reset link. 
  If you don't see it, check your spam folder.
</AlertDescription>
```

---

## Backend Changes Made

### New Email Service

**File**: `app/services/email_service.py`

Features:
- ✅ SMTP email sending
- ✅ HTML + Plain text emails
- ✅ Professional email template
- ✅ Error handling and logging
- ✅ Configuration checking

### Updated Endpoint

**File**: `app/routers/auth.py` (forgot-password endpoint)

Changes:
- ✅ Uses email service to send actual emails
- ✅ Still logs to console for development
- ✅ Returns email_sent status
- ✅ Better error handling for non-existent users

### Updated Configuration

**File**: `app/config.py`

Added settings:
```python
smtp_server: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_username: str = ""
smtp_password: str = ""
sender_email: str = ""
sender_name: str = "MeghaMart"
```

---

## Email Template Features

The generated email includes:

✅ **Professional Design**
- Gradient header with lock icon
- Responsive layout
- Mobile-friendly

✅ **Content**
- Personalized greeting with user's first name
- Clear explanation of what happened
- Large "Reset Password" button
- Fallback text link
- Security warning (24-hour expiration)
- Contact support information
- Footer with company info

✅ **Security**
- HTML + Plain text versions
- No sensitive information in email body
- Clear expiration warning
- Professional tone

---

## Troubleshooting

### Problem: "Email service not configured"

**Solution**: 
1. Check `.env` file exists with email settings
2. Verify SMTP credentials are correct
3. Restart backend after changing .env

### Problem: "SMTP authentication failed"

**Solution**:
1. For Gmail: Make sure you used the 16-character App Password, not your regular password
2. For Outlook: Verify email and password are correct
3. Try using the email in a test tool first (Gmail itself, Outlook)

### Problem: "Connection timed out"

**Solution**:
1. Check SMTP server address is correct
2. Check SMTP port is correct (usually 587 for TLS)
3. Make sure firewall isn't blocking outgoing email
4. Try a different email provider

### Problem: "Email received but looks ugly"

**Solution**:
1. The HTML template is professional but may vary by email client
2. Check both HTML and plain text versions
3. Most email clients support the HTML version

### Problem: Email goes to spam

**Solution**:
1. Add your domain to SPF records (setup with your email provider)
2. Configure DKIM (with your email provider)
3. Use a professional email service (SendGrid, Mailtrap) for production

---

## Development vs Production

### Development (.env)
```bash
# Use Gmail or Mailtrap for testing
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-dev-email@gmail.com
SMTP_PASSWORD=app-password
SENDER_EMAIL=your-dev-email@gmail.com
```

### Production (.env on Server)
```bash
# Use SendGrid or dedicated email service
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SENDER_EMAIL=noreply@yourdomain.com
```

---

## Quick Start (5 Minutes)

### For Gmail Users:
1. Enable 2FA on your Gmail account
2. Generate an App Password
3. Add these 4 lines to `.env`:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=16-char-app-password
   ```
4. Restart backend
5. Test by requesting password reset
6. Check your inbox!

---

## Files Created/Modified

### Created
- ✅ `app/services/email_service.py` - Email sending service

### Modified
- ✅ `app/config.py` - Added email settings
- ✅ `app/routers/auth.py` - Updated forgot-password endpoint
- ✅ `requirements.txt` - Added email dependencies
- ✅ `frontend/src/pages/ForgotPasswordPage.jsx` - Updated message

---

## Testing Checklist

- [ ] `.env` file has SMTP credentials
- [ ] Backend restarted after .env changes
- [ ] `requirements.txt` installed (pip install -r requirements.txt)
- [ ] Email service configured (is_configured() returns True)
- [ ] Can request password reset
- [ ] Email arrives in inbox (not spam)
- [ ] Email has professional HTML format
- [ ] Reset link in email works
- [ ] Can actually reset password using link

---

## Production Deployment

For production, use a professional email service:

**Recommended**:
1. SendGrid (most popular)
2. Amazon SES
3. Mailgun
4. Brevo (formerly Sendinblue)

These services:
- ✅ Handle deliverability
- ✅ Provide analytics
- ✅ Scale to thousands of emails
- ✅ Have better security

---

## Support

If you need help:

1. Check the error logs in backend console
2. Verify SMTP credentials with your email provider
3. Use Mailtrap to test (it captures all emails)
4. Check documentation of your email provider

---

**Status**: ✅ Email configuration ready

The system is now set up to send actual emails instead of just logging to console!

