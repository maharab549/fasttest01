# Return Request Issue - Testing Guide

## ✅ What Was Fixed

### 1. **Product Snapshot in Orders**
- Order items now save product name and image when orders are placed
- Migrated 11 existing order items with product data
- Fixed "Product #null" display issue

### 2. **Database Migration**  
- Added `product_name` and `product_image` columns to `order_items` table
- Updated migration to extract first image from JSON array: `json_extract(images, '$[0]')`
- Fixed SQLite compatibility issues

### 3. **Frontend Improvements**
- Added "My Returns" button in Orders page header with badge showing return count
- Enhanced return detection logic
- Added comprehensive logging for debugging
- Improved query invalidation after return submission

## 🔍 What to Test

### Test 1: View Orders
1. Go to the Orders page
2. **Expected**: You should see a "My Returns" button in the header
3. Click on an order to see details
4. **Expected**: Product names and images should display correctly (no more "Product #null")

### Test 2: Submit Return Request
1. Find a delivered order
2. Click "Return Item" button on any product
3. Fill in the return reason
4. Click "Submit Return Request"
5. **Expected Results**:
   - Success message: "Return request submitted successfully!"
   - Return button should change to "View Return" button
   - "My Returns" badge should update with count

### Test 3: Track Returns
1. Click the "My Returns" button in Orders page header
   OR
2. Click "View Return" button on a returned item
3. **Expected**: You should see your return requests with tracking information

## 🐛 If Issues Persist

### Check Browser Console
Open browser DevTools (F12) and look for these logs:
```
[OrdersPage] ===== RETURNS DEBUG =====
[OrdersPage] myReturns: [...]
[OrdersPage] myReturns length: X
```

### What the logs should show:
- `myReturns` should be an array of return objects
- Each return should have:
  - `id`: Return ID
  - `order_id`: Order ID  
  - `return_number`: Unique tracking number
  - `return_items`: Array of items being returned
  - `status`: Current status (pending, approved, etc.)

### Common Issues:

**Issue 1: "View Return" button doesn't appear**
- Check console for return detection logs
- Verify `return_items` array exists and matches product_id or order_item_id

**Issue 2: Can't find returns after submission**
- Check if API call succeeded (Network tab, look for `/returns/` POST request)
- Check if `my-returns` query is fetching data

**Issue 3: Return option still visible after submission**
- Check if queries are refetching properly
- Look for "All queries refetched" log in console

## 📝 API Endpoints

- **Create Return**: `POST /api/v1/returns/`
- **Get My Returns**: `GET /api/v1/returns/my-returns`
- **Get Return Details**: `GET /api/v1/returns/{return_id}`

## 💡 Tips

1. **Refresh the page** after submitting a return to ensure state is synced
2. Check the **My Returns page** directly at `/my-returns`
3. Look for the **return count badge** on the "My Returns" button
4. Each return has a unique **return_number** for tracking

## ✨ Expected User Flow

```
Orders Page → Click Order → See Product Details
            ↓
     (if delivered)
            ↓
  Click "Return Item" → Fill Reason → Submit
            ↓
  Button changes to "View Return"
            ↓
  Click "View Return" or "My Returns" button
            ↓
  See Return Tracking Page with Status
```
