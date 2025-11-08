# Forgot Password - Blank Page Troubleshooting

## Issue: Blank Page After Submitting Email

If you see a blank page after entering an email and clicking "Send Reset Link", follow these steps:

---

## Step 1: Check Browser Console (F12)

1. **Open Developer Tools**: Press `F12` in your browser
2. **Go to Console tab**: Look at the bottom tabs
3. **Look for errors**: You should see:
   - ✅ "Forgot password response: {...}" - Good, it worked
   - ❌ Red error messages - There's a problem

### What you should see:
```
Forgot password response: {message: "If this email exists, a password reset link has been sent"}
```

---

## Step 2: Check Network Tab

1. **Open Developer Tools**: Press `F12`
2. **Go to Network tab**: Next to Console
3. **Do the reset again**: Enter email and click Submit
4. **Look for `forgot-password` request**:
   - Should show `POST` method
   - Should show status `200` (green)
   - **Check Response** tab to see the answer

### Good Response (200):
```json
{
  "message": "If this email exists, a password reset link has been sent"
}
```

### Bad Response (400/500):
- Shows error message in Response tab
- Example: `{"detail": "..."}`

---

## Step 3: Check Backend Console

1. **Look at terminal where backend is running**
2. **You should see**:
```
==================================================
PASSWORD RESET LINK FOR user@example.com
http://localhost:5173/reset-password?token=abc123...xyz
==================================================
```

If you don't see this, the backend didn't receive the request.

---

## Step 4: Common Issues & Solutions

### Issue 1: "Cannot POST /api/v1/auth/forgot-password"
**Problem**: Backend endpoint not found
**Solution**:
1. Restart backend server
2. Make sure you have latest code
3. Check backend is running on port 8000

### Issue 2: Backend console shows error about "email_request"
**Problem**: Schema validation failed
**Solution**:
1. Make sure you're sending valid email
2. Email must have @ symbol
3. Clear browser cache and try again

### Issue 3: No response from backend
**Problem**: Backend not running or wrong URL
**Solution**:
1. Check terminal - is backend still running?
2. If crashed, restart it:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
3. Check frontend .env has correct API URL

### Issue 4: Completely blank page (no UI)
**Problem**: Component rendering issue
**Solution**:
1. Hard refresh browser: `Ctrl + Shift + R`
2. Check browser console for JavaScript errors (red text)
3. Restart frontend dev server:
   ```bash
   npm run dev
   ```

---

## Step 5: Verify Success

You should see:
1. ✅ Spinner disappears
2. ✅ Success message appears with check icon
3. ✅ Says "Check Your Email"
4. ✅ Shows your email address
5. ✅ Has buttons: "Back to Login" and "Try Another Email"

If you see this, it's working! ✅

---

## Full Test Sequence

```
1. Open http://localhost:5173/login
   ↓
2. Click "Forgot your password?"
   ↓
3. See email form
   ↓
4. Enter your email (e.g., seller@example.com)
   ↓
5. Click "Send Reset Link"
   ↓
6. Wait for spinner to finish (2-3 seconds)
   ↓
7. Should see success message with email shown
   ↓
8. Check backend console for reset URL
   ↓
9. Copy URL: http://localhost:5173/reset-password?token=xxx
   ↓
10. Open that URL in browser
    ↓
11. Should see password reset form
    ↓
12. Enter new password and confirm
    ↓
13. Click "Reset Password"
    ↓
14. Should see success and redirect to login
    ↓
15. Log in with new password
    ✅ SUCCESS!
```

---

## Quick Debug Commands

### Check if backend is working:
```bash
# In PowerShell
curl http://localhost:8000/api/v1/auth/verify-token
```

### Check if frontend can reach backend:
Open browser console and run:
```javascript
fetch('http://localhost:8000/api/v1/auth/verify-token')
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e))
```

### Clear cache and restart:
```bash
# Terminal 1 - Backend
python -m uvicorn app.main:app --reload

# Terminal 2 - Frontend (after killing current)
npm run dev
```

---

## If Still Not Working

### Try this nuclear option:

1. **Kill all processes**:
   ```bash
   # Close all terminals with backend/frontend
   ```

2. **Clear cache**:
   ```bash
   # Frontend cache
   del frontend\node_modules\.vite
   
   # Browser cache
   # In browser: Ctrl + Shift + Delete → Clear browsing data
   ```

3. **Restart everything**:
   ```bash
   # Terminal 1
   cd backend
   python -m uvicorn app.main:app --reload
   
   # Terminal 2
   cd frontend
   npm run dev
   ```

4. **Test again from scratch**

---

## Last Resort: Add Debugging

If still stuck, modify `ForgotPasswordPage.jsx` temporarily:

Add this after line 41 (after `setIsLoading(true);`):

```jsx
console.log('Submitting email:', email);
console.log('API being called:', authAPI.forgotPassword);
```

Then in Network tab, you'll see exactly what's being sent.

---

## Success Indicators ✅

When working properly:
- ✅ Page shows loading spinner
- ✅ Spinner disappears after 2-3 seconds
- ✅ Success message appears (green checkmark, "Check Your Email")
- ✅ Email shown in success message
- ✅ Buttons appear ("Back to Login", "Try Another Email")
- ✅ No error messages
- ✅ Backend console shows reset URL

**If all 7 show ✅, it's working perfectly!**

---

Need more help? Check the files:
- Frontend component: `frontend/src/pages/ForgotPasswordPage.jsx`
- API methods: `frontend/src/lib/api.js`
- Backend endpoint: `backend/app/routers/auth.py` (lines 185-228)
- Backend model: `backend/app/models.py` (PasswordResetToken)
