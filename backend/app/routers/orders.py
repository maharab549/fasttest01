from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .. import crud, schemas, auth, models
from ..database import get_db
from .notifications import create_notification
from typing import cast
import json

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=schemas.Order)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create a new order with optional discount code"""
    from datetime import datetime
    
    # Validate discount code if provided
    discount_amount = 0.0
    applied_redemption_id = None
    
    if order.discount_code:
        # Get user's loyalty account
        loyalty_account = crud.get_loyalty_account_by_user(db, current_user.id)
        if not loyalty_account:
            raise HTTPException(
                status_code=404,
                detail="Loyalty account not found"
            )
        
        # Find redemption with this code
        redemption = db.query(models.Redemption).filter(
            models.Redemption.reward_code == order.discount_code.strip(),
            models.Redemption.loyalty_account_id == int(loyalty_account.id)  # type: ignore
        ).first()
        
        if not redemption:
            raise HTTPException(
                status_code=404,
                detail="Discount code not found"
            )
        
        # Validate redemption status
        redemption_status = getattr(redemption, "status", None)
        if redemption_status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"This code is no longer {redemption_status}"
            )
        
        # Check if expired
        expires_at = getattr(redemption, "expires_at", None)
        if expires_at is not None and expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="This code has expired"
            )
        
        # Get discount amount
        discount_amount = float(getattr(redemption, "reward_value", 0))
        applied_redemption_id = int(getattr(redemption, "id", 0))  # type: ignore
    
    # Validate all products exist and are available
    # Collect seller notifications context: seller_user_id -> list of item summaries
    seller_items_map = {}
    for item in order.items:
        product = crud.get_product(db=db, product_id=item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        product_typed = cast(models.Product, product)
        is_active = cast(bool, product_typed.is_active)
        if is_active is False:
            raise HTTPException(status_code=400, detail=f"Product {product.title} is not available")
        
        inventory = cast(int, product_typed.inventory_count)
        if int(item.quantity) > inventory:
            raise HTTPException(
                status_code=400,
                detail=f"Only {inventory} items available for {product.title}"
            )
        
        # Set unit price from product
        unit_price_val = cast(float, product_typed.price)
        item.unit_price = unit_price_val

        # Track items per seller for notifications
        try:
            if product.seller and product.seller.user_id:
                sid = int(product.seller.user_id)
                entry = seller_items_map.setdefault(sid, [])
                entry.append({
                    "title": getattr(product, "title", str(product.id)),
                    "quantity": int(item.quantity)
                })
        except Exception:
            # best-effort, continue
            pass
    
    # Create the order (this calculates totals)
    db_order = crud.create_order(db=db, order=order, user_id=current_user.id)
    
    # Apply discount if provided
    if discount_amount > 0 and applied_redemption_id:
        # Update order with discount
        setattr(db_order, "discount_amount", discount_amount)
        discount_code_str = order.discount_code.strip() if order.discount_code else ""
        setattr(db_order, "discount_code", discount_code_str)
        setattr(db_order, "applied_redemption_id", applied_redemption_id)
        
        # Recalculate total after discount
        current_total = cast(float, getattr(db_order, "total_amount", 0))
        new_total = max(0.0, current_total - discount_amount)
        setattr(db_order, "total_amount", new_total)
        
        # Mark redemption as used
        redemption = db.query(models.Redemption).filter(
            models.Redemption.id == applied_redemption_id
        ).first()
        if redemption:
            setattr(redemption, "status", "used")
            setattr(redemption, "order_id", int(getattr(db_order, "id", 0)))  # type: ignore
            setattr(redemption, "used_at", datetime.utcnow())
        
        db.commit()
        db.refresh(db_order)
    
    # Create notification for order placement
    create_notification(
        db=db,
        user_id=current_user.id,
        title=f"Order #{db_order.order_number} Placed Successfully",
        message=f"Your order for ${cast(float, db_order.total_amount):.2f} has been placed and is awaiting confirmation.",
        notification_type="new_order",
        related_order_id=cast(int, db_order.id)
    )
    
    # Update inventory
    for item in order.items:
        product = crud.get_product(db=db, product_id=item.product_id)
        if product:
            inv_now = cast(int, product.inventory_count)
            new_inv = int(inv_now - int(item.quantity))
            setattr(product, "inventory_count", new_inv)
            db.commit()
    
    # Clear cart after successful order
    crud.clear_cart(db=db, user_id=current_user.id)
    
    # Award loyalty points for the purchase (1 point per $100 spent on final amount)
    loyalty_account = crud.get_loyalty_account_by_user(db, current_user.id)
    if loyalty_account:
        final_amount = cast(float, getattr(db_order, "total_amount", 0))
        points_earned = int(final_amount / 100)  # 1 point per $100
        crud.award_points(
            db=db,
            loyalty_account_id=cast(int, loyalty_account.id),  # type: ignore
            points=points_earned,
            source="purchase",
            source_id=str(getattr(db_order, "id", 0)),
            description=f"Earned {points_earned} points from order #{getattr(db_order, 'order_number', 'Unknown')}",
            metadata={"order_number": getattr(db_order, "order_number", ""), "order_amount": final_amount}
        )
    
    # Notify each seller with items included in the order
    try:
        for seller_user_id, items in seller_items_map.items():
            # Summarize items: up to 3 titles + count
            titles = ", ".join([i["title"] for i in items[:3]])
            more = len(items) - 3
            if more > 0:
                titles += f" and {more} more"
            total_qty = sum(i["quantity"] for i in items)
            create_notification(
                db=db,
                user_id=seller_user_id,
                title=f"New order #{db_order.order_number}",
                message=f"You sold {total_qty} item(s): {titles}",
                notification_type="seller_new_order",
                related_order_id=cast(int, db_order.id)
            )
    except Exception:
        # best-effort
        pass
    
    return db_order

    


@router.get("/", response_model=List[schemas.Order])
@router.get("", response_model=List[schemas.Order])
def get_user_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get current user's orders"""
    print(f"[orders.py] 🔍 get_user_orders called: user_id={current_user.id}, skip={skip}, limit={limit}")
    orders = crud.get_orders_by_user(db=db, user_id=current_user.id, skip=skip, limit=limit)
    print(f"[orders.py] 📦 Found {len(orders)} orders for user {current_user.id}")
    for i, o in enumerate(orders):
        print(f"[orders.py]   Order {i}: id={o.id}, order_number={o.order_number}, status={o.status}, user_id={o.user_id}")
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
@router.get("/{order_id}/", response_model=schemas.Order)
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
    if cast(int, order.user_id) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order


