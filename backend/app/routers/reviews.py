from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth, models
from ..database import get_db

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
    
    # Check if product exists
    product = crud.get_product(db=db, product_id=review.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user has a delivered order containing this product
    delivered_order = db.query(models.Order).join(
        models.OrderItem
    ).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == "delivered",
        models.OrderItem.product_id == review.product_id
    ).first()
    
    if not delivered_order:
        raise HTTPException(
            status_code=400, 
            detail="You can only review products from delivered orders"
        )
    
    # Check if user already reviewed this product
    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == review.product_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=400, 
            detail="You have already reviewed this product"
        )
    
    # Validate rating
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(
            status_code=400, 
            detail="Rating must be between 1 and 5"
        )
    
    # Create the review
    db_review = models.Review(
        user_id=current_user.id,
        product_id=review.product_id,
        order_id=delivered_order.id,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        is_verified_purchase=True,
        is_approved=True  # Auto-approve for now
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Update product rating
    crud.update_product_rating(db=db, product_id=review.product_id)
    
    return db_review


@router.get("/reviewable-products")
def get_reviewable_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get products that the user can review (from delivered orders, not yet reviewed)"""
    
    # Get delivered orders for the user
    delivered_orders = db.query(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == "delivered"
    ).all()
    
    if not delivered_orders:
        return {"data": [], "total": 0}
    
    # Get all product IDs from delivered orders
    delivered_product_ids = []
    for order in delivered_orders:
        for item in order.order_items:
            delivered_product_ids.append(item.product_id)
    
    # Remove duplicates
    delivered_product_ids = list(set(delivered_product_ids))
    
    # Get product IDs that user has already reviewed
    reviewed_product_ids = db.query(models.Review.product_id).filter(
        models.Review.user_id == current_user.id
    ).all()
    reviewed_product_ids = [pid[0] for pid in reviewed_product_ids]
    
    # Get reviewable product IDs (delivered but not reviewed)
    reviewable_product_ids = [
        pid for pid in delivered_product_ids 
        if pid not in reviewed_product_ids
    ]
    
    if not reviewable_product_ids:
        return {"data": [], "total": 0}
    
    # Get the actual products
    products = db.query(models.Product).filter(
        models.Product.id.in_(reviewable_product_ids)
    ).offset(skip).limit(limit).all()
    
    return {
        "data": products,
        "total": len(reviewable_product_ids)
    }


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Delete a review (only by the review author)"""
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not authorized")
    
    db.delete(review)
    db.commit()
    
    return {"message": "Review deleted successfully"}


@router.put("/{review_id}")
def update_review(
    review_id: int,
    review_update: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Update a review (only by the review author)"""
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not authorized")
    
    # Update review fields
    review.rating = review_update.rating
    review.title = review_update.title
    review.comment = review_update.comment
    
    db.commit()
    db.refresh(review)
    
    return review


@router.get("/user/{product_id}")
@router.get("/user/{product_id}/")
def get_user_product_review(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get the current user's review for a specific product.
    Returns the review object or null if no review exists.
    """
    review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == product_id
    ).first()
    return review

