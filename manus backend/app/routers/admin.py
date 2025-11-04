from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .. import crud, schemas, auth
from ..database import get_db
import math

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin Dashboard Stats
@router.get("/stats", response_model=Dict[str, Any])
def get_admin_stats(
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get total counts
    total_users = db.query(crud.models.User).count()
    total_products = db.query(crud.models.Product).count()
    total_orders = db.query(crud.models.Order).count()
    total_categories = db.query(crud.models.Category).count()
    
    # Get recent activity
    recent_users = db.query(crud.models.User).order_by(crud.models.User.created_at.desc()).limit(5).all()
    recent_orders = db.query(crud.models.Order).order_by(crud.models.Order.created_at.desc()).limit(5).all()
    
    # Calculate revenue
    total_revenue = db.query(crud.models.Order).filter(
        crud.models.Order.status == "delivered"
    ).with_entities(crud.models.Order.total_amount).all()
    total_revenue = sum([order.total_amount for order in total_revenue])
    
    # Convert models to dictionaries for serialization
    recent_users_data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": user.is_active
        }
        for user in recent_users
    ]
    
    recent_orders_data = [
        {
            "id": order.id,
            "user_id": order.user_id,
            "total_amount": float(order.total_amount),
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
        for order in recent_orders
    ]
    
    return {
        "totals": {
            "users": total_users,
            "products": total_products,
            "orders": total_orders,
            "categories": total_categories,
            "revenue": float(total_revenue)
        },
        "recent_users": recent_users_data,
        "recent_orders": recent_orders_data
    }

# User Management
@router.get("/users", response_model=Dict[str, Any])
def get_all_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users with pagination and search"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    query = db.query(crud.models.User)
    
    if search:
        query = query.filter(
            crud.models.User.username.ilike(f"%{search}%") |
            crud.models.User.email.ilike(f"%{search}%") |
            crud.models.User.full_name.ilike(f"%{search}%")
        )
    
    total = query.count()
    users = query.offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert users to dictionaries for serialization
    users_data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_seller": user.is_seller
        }
        for user in users
    ]
    
    return {
        "items": users_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }

@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update user active status"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

# Product Management
@router.get("/products", response_model=Dict[str, Any])
def get_all_products_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products for admin management"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    query = db.query(crud.models.Product)
    
    if search:
        query = query.filter(
            crud.models.Product.title.ilike(f"%{search}%") |
            crud.models.Product.description.ilike(f"%{search}%")
        )
    
    if category_id:
        query = query.filter(crud.models.Product.category_id == category_id)
    
    total = query.count()
    products = query.offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert products to dictionaries for serialization
    products_data = [
        {
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": float(product.price),
            "category_id": product.category_id,
            "seller_id": product.seller_id,
            "inventory_count": product.inventory_count,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "images": product.images
        }
        for product in products
    ]
    
    return {
        "items": products_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }

