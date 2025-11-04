from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import crud, schemas, models, auth
from ..database import get_db

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/dashboard", response_model=schemas.LoyaltyDashboard)
def get_loyalty_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Get loyalty dashboard for current user
    
    Returns:
    - Loyalty account details with points balance and tier
    - Recent transactions (last 10)
    - Active redemptions
    - Next tier information and points needed
    """
    # Get or create loyalty account
    user_id = int(current_user.id)  # type: ignore
    account = crud.get_loyalty_account_by_user(db, user_id)
    if not account:
        account = crud.create_loyalty_account(db, user_id)
    
    # Get recent transactions
    account_id = int(account.id)  # type: ignore
    transactions = crud.get_points_transactions(db, account_id, limit=10)
    
    # Get active redemptions
    redemptions = crud.get_redemptions(db, account_id, status="active", limit=10)
    
    # Calculate next tier info
    tiers = crud.get_reward_tiers(db)
    next_tier = None
    points_to_next_tier = None
    
    if account.tier:
        # Find next tier
        for tier in tiers:
            if int(tier.min_points) > int(account.lifetime_points):  # type: ignore
                next_tier = tier
                points_to_next_tier = int(tier.min_points) - int(account.lifetime_points)  # type: ignore
                break
    elif tiers:
        # No tier yet, first tier is next
        next_tier = tiers[0]
        points_to_next_tier = int(next_tier.min_points) - int(account.lifetime_points)  # type: ignore
    
    return {
        "account": account,
        "recent_transactions": transactions,
        "active_redemptions": redemptions,
        "next_tier": next_tier,
        "points_to_next_tier": points_to_next_tier
    }


@router.get("/account", response_model=schemas.LoyaltyAccount)
def get_my_loyalty_account(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get current user's loyalty account"""
    account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
    if not account:
        account = crud.create_loyalty_account(db, int(current_user.id))  # type: ignore
    return account


@router.get("/transactions", response_model=List[schemas.PointsTransaction])
def get_my_transactions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get transaction history for current user"""
    account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
    if not account:
        return []
    
    return crud.get_points_transactions(db, int(account.id), skip=skip, limit=limit)  # type: ignore


@router.get("/tiers", response_model=List[schemas.RewardTier])
def get_all_tiers(db: Session = Depends(get_db)):
    """Get all reward tiers"""
    return crud.get_reward_tiers(db)


@router.post("/redeem", response_model=schemas.Redemption, status_code=status.HTTP_201_CREATED)
def redeem_points(
    redemption_data: schemas.RedemptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Redeem points for rewards
    
    Redemption types:
    - **discount_code**: Get a discount code (e.g., 1000 points = $10 off)
    - **free_shipping**: Free shipping voucher (e.g., 500 points)
    - **gift_card**: Store gift card (e.g., 5000 points = $50 card)
    - **cashback**: Cash refund (e.g., 10000 points = $100)
    """
    account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
    if not account:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    
    # Validate redemption type and points
    min_points = {
        "discount_code": 500,
        "free_shipping": 300,
        "gift_card": 2000,
        "cashback": 5000
    }
    
    if redemption_data.redemption_type not in min_points:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid redemption type. Must be one of: {', '.join(min_points.keys())}"
        )
    
    if redemption_data.points_redeemed < min_points[redemption_data.redemption_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum {min_points[redemption_data.redemption_type]} points required for {redemption_data.redemption_type}"
        )
    
    try:
        redemption = crud.create_redemption(db, int(account.id), redemption_data)  # type: ignore
        return redemption
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/redemptions", response_model=List[schemas.Redemption])
def get_my_redemptions(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get redemption history for current user"""
    account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
    if not account:
        return []
    
    return crud.get_redemptions(db, int(account.id), status=status, skip=skip, limit=limit)  # type: ignore


@router.post("/redemptions/{redemption_id}/use")
def use_my_redemption(
    redemption_id: int,
    order_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark a redemption as used"""
    # Get redemption and verify ownership
    account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
    if not account:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    
    redemptions = crud.get_redemptions(db, int(account.id))  # type: ignore
    redemption = next((r for r in redemptions if int(r.id) == redemption_id), None)  # type: ignore
    
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption not found")
    
    try:
        updated_redemption = crud.use_redemption(db, redemption_id, order_id)
        return {"message": "Redemption marked as used", "redemption": updated_redemption}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Admin endpoints
@router.post("/admin/tiers", response_model=schemas.RewardTier, status_code=status.HTTP_201_CREATED)
def create_tier(
    tier_data: schemas.RewardTierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    """Create a new reward tier (admin only)"""
    return crud.create_reward_tier(db, tier_data)


@router.post("/admin/award-points")
def admin_award_points(
    user_id: int,
    points_data: schemas.PointsEarnRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    """Manually award points to a user (admin only)"""
    account = crud.get_loyalty_account_by_user(db, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Loyalty account not found for user")
    
    try:
        transaction = crud.award_points(
            db=db,
            loyalty_account_id=int(account.id),  # type: ignore
            points=points_data.points,
            source=points_data.source or "admin_adjustment",
            source_id=points_data.source_id,
            description=points_data.description
        )
        return {"message": "Points awarded successfully", "transaction": transaction}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
