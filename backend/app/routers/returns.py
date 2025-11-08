from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, models, auth
from ..database import get_db
from datetime import datetime

router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("/", response_model=schemas.Return, status_code=status.HTTP_201_CREATED)
def create_return_request(
    return_data: schemas.ReturnCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Create a new return request
    
    - **order_id**: ID of the order to return
    - **reason**: Reason for return (defective, wrong_item, not_as_described, changed_mind, other)
    - **reason_details**: Additional details about the return
    - **items**: List of items to return with quantities
    - **refund_method**: original or store_credit
    """
    # Verify the order belongs to the user
    order = crud.get_order(db, return_data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if int(order.user_id) != int(current_user.id):  # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to return this order")
    
    # Check if order is eligible for return (e.g., within 30 days)
    days_since_order = (datetime.now() - order.created_at).days
    if days_since_order > 30:
        raise HTTPException(
            status_code=400,
            detail="Return window has expired. Returns must be initiated within 30 days of order."
        )
    
    # Check if order status allows returns
    if order.status not in ["delivered", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Only delivered orders can be returned"
        )
    
    try:
        return_request = crud.create_return(db=db, return_data=return_data, user_id=int(current_user.id))  # type: ignore
        return return_request
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-returns", response_model=List[schemas.Return])
def get_my_returns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all return requests for the current user"""
    returns = crud.get_returns_by_user(db=db, user_id=int(current_user.id), skip=skip, limit=limit)  # type: ignore
    return returns


@router.get("/seller/returns", response_model=List[schemas.Return])
def get_seller_returns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all return requests for products sold by the current seller"""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_
    import logging
    
    logger = logging.getLogger("uvicorn")
    logger.info(f"[SELLER RETURNS] Current user: {current_user.username} (ID: {current_user.id})")
    
    # Get seller profile
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        logger.warning(f"[SELLER RETURNS] No seller profile found for user {current_user.id}")
        return []
    
    logger.info(f"[SELLER RETURNS] Seller ID: {seller.id}")
    
    # Get all returns where the products belong to the current seller
    returns = db.query(models.Return)\
        .join(models.ReturnItem)\
        .join(models.Product, models.ReturnItem.product_id == models.Product.id)\
        .filter(models.Product.seller_id == seller.id)\
        .options(joinedload(models.Return.return_items))\
        .order_by(models.Return.created_at.desc())\
        .distinct()\
        .offset(skip).limit(limit).all()
    
    
    logger.info(f"[SELLER RETURNS] Found {len(returns)} returns for seller")
    
    return returns


@router.put("/seller/{return_id}/approve", response_model=schemas.Return)
def approve_return_seller(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Approve a return request (seller only)"""
    return_request = crud.get_return(db=db, return_id=return_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Verify seller owns the products in this return
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=403, detail="Seller profile not found")
    
    # Check if all items in the return belong to this seller
    for item in return_request.return_items:
        if item.product.seller_id != seller.id:
            raise HTTPException(status_code=403, detail="Not authorized to approve this return")
    
    # Update status to approved
    updated_return = crud.update_return_status(
        db=db,
        return_id=return_id,
        status="approved",
        admin_notes=f"Approved by seller {current_user.username}"
    )
    
    return updated_return


@router.put("/seller/{return_id}/reject", response_model=schemas.Return)
def reject_return_seller(
    return_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Reject a return request (seller only)"""
    return_request = crud.get_return(db=db, return_id=return_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Verify seller owns the products in this return
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=403, detail="Seller profile not found")
    
    # Check if all items in the return belong to this seller
    for item in return_request.return_items:
        if item.product.seller_id != seller.id:
            raise HTTPException(status_code=403, detail="Not authorized to reject this return")
    
    # Update status to rejected
    notes = f"Rejected by seller {current_user.username}"
    if reason:
        notes += f": {reason}"
    
    updated_return = crud.update_return_status(
        db=db,
        return_id=return_id,
        status="rejected",
        admin_notes=notes
    )
    
    return updated_return


@router.put("/seller/{return_id}/status", response_model=schemas.Return)
def update_return_status_seller(
    return_id: int,
    status: str,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Update return status (seller only)
    
    Valid statuses for sellers: approved, rejected, received, refunded, completed
    """
    valid_statuses = ["approved", "rejected", "received", "refunded", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    return_request = crud.get_return(db=db, return_id=return_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Verify seller owns the products in this return
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=403, detail="Seller profile not found")
    
    # Check if all items in the return belong to this seller
    for item in return_request.return_items:
        if item.product.seller_id != seller.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this return")
    
    # Update status
    admin_notes = notes if notes else f"Updated to {status} by seller {current_user.username}"
    updated_return = crud.update_return_status(
        db=db,
        return_id=return_id,
        status=status,
        admin_notes=admin_notes
    )
    
    return updated_return


@router.get("/{return_id}", response_model=schemas.Return)
def get_return_details(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get details of a specific return request"""
    return_request = crud.get_return(db=db, return_id=return_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Check authorization
    if int(return_request.user_id) != int(current_user.id) and not bool(current_user.is_admin):  # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to view this return")
    
    return return_request


@router.get("/track/{return_number}", response_model=schemas.Return)
def track_return_by_number(
    return_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Track a return request by return number"""
    return_request = crud.get_return_by_number(db=db, return_number=return_number)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Check authorization
    if int(return_request.user_id) != int(current_user.id) and not bool(current_user.is_admin):  # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to view this return")
    
    return return_request


@router.post("/{return_id}/generate-label")
def generate_shipping_label(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Generate a shipping label for the return
    
    In a production system, this would integrate with a shipping provider API
    For now, we'll simulate label generation
    """
    return_request = crud.get_return(db=db, return_id=return_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    if int(return_request.user_id) != int(current_user.id):  # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if return_request.status not in ["initiated", "approved"]:
        raise HTTPException(
            status_code=400,
            detail="Shipping label can only be generated for approved returns"
        )
    
    # Simulate label generation
    tracking_number = f"TRACK-{return_request.return_number}"
    label_url = f"https://example.com/labels/{return_request.return_number}.pdf"
    
    # Update return with shipping info
    update_data = schemas.ReturnUpdate(
        shipping_label_url=label_url,
        tracking_number=tracking_number,
        status="approved"
    )
    
    updated_return = crud.update_return(db=db, return_id=return_id, return_update=update_data)
    
    return {
        "message": "Shipping label generated successfully",
        "label_url": label_url,
        "tracking_number": tracking_number,
        "return": updated_return
    }


# Admin endpoints
@router.get("/admin/all", response_model=List[schemas.Return])
def get_all_returns_admin(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    """Get all return requests (admin only)"""
    returns = crud.get_all_returns(db=db, skip=skip, limit=limit)
    return returns


@router.put("/admin/{return_id}/status", response_model=schemas.Return)
def update_return_status_admin(
    return_id: int,
    status: str,
    admin_notes: str = "",  # Changed from None to empty string
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    """
    Update return status (admin only)
    
    Valid statuses: initiated, approved, rejected, shipped, received, refunded, completed
    """
    valid_statuses = ["initiated", "approved", "rejected", "shipped", "received", "refunded", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    updated_return = crud.update_return_status(
        db=db,
        return_id=return_id,
        status=status,
        admin_notes=admin_notes
    )
    
    if not updated_return:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    return updated_return