@router.put("/products/{product_id}/status")
def update_product_status(
    product_id: int,
    is_active: bool,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update product active status"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = is_active
    db.commit()
    db.refresh(product)
    
    return {"message": f"Product {'activated' if is_active else 'deactivated'} successfully"}

@router.delete("/products/{product_id}")
def delete_product_admin(
    product_id: int,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a product"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    db.refresh(product)

    
    return {"message": "Product deleted successfully"}

# Order Management
@router.get("/orders", response_model=Dict[str, Any])
def get_all_orders_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all orders for admin management"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    query = db.query(crud.models.Order)
    
    if status:
        query = query.filter(crud.models.Order.status == status)
    
    total = query.count()
    orders = query.order_by(crud.models.Order.created_at.desc()).offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert orders to dictionaries for serialization
    orders_data = [
        {
            "id": order.id,
            "user_id": order.user_id,
            "total_amount": float(order.total_amount),
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "shipping_address": order.shipping_address,
            "payment_method": order.payment_method
        }
        for order in orders
    ]
    
    return {
        "items": orders_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }

@router.put("/orders/{order_id}/status")
def update_order_status_admin(
    order_id: int,
    status: str,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled", "completed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    order.status = status
    db.commit()
    db.refresh(order)
    
    return {"message": f"Order status updated to {status}"}

# Category Management
@router.post("/categories", response_model=schemas.Category)
def create_category_admin(
    category: schemas.CategoryCreate,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new category"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return crud.create_category(db, category)

@router.put("/categories/{category_id}")
def update_category_admin(
    category_id: int,
    category_update: schemas.CategoryCreate,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a category"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    category = crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category.name = category_update.name
    category.description = category_update.description
    category.slug = category_update.slug
    
    db.commit()
    db.refresh(category)
    
    return category

@router.delete("/categories/{category_id}")
def delete_category_admin(
    category_id: int,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a category"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    category = crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has products
    products_count = db.query(crud.models.Product).filter(crud.models.Product.category_id == category_id).count()
    if products_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category with existing products")
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}


# Message Monitoring
@router.get("/messages", response_model=Dict[str, Any])
def get_all_messages_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for admin monitoring"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    query = db.query(crud.models.Message)
    
    if search:
        # Search in message content or user names
        query = query.join(
            crud.models.User, crud.models.Message.sender_id == crud.models.User.id
        ).filter(
            crud.models.Message.content.ilike(f"%{search}%") |
            crud.models.User.full_name.ilike(f"%{search}%") |
            crud.models.User.username.ilike(f"%{search}%")
        )
    
    total = query.count()
    messages = query.order_by(crud.models.Message.created_at.desc()).offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert messages to dictionaries for serialization
    messages_data = []
    for message in messages:
        sender = crud.get_user(db, message.sender_id)
        receiver = crud.get_user(db, message.receiver_id)
        
        messages_data.append({
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "subject": message.subject,
            "content": message.content,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "full_name": sender.full_name,
                "is_seller": sender.is_seller
            } if sender else None,
            "receiver": {
                "id": receiver.id,
                "username": receiver.username,
                "full_name": receiver.full_name,
                "is_seller": receiver.is_seller
            } if receiver else None,
            "related_order_id": message.related_order_id,
            "related_product_id": message.related_product_id
        })
    
    return {
        "items": messages_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }


@router.get("/conversations", response_model=Dict[str, Any])
def get_all_conversations_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for admin monitoring"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get unique conversation pairs
    conversations_query = db.query(
        crud.models.Message.sender_id,
        crud.models.Message.receiver_id,
        db.func.max(crud.models.Message.created_at).label('last_message_time'),
        db.func.count(crud.models.Message.id).label('message_count')
    ).group_by(
        db.func.least(crud.models.Message.sender_id, crud.models.Message.receiver_id),
        db.func.greatest(crud.models.Message.sender_id, crud.models.Message.receiver_id)
    ).order_by(db.func.max(crud.models.Message.created_at).desc())
    
    skip = (page - 1) * per_page
    total = conversations_query.count()
    conversations = conversations_query.offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert conversations to dictionaries
    conversations_data = []
    for conv in conversations:
        user1 = crud.get_user(db, conv.sender_id)
        user2 = crud.get_user(db, conv.receiver_id)
        
        # Get latest message
        latest_message = db.query(crud.models.Message).filter(
            ((crud.models.Message.sender_id == conv.sender_id) & (crud.models.Message.receiver_id == conv.receiver_id)) |
            ((crud.models.Message.sender_id == conv.receiver_id) & (crud.models.Message.receiver_id == conv.sender_id))
        ).order_by(crud.models.Message.created_at.desc()).first()
        
        conversations_data.append({
            "user1": {
                "id": user1.id,
                "username": user1.username,
                "full_name": user1.full_name,
                "is_seller": user1.is_seller
            } if user1 else None,
            "user2": {
                "id": user2.id,
                "username": user2.username,
                "full_name": user2.full_name,
                "is_seller": user2.is_seller
            } if user2 else None,
            "message_count": conv.message_count,
            "last_message_time": conv.last_message_time.isoformat() if conv.last_message_time else None,
            "latest_message": {
                "content": latest_message.content,
                "sender_id": latest_message.sender_id,
                "created_at": latest_message.created_at.isoformat() if latest_message.created_at else None
            } if latest_message else None
        })
    
    return {
        "items": conversations_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }


@router.get("/conversations/{user1_id}/{user2_id}/messages")
def get_conversation_messages_admin(
    user1_id: int,
    user2_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages between two specific users for admin monitoring"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    skip = (page - 1) * per_page
    
    # Get messages between the two users
    query = db.query(crud.models.Message).filter(
        ((crud.models.Message.sender_id == user1_id) & (crud.models.Message.receiver_id == user2_id)) |
        ((crud.models.Message.sender_id == user2_id) & (crud.models.Message.receiver_id == user1_id))
    )
    
    total = query.count()
    messages = query.order_by(crud.models.Message.created_at.asc()).offset(skip).limit(per_page).all()
    pages = math.ceil(total / per_page) if total > 0 else 0
    
    # Convert messages to dictionaries
    messages_data = []
    for message in messages:
        sender = crud.get_user(db, message.sender_id)
        receiver = crud.get_user(db, message.receiver_id)
        
        messages_data.append({
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "full_name": sender.full_name
            } if sender else None,
            "receiver": {
                "id": receiver.id,
                "username": receiver.username,
                "full_name": receiver.full_name
            } if receiver else None
        })
    
    return {
        "items": messages_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages
    }


@router.delete("/messages/{message_id}")
def delete_message_admin(
    message_id: int,
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    message = db.query(crud.models.Message).filter(crud.models.Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}



@router.get("/analytics", response_model=Dict[str, Any])
def get_analytics(
    time_range: str = Query("7d"),
    current_user: schemas.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics data for admin dashboard"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    end_date = datetime.now()
    if time_range == "7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "30d":
        start_date = end_date - timedelta(days=30)
    elif time_range == "90d":
        start_date = end_date - timedelta(days=90)
    elif time_range == "365d":
        start_date = end_date - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Invalid time range")

    # Sales over time
    sales_over_time = db.query(
        func.date(crud.models.Order.created_at).label("date"),
        func.sum(crud.models.Order.total_amount).label("total_sales")
    ).filter(
        crud.models.Order.created_at >= start_date,
        crud.models.Order.status == "delivered"
    ).group_by("date").order_by("date").all()

    # Orders over time
    orders_over_time = db.query(
        func.date(crud.models.Order.created_at).label("date"),
        func.count(crud.models.Order.id).label("total_orders")
    ).filter(
        crud.models.Order.created_at >= start_date
    ).group_by("date").order_by("date").all()

    # Top products by sales
    top_products = db.query(
        crud.models.Product.title.label("product_title"),
        func.sum(crud.models.OrderItem.quantity * crud.models.OrderItem.price).label("total_sales")
    ).join(
        crud.models.OrderItem, crud.models.Product.id == crud.models.OrderItem.product_id
    ).join(
        crud.models.Order, crud.models.OrderItem.order_id == crud.models.Order.id
    ).filter(
        crud.models.Order.created_at >= start_date,
        crud.models.Order.status == "delivered"
    ).group_by("product_title").order_by(func.sum(crud.models.OrderItem.quantity * crud.models.OrderItem.price).desc()).limit(5).all()

    # User growth
    user_growth = db.query(
        func.date(crud.models.User.created_at).label("date"),
        func.count(crud.models.User.id).label("new_users")
    ).filter(
        crud.models.User.created_at >= start_date
    ).group_by("date").order_by("date").all()

    # Order status distribution
    order_status_distribution = db.query(
        crud.models.Order.status,
        func.count(crud.models.Order.id).label("count")
    ).filter(
        crud.models.Order.created_at >= start_date
    ).group_by(crud.models.Order.status).all()

    return {
        "sales_over_time": [{
            "date": s.date.isoformat(),
            "total_sales": float(s.total_sales)
        } for s in sales_over_time],
        "orders_over_time": [{
            "date": o.date.isoformat(),
            "total_orders": o.total_orders
        } for o in orders_over_time],
        "top_products": [{
            "product_title": tp.product_title,
            "total_sales": float(tp.total_sales)
        } for tp in top_products],
        "user_growth": [{
            "date": ug.date.isoformat(),
            "new_users": ug.new_users
        } for ug in user_growth],
        "order_status_distribution": {
            os.status: os.count for os in order_status_distribution
        }
    }

