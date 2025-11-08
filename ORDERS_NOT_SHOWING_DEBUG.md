# 🔍 ORDERS NOT SHOWING - Debugging Guide

## Current Status

✅ **Database:** OK - 20 orders exist in database
✅ **Backend Server:** Running on http://0.0.0.0:8000
✅ **Database Columns:** All discount columns migrated successfully
❓ **Frontend Orders Display:** NOT SHOWING

## Possible Issues

### 1. **Wrong User Logged In**
- Database has orders for users: 1, 2, 5
- Check: Are you logged in as user 1, 2, or 5?
- **Solution:** Log out and log in as one of these test users

### 2. **API Endpoint Not Returning Data**
- Endpoint: `GET /api/v1/orders/`
- **Check:** Open browser DevTools (F12) → Network tab
- **Look for:** `/orders/` request
- **Status should be:** 200 OK
- **Response should contain:** Array of order objects

### 3. **Frontend Not Processing Response**
- The OrdersPage component expects response in one of these formats:
  - Direct array: `[]`
  - Wrapped in data: `{ data: [] }`
  - Wrapped in data twice: `{ data: { data: [] } }`

## How to Test

### Step 1: Check Current User
Open browser DevTools Console and run:
```javascript
// Check who you're logged in as
localStorage.getItem('user') // or check from AuthContext
```

### Step 2: Test API Directly
In browser console, run:
```javascript
// Get your auth token
const token = localStorage.getItem('access_token');

// Test orders endpoint
fetch('http://localhost:8000/api/v1/orders/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(data => console.log('Orders:', data))
.catch(e => console.error('Error:', e));
```

### Step 3: Check Backend Logs
The backend should print something like:
```
[orders.py] 🔍 get_user_orders called: user_id=5, skip=0, limit=50
[orders.py] 📦 Found N orders for user 5
```

Look for these logs in the backend terminal.

## Test Users in Database

```
User ID: 1
  - Orders: 3 (IDs: 3, 4, 5)
  - Status: delivered

User ID: 2  
  - Orders: 4 (IDs: 7, 9, 10, 20)
  - Status: delivered/confirmed

User ID: 5
  - Orders: 13 (Most recent)
  - Status: pending/delivered
```

## Common Fixes

### Fix 1: Frontend Not Making Request
- Check if `useQuery` is enabled: `enabled: isAuthenticated`
- Verify `isAuthenticated` is true

### Fix 2: CORS Error
- Check browser console for CORS errors
- Backend CORS should allow requests from `http://localhost:5173`

### Fix 3: Auth Token Expired
- Clear localStorage
- Log out and back in
- Try again

### Fix 4: API Response Format Issue
- Backend returns: `List[Order]` (array)
- Frontend expects: `Array` OR `{ data: Array }`
- The normalization logic should handle both

## Quick Diagnosis Script

Run in backend terminal:
```bash
python check_orders.py
```

This shows:
- ✅ Number of orders
- ✅ Orders by user
- ✅ Order statuses
- ✅ Most recent orders

## Next Steps

1. **Verify you're logged in** as user 1, 2, or 5
2. **Open DevTools** (F12) → Network tab
3. **Reload page** and look for `/orders/` request
4. **Check response:**
   - Should be 200 OK
   - Should contain array of orders
5. **If empty response:** Check backend logs for errors
6. **If error:** Share the error message

## Backend Logs to Check

Look for these in the backend terminal when accessing /orders page:

```
INFO:app.security_middleware:Request: GET /api/v1/orders/ from 127.0.0.1
[orders.py] 🔍 get_user_orders called: user_id=X, skip=0, limit=50
[orders.py] 📦 Found N orders for user X
```

If you don't see these logs, the request isn't reaching the backend.

---

**Last Verified:** Nov 8, 2025
- Database: ✅ OK
- Server: ✅ Running
- Orders: ✅ 20 in database
- Status: 🔍 Investigating frontend display
