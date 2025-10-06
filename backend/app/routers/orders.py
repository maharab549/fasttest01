from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth
from ..database import get_db
from .notifications import create_notification

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=schemas.Order)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create a new order"""
    # Validate all products exist and are available
    for item in order.items:
        product = crud.get_product(db=db, product_id=item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product.title} is not available")
        
        if item.quantity > product.inventory_count:
            raise HTTPException(
                status_code=400,
                detail=f"Only {product.inventory_count} items available for {product.title}"
            )
        
        # Set unit price from product
        item.unit_price = product.price
    
    # Create the order
    db_order = crud.create_order(db=db, order=order, user_id=current_user.id)
    
    # Create notification for order placement
    create_notification(
        db=db,
        user_id=current_user.id,
        title=f"Order #{db_order.order_number} Placed Successfully",
        message=f"Your order for ${db_order.total_amount:.2f} has been placed and is awaiting confirmation.",
        notification_type="new_order",
        related_order_id=db_order.id
    )
    
    # Update inventory
    for item in order.items:
        product = crud.get_product(db=db, product_id=item.product_id)
        if product:
            product.inventory_count -= item.quantity
            db.commit()
    
    # Clear cart after successful order
    crud.clear_cart(db=db, user_id=current_user.id)
    
    return db_order


@router.get("/", response_model=List[schemas.Order])
def get_user_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get current user's orders"""
    orders = crud.get_orders_by_user(db=db, user_id=current_user.id, skip=skip, limit=limit)
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get order by ID"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order


@router.put("/{order_id}/status", response_model=schemas.Order)
def update_order_status(
    order_id: int,
    status_data: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Update order status (seller only)"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if seller owns any products in this order
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")
    
    # Verify seller has products in this order
    seller_has_products = any(
        item.product.seller_id == seller.id 
        for item in order.order_items 
        if item.product
    )
    
    if not seller_has_products:
        raise HTTPException(status_code=403, detail="Not authorized to update this order")
    
    # Valid status transitions
    valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
    if status_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    updated_order = crud.update_order_status(db=db, order_id=order_id, status=status_data.status)

    if updated_order:
        # Create a notification for the user who placed the order
        create_notification(
            db=db,
            user_id=updated_order.user_id,
            title=f"Order #{updated_order.order_number} Status Updated",
            message=f"Your order status has been updated to: {updated_order.status.capitalize()}",
            notification_type="order_update",
            related_order_id=updated_order.id
        )

    return updated_order


@router.get("/{order_id}/track/")
@router.get("/{order_id}/track")
def track_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Track order status"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to track this order")
    
    # Order status timeline
    status_timeline = {
        "pending": "Order placed and awaiting confirmation",
        "confirmed": "Order confirmed by seller",
        "processing": "Order is being prepared",
        "shipped": "Order has been shipped",
        "delivered": "Order has been delivered",
        "cancelled": "Order has been cancelled"
    }
    
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "status_description": status_timeline.get(order.status, "Unknown status"),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "total_amount": order.total_amount
    }

