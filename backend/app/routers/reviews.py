from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth, models
from ..database import get_db
import os
from uuid import uuid4

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/can-review/{product_id}")
def can_review_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Check if user can review a product (has delivered order and hasn't reviewed yet)"""
    
    # Check if product exists
    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user has a delivered order containing this product
    delivered_order = db.query(models.Order).join(
        models.OrderItem
    ).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == "delivered",
        models.OrderItem.product_id == product_id
    ).first()
    
    # Check if user already reviewed this product
    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == product_id
    ).first()
    
    can_review = delivered_order is not None and existing_review is None
    
    return {
        "can_review": can_review,
        "has_delivered_order": delivered_order is not None,
        "already_reviewed": existing_review is not None,
        "order_id": delivered_order.id if delivered_order else None,
        "message": (
            "You can review this product" if can_review else
            "You have already reviewed this product" if existing_review else
            "You can only review products from delivered orders"
        )
    }


@router.get("/user-reviews")
def get_user_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get reviews written by the current user"""
    reviews = db.query(models.Review).filter(
        models.Review.user_id == current_user.id
    ).order_by(models.Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "data": reviews,
        "total": db.query(models.Review).filter(
            models.Review.user_id == current_user.id
        ).count()
    }


@router.post("/", response_model=schemas.Review)
def create_review(
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create a new review for a product"""
    # Validate product exists
    product = crud.get_product(db=db, product_id=review.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # If order_id provided, validate the order belongs to the user and is delivered
    if review.order_id:
        order = crud.get_order(db=db, order_id=review.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if int(order.user_id) != int(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to review this order")
        if order.status != "delivered":
            raise HTTPException(status_code=400, detail="Only delivered orders can be reviewed")

    # Prevent duplicate reviews for same product by same user
    existing = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == review.product_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    # Create review
    created = crud.create_review(db=db, review=review, user_id=current_user.id)
    return created