@router.put("/{order_id}/status", response_model=schemas.Order)
@router.put("/{order_id}/status/", response_model=schemas.Order)
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
            user_id=cast(int, updated_order.user_id),
            title=f"Order #{updated_order.order_number} Status Updated",
            message=f"Your order status has been updated to: {updated_order.status.capitalize()}",
            notification_type="order_update",
            related_order_id=cast(int, updated_order.id)
        )

        # If order is delivered, also prompt the user to leave a review
        if cast(str, updated_order.status) == "delivered":
            create_notification(
                db=db,
                user_id=cast(int, updated_order.user_id),
                title=f"Order #{updated_order.order_number} Delivered",
                message=(
                    "Your order was delivered successfully. We'd love to hear your feedback — "
                    "please leave a review for the items you received."
                ),
                notification_type="review_request",
                related_order_id=cast(int, updated_order.id)
            )

    return updated_order


@router.get("/seller/orders/{order_id}", response_model=schemas.Order)
def get_seller_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_user)
):
    """Get order details for seller - seller can view orders containing their products"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if seller has products in this order
    seller_has_products = any(
        item.product and item.product.seller_id == current_user.id
        for item in order.order_items
    )
    
    if not seller_has_products and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order


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
    if cast(int, order.user_id) != current_user.id:
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
    "status_description": status_timeline.get(cast(str, order.status), "Unknown status"),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "total_amount": order.total_amount
    }


@router.get("/delivered", response_model=List[schemas.Order])
@router.get("/delivered/", response_model=List[schemas.Order])
def get_delivered_orders(
    product_id: Optional[int] = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get delivered orders for the current user. If product_id is provided,
    only return delivered orders that contain that product.
    """
    query = db.query(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == "delivered"
    )

    if product_id is not None:
        # Join with order items to ensure the order contains the product
        query = query.join(models.OrderItem).filter(
            models.OrderItem.product_id == product_id
        )

    orders = query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.put("/{order_id}/cancel", response_model=schemas.Order)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Cancel an order (user only, if not shipped/delivered/refunded)"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if getattr(order, "user_id", None) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    if order.status in ["shipped", "delivered", "cancelled"] or order.payment_status == "refunded":
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")
    updated_order = crud.update_order_status(db=db, order_id=order_id, status="cancelled")
    if updated_order:
        create_notification(
            db=db,
            user_id=int(getattr(updated_order, "user_id", 0)),
            title=f"Order #{updated_order.order_number} Cancelled",
            message="Your order has been cancelled.",
            notification_type="order_cancelled",
            related_order_id=int(getattr(updated_order, "id", 0))
        )
    return updated_order


