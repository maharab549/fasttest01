# Forgot Password Feature - Quick Testing Guide

## Prerequisites
- Backend server running: `python -m uvicorn app.main:app --reload`
- Frontend dev server running: `npm run dev`
- Modern web browser with Developer Tools

## Quick Test (5 minutes)

### Step 1: Start at Login Page
1. Open `http://localhost:5173/login`
2. You should see the login form with a "Forgot your password?" link

### Step 2: Request Password Reset
1. Click "Forgot your password?" link
2. Enter your registered email (e.g., `seller@example.com`)
3. Click "Submit"
4. You should see a success message: "Check your email for password reset instructions"

### Step 3: Get Reset Token
1. Open backend terminal where server is running
2. Look for console log with format:
   ```
   Reset URL: /reset-password?token=abc123...xyz789
   ```
3. Copy the entire reset URL

**If you don't see console output:**
- Open browser Developer Tools (F12)
- Go to Network tab
- Find the `forgot-password` request
- Click it and check Response

### Step 4: Reset Password
1. In browser, visit: `http://localhost:5173/reset-password?token=YOUR_TOKEN`
   (Replace YOUR_TOKEN with the token from step 3)
2. You should see password reset form
3. Enter new password:
   - Must be at least 8 characters
   - Must have 1 uppercase letter
   - Must have 1 lowercase letter
   - Must have 1 number
   - Example: `NewPassword123`
4. Confirm password (enter same password again)
5. Click "Reset Password"

### Step 5: Verify Success
1. You should see "Password Reset Successfully!" message
2. You'll be automatically redirected to login after 2 seconds
3. Enter your email and new password
4. You should successfully log in

## Detailed Test Scenarios

### Scenario 1: Valid Reset Flow
**Expected**: Successfully reset password

**Steps**:
1. Go to `/forgot-password`
2. Enter valid email
3. Submit
4. Copy reset URL from console
5. Visit reset URL
6. Enter valid new password
7. Submit

**Result**: ✅ Should see success message and redirect to login

---

### Scenario 2: Invalid Token
**Expected**: Show error message

**Steps**:
1. Visit `/reset-password?token=invalid_token_12345`

**Result**: ✅ Should show "This reset link has expired or is invalid"

---

### Scenario 3: Expired Token
**Expected**: Show error message

**Steps**:
1. Get reset token and wait 24+ hours
2. Visit reset URL

**Result**: ✅ Should show token expired error

---

### Scenario 4: Token Already Used
**Expected**: Show error message

**Steps**:
1. Get reset token and use it once
2. Try to use same token again

**Result**: ✅ Should show token already used error

---

### Scenario 5: Password Mismatch
**Expected**: Show validation error

**Steps**:
1. Get reset token
2. Visit reset URL
3. Enter `NewPassword123` in first field
4. Enter `DifferentPassword456` in confirm field
5. Try to submit

**Result**: ✅ Should show "Passwords do not match" error

---

### Scenario 6: Password Too Short
**Expected**: Show validation error

**Steps**:
1. Get reset token
2. Enter `Pass1` (5 characters)
3. Try to submit

**Result**: ✅ Should show "Password must be at least 8 characters"

---

### Scenario 7: Missing Requirements
**Expected**: Show what's missing

**Steps**:
1. Get reset token
2. Try entering `abcdefgh1` (no uppercase)
3. Try entering `ABCDEFGH1` (no lowercase)
4. Try entering `Abcdefgh` (no number)

**Result**: ✅ Should highlight missing requirements in red

---

### Scenario 8: Multiple Reset Requests
**Expected**: Old tokens invalidated, only newest works

**Steps**:
1. Request reset for email
2. Note the reset URL
3. Request reset again for same email
4. Get new reset URL
5. Try old token
6. Try new token

**Result**: 
- ✅ Old token should show as expired
- ✅ New token should work

---

## Backend Console Output Reference

### Successful Reset Request
```
Reset URL: /reset-password?token=abcdef123456789xyz...
```

### Successful Password Reset
```
User password updated for user: user@example.com
Password reset token marked as used: token_id_123
```

### Errors
```
Email not found (generic message shown to user)
Token has expired
Token already used
```

## Network Tab Reference

### Request: POST /auth/forgot-password
```
Request Body:
{
  "email": "user@example.com"
}

Response:
{
  "message": "If an account exists with this email, you will receive a password reset link."
}
```

### Request: GET /auth/reset-token/{token}
```
Response (Valid):
{
  "is_valid": true,
  "user_id": 123
}

Response (Invalid):
{
  "detail": "This reset link has expired or is invalid."
}
```

### Request: POST /auth/reset-password
```
Request Body:
{
  "token": "abc123...",
  "new_password": "NewPassword123",
  "confirm_password": "NewPassword123"
}

Response:
{
  "message": "Password has been reset successfully. You can now login with your new password."
}
```

## Troubleshooting

### Issue: "Backend console doesn't show reset URL"
**Solution**:
1. Make sure backend is running in foreground (not background)
2. Check Network tab in browser DevTools
3. Look at the forgot-password request response

### Issue: Reset URL keeps showing as expired
**Solution**:
1. Tokens are valid for 24 hours
2. Get a fresh token by requesting a new reset
3. Use the new token immediately

### Issue: "Password requirements keep showing red"
**Solution**:
1. Password must have ALL of:
   - At least 8 characters
   - At least 1 uppercase (A-Z)
   - At least 1 lowercase (a-z)
   - At least 1 number (0-9)
2. Try: `SecurePass123`

### Issue: Getting 404 on reset page
**Solution**:
1. Make sure frontend is running
2. Check your token is correct (no typos)
3. Try visiting `/forgot-password` first

### Issue: Can't log in with new password
**Solution**:
1. Make sure you're entering the exact password you set
2. Check caps lock is off
3. Try requesting a new reset if token was used

## Test Data

### Test User 1
- Email: `seller@example.com`
- Current Password: `seller123` (or whatever you set)
- New Password (for testing): `NewSecure123`

### Test User 2
- Email: `customer@example.com`
- Current Password: `customer123`
- New Password (for testing): `TestPass456`

## Success Indicators ✅

After completing all steps, you should see:

1. ✅ Email submission works on ForgotPasswordPage
2. ✅ Success message shows after submission
3. ✅ Reset URL appears in backend console
4. ✅ ResetPasswordPage loads with reset form
5. ✅ Password requirements show and update in real-time
6. ✅ Password reset succeeds
7. ✅ Success message appears
8. ✅ Automatic redirect to login happens
9. ✅ Can log in with new password

If all 9 items show ✅, the forgot password feature is working perfectly!

---

**Created**: Implementation Complete
**Last Updated**: Today
**Status**: Ready for Testing ✅
