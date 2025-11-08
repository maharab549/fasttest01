# ⚡ 5-Minute Professional Email Setup

## What You Get

✅ Production-grade password reset emails  
✅ Rate limiting (prevent abuse)  
✅ Retry mechanism (reliability)  
✅ Beautiful email templates  
✅ Comprehensive logging  
✅ Security best practices  

---

## Option A: Gmail (EASIEST) ⭐

### Step 1: Enable 2FA on Gmail
1. Go to https://myaccount.google.com
2. Click "Security" in left menu
3. Find "2-Step Verification" → Click to enable
4. Follow prompts (add phone number, etc.)

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows" (or your device)
3. Google generates 16-character password
4. Copy it (you'll need this)

### Step 3: Create `.env` file

In `backend` folder, create file named `.env`:

```env
# Email Configuration (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=MeghaMart

# Optional: Frontend URL
FRONTEND_URL=http://localhost:5173
```

Replace:
- `your-email@gmail.com` → Your actual Gmail
- `xxxx xxxx xxxx xxxx` → The 16-char password from Step 2

### Step 4: Install & Restart

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Step 5: Test
- Go to forgot password page
- Enter test email
- Check inbox → You should receive email! ✅

**Done in 5 minutes!** 🎉

---

## Option B: Outlook (EASY) ⭐⭐

```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SENDER_EMAIL=your-email@outlook.com
SENDER_NAME=MeghaMart
```

---

## Option C: Mailtrap (TESTING) ⭐⭐⭐

Great for testing before production!

1. Go to https://mailtrap.io
2. Sign up (free account)
3. Create project
4. Go to SMTP settings
5. Copy credentials:

```env
SMTP_SERVER=live.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USERNAME=api
SMTP_PASSWORD=your-mailtrap-token
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=MeghaMart
```

6. All emails go to Mailtrap inbox (not real inboxes)

---

## Option D: SendGrid (PRODUCTION) 🚀

1. Go to https://sendgrid.com
2. Sign up (free tier available)
3. Create API key
4. Add to `.env`:

```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SENDER_EMAIL=your-verified-email@domain.com
SENDER_NAME=MeghaMart
```

---

## Without Email Configuration (DEVELOPMENT) 🛠️

If you don't add `.env`:
- System still works ✅
- Reset URLs logged to console ✅
- Copy URL and test manually ✅
- Perfect for development!

```
Backend console shows:
============================================================
PASSWORD RESET LINK FOR user@email.com
http://localhost:5173/reset-password?token=xyz...
============================================================
```

---

## Verify Setup

### Check 1: Backend is running
```
Look at terminal where you ran:
python -m uvicorn app.main:app --reload

Should show:
Uvicorn running on http://127.0.0.1:8000
```

### Check 2: Email configured
```
Backend should log this on startup:
"Email service configured" (if `.env` set)
OR
"Email service not configured" (if no `.env`)

Both are OK! 
```

### Check 3: Test password reset
```
1. Frontend: Forgot password page
2. Enter your test email
3. Check console (if no email config)
   OR check inbox (if email configured)
4. Should see reset link ✅
```

---

## Features Now Enabled

### Rate Limiting (Prevent Abuse)
- Max 5 resets per IP per hour
- Max 3 resets per email per hour
- Attacker can't spam

### Professional Emails
- Beautiful design
- Mobile-responsive
- Security info included
- Backup text link

### Retry Mechanism
- Auto-retries on failure
- Exponential backoff
- Max 3 attempts

### Comprehensive Logging
- Every attempt logged
- Error tracking
- Security monitoring

---

## Common Issues

### "Connection timeout"
**Fix**: Check SMTP_SERVER and SMTP_PORT are correct

### "Authentication failed"
**Fix**: Check SMTP_USERNAME and SMTP_PASSWORD are correct
- For Gmail: Use 16-char app password, NOT your regular password
- For Outlook: Use your actual password

### "No email received"
**Fix**: Check spam folder first!
Then try:
1. Verify email address in `.env`
2. Check backend console for errors
3. Try with Mailtrap (test service)

### "Rate limit error"
**Fix**: This is normal! It means system is protecting against abuse
- Wait 1 hour and try again
- Or test with different email

---

## Production Checklist

Before deploying to production:

- [ ] Email configured in `.env`
- [ ] Test emails arrive successfully
- [ ] Check for formatting issues
- [ ] Verify sender name displays correctly
- [ ] Test on mobile device
- [ ] Add SPF/DKIM records (optional but recommended)
- [ ] Test rate limiting
- [ ] Check backend logs for errors

---

## Quick Reference

| Provider | Setup Time | Cost | Difficulty |
|----------|-----------|------|------------|
| Gmail | 5 min | Free | ⭐ Easy |
| Outlook | 3 min | Free | ⭐ Easy |
| Mailtrap | 5 min | Free | ⭐ Easy |
| SendGrid | 10 min | Free+ | ⭐⭐ Medium |
| AWS SES | 15 min | $0.10/1k | ⭐⭐⭐ Hard |

**Recommendation**: Start with Gmail (easiest), upgrade to SendGrid for production.

---

## Support

**If emails still not working**:
1. Check backend console logs
2. Verify credentials in `.env`
3. Try with Mailtrap first
4. Check backend is restarted
5. Clear browser cache

**Technical Details**:
- See: `PROFESSIONAL_EMAIL_SYSTEM_GUIDE.md`
- See: `app/services/email_service_enhanced.py`

---

**You're ready! Email system is production-grade now.** 🚀
