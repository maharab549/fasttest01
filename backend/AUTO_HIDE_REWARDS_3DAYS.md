# 🔄 AUTO-HIDE USED/EXPIRED REWARDS AFTER 3 DAYS

## Feature Implementation

### User Request
> "used rewards and expired reward will be disapear after 3 days"

### Solution
Implemented automatic hiding of used and expired rewards that are older than 3 days.

---

## How It Works

### Backend Logic (CRUD Layer)
**File**: `app/crud.py` → `get_redemptions()` function

```python
def get_redemptions(
    db: Session,
    loyalty_account_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    include_old_used_expired: bool = False  # NEW parameter
) -> List[models.Redemption]:
```

**New Behavior:**
- By default (`include_old_used_expired=False`), automatically filters out rewards with:
  - Status = "used" OR status = "expired"
  - AND used/expires date is older than 3 days
- Keeps "active" rewards always (no age filtering)
- Can retrieve all rewards including old ones by setting `include_old_used_expired=True`

**Timestamp Checking:**
- Uses `used_at` for used rewards (when reward was applied to order)
- Uses `expires_at` for expired rewards (when reward becomes invalid)
- Falls back to `created_at` if those aren't available

### API Layer Update
**File**: `app/routers/loyalty.py` → `get_loyalty_dashboard()` endpoint

Updated to pass `include_old_used_expired=False` when fetching redemptions:
```python
redemptions = crud.get_redemptions(
    db, account_id, 
    status=None, 
    limit=50, 
    include_old_used_expired=False  # Auto-hide old used/expired
)
```

### Frontend Display
**File**: `src/pages/RewardsPage.jsx`

No changes needed! The frontend already:
1. Groups rewards by status
2. Only shows sections if they have items
3. When backend returns no old used/expired rewards, those sections are empty and don't display

---

## Timeline Examples

### Today (Day 0)
- Used reward at 10 AM → Shows in "Used Rewards" section

### Tomorrow (Day 1)
- Still shows in "Used Rewards" section

### Day 2
- Still shows in "Used Rewards" section

### Day 3 (72 hours after use)
- Still shows (less than 3 days old)

### Day 3.1 (>72 hours after use)
- ✅ **HIDDEN** - No longer appears on rewards page
- Can still be retrieved from database if needed (admin access)

---

## Code Changes

### 1. `app/crud.py` - New filtering logic in `get_redemptions()`

Added approximately 50 lines of logic:
```python
from datetime import datetime, timedelta

# Filter out used/expired rewards older than 3 days
if not include_old_used_expired:
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    filtered = []
    
    for redemption in all_redemptions:
        status_val = getattr(redemption, "status", None)
        
        # Keep 'active' rewards always
        if status_val == "active":
            filtered.append(redemption)
            continue
        
        # For 'used' and 'expired', check the timestamp
        if status_val in ["used", "expired"]:
            # Check which timestamp to use
            timestamp = getattr(redemption, "used_at", None)
            if not timestamp:
                timestamp = getattr(redemption, "expires_at", None)
            if not timestamp:
                timestamp = getattr(redemption, "created_at", None)
            
            # Only keep if newer than 3 days
            if timestamp and timestamp > three_days_ago:
                filtered.append(redemption)
        else:
            # Keep any other status
            filtered.append(redemption)
    
    all_redemptions = filtered
```

### 2. `app/routers/loyalty.py` - Updated dashboard call

Changed from:
```python
redemptions = crud.get_redemptions(db, account_id, status=None, limit=50)
```

To:
```python
redemptions = crud.get_redemptions(db, account_id, status=None, limit=50, include_old_used_expired=False)
```

---

## Frontend Behavior

### Active Rewards (Green Section)
- ✅ Always shown
- No age filtering applied
- "Expires: [DATE]" shown

### Used Rewards (Blue Section)  
- ✅ Shown if < 3 days old
- ✗ Hidden if ≥ 3 days old
- Shows "Used: [DATE]"
- Marked with strikethrough

### Expired Rewards (Gray Section)
- ✅ Shown if < 3 days old  
- ✗ Hidden if ≥ 3 days old
- Shows "Expired: [DATE]"
- Marked with strikethrough

---

## User Experience

**Before:**
- Rewards page cluttered with old used/expired items
- Confusing to see many "strikethrough" rewards

**After:**
- Rewards page shows only actionable/recent items
- Old used/expired rewards automatically disappear after 3 days
- Cleaner, less cluttered UI
- Focus on active and recent rewards

---

## Technical Details

### 3-Day Calculation
- Uses UTC time for consistency
- Exact calculation: `now() - 72 hours`
- Example: If used at 2025-11-08 10:00:00 AM UTC
  - Disappears after 2025-11-11 10:00:00 AM UTC

### Database Query Impact
- No database schema changes needed
- No new columns added
- Uses existing timestamps: `used_at`, `expires_at`, `created_at`
- Filtering done in Python (small performance impact)

### Backward Compatibility
- Old rewards still exist in database
- Optional `include_old_used_expired` parameter (defaults to False)
- Admin can retrieve full history if needed

---

## Testing

### Test Case 1: Active Rewards
✅ Never disappear (no age filtering)

### Test Case 2: Recent Used Reward (< 3 days)
1. Create used reward
2. Check rewards page → Shows in "Used Rewards"
3. Wait < 3 days
4. Check again → Still visible

### Test Case 3: Old Used Reward (> 3 days)
1. Create used reward at 2025-11-01
2. Current date: 2025-11-11
3. Check rewards page → NOT in "Used Rewards"
4. Used Rewards section shows 0 items or not visible

### Test Case 4: Old Expired Reward (> 3 days)
Same as Test Case 3, but for expired rewards

---

## Future Enhancements

1. **Admin History View**
   - Add endpoint to retrieve all rewards including old ones
   - `/api/v1/loyalty/history` with optional date range

2. **Configuration**
   - Make 3-day threshold configurable
   - Settings in environment or database

3. **Archive Feature**
   - Let users manually archive old rewards
   - Separate "Archived" section

4. **Notifications**
   - Notify user before reward expires (e.g., 1 day before)
   - Notify when reward is about to disappear from view (e.g., 2 days after use)

---

## Files Modified
- ✅ `app/crud.py` - Added filtering logic to `get_redemptions()`
- ✅ `app/routers/loyalty.py` - Updated dashboard endpoint comment

## Files NOT Modified (Already Correct)
- ✓ `src/pages/RewardsPage.jsx` - Frontend already handles hiding empty sections