class OrderEditRequest(BaseModel):
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    items: Optional[List[Dict[str, Any]]] = None  # Each item: {order_item_id, quantity}


@router.put("/{order_id}/edit", response_model=schemas.Order)
def edit_order(
    order_id: int,
    edit_data: OrderEditRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Edit an order (user only, if not shipped/delivered/refunded)"""
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if getattr(order, "user_id", None) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this order")
    if getattr(order, "status", None) in ["shipped", "delivered", "cancelled"] or getattr(order, "payment_status", None) == "refunded":
        raise HTTPException(status_code=400, detail="Order cannot be edited at this stage")
    # Update address
    if edit_data.shipping_address:
        setattr(order, "shipping_address", edit_data.shipping_address)
    if edit_data.billing_address:
        setattr(order, "billing_address", edit_data.billing_address)
    # Update items/quantities
    if edit_data.items:
        for item_update in edit_data.items:
            order_item = next((oi for oi in order.order_items if oi.id == item_update.get("order_item_id")), None)
            if order_item:
                new_qty = item_update.get("quantity")
                if new_qty and new_qty > 0:
                    order_item.quantity = new_qty
    db.commit()
    db.refresh(order)
    # Log and notify
    create_notification(
        db=db,
        user_id=int(getattr(order, "user_id", 0)),
        title=f"Order #{order.order_number} Edited",
        message="Your order details have been updated.",
        notification_type="order_edited",
        related_order_id=int(getattr(order, "id", 0))
    )
    return order


@router.post("/validate-discount")
def validate_discount_code(
    code: str = Query(..., description="Discount code to validate"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Validate a discount code and return discount amount
    
    The code must belong to the current user and be:
    - Status: active
    - Not expired
    - Not already used
    
    Returns discount amount and redemption details
    """
    from datetime import datetime
    
    try:
        # Get user's loyalty account
        loyalty_account = crud.get_loyalty_account_by_user(db, int(current_user.id))  # type: ignore
        if not loyalty_account:
            raise HTTPException(
                status_code=404,
                detail="Loyalty account not found"
            )
        
        # Get redemption with this code
        redemption = db.query(models.Redemption).filter(
            models.Redemption.reward_code == code.strip(),
            models.Redemption.loyalty_account_id == int(loyalty_account.id)  # type: ignore
        ).first()
        
        if not redemption:
            raise HTTPException(
                status_code=404,
                detail="Discount code not found or does not belong to you"
            )
        
        # Check if code is active
        redemption_status = getattr(redemption, "status", None)
        if redemption_status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"This code is no longer {redemption_status}"
            )
        
        # Check if code is expired
        expires_at = getattr(redemption, "expires_at", None)
        if expires_at is not None and expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="This code has expired"
            )
        
        # Return discount details
        reward_value = getattr(redemption, "reward_value", 0)
        redemption_id = getattr(redemption, "id", 0)
        
        return {
            "valid": True,
            "code": code.strip(),
            "discount_amount": float(reward_value),
            "redemption_type": getattr(redemption, "redemption_type", "discount_code"),
            "redemption_id": int(redemption_id),
            "message": f"${reward_value} discount applied!"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error validating code: {str(e)}"
        )

