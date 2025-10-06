from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import crud, schemas, auth, models
from ..database import get_db

router = APIRouter(prefix="/user", tags=["user-stats"])


@router.get("/stats/")
@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get user statistics for profile page"""
    
    # Customer statistics
    total_orders = db.query(models.Order).filter(
        models.Order.user_id == current_user.id
    ).count()
    
    total_spent = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.user_id == current_user.id
    ).scalar() or 0.0
    
    reviews_written = db.query(models.Review).filter(
        models.Review.user_id == current_user.id
    ).count()
    
    customer_stats = {
        "total_orders": total_orders,
        "total_spent": float(total_spent),
        "reviews_written": reviews_written
    }
    
    # Seller statistics (if user is a seller)
    seller_stats = None
    if current_user.is_seller:
        seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
        if seller:
            products_listed = db.query(models.Product).filter(
                models.Product.seller_id == seller.id,
                models.Product.is_active == True
            ).count()
            
            # Count orders that contain seller's products
            orders_received = db.query(models.OrderItem).join(
                models.Product
            ).filter(
                models.Product.seller_id == seller.id
            ).distinct(models.OrderItem.order_id).count()
            
            # Calculate total revenue from seller's products
            total_revenue = db.query(
                func.sum(models.OrderItem.unit_price * models.OrderItem.quantity)
            ).join(models.Product).filter(
                models.Product.seller_id == seller.id
            ).scalar() or 0.0
            
            seller_stats = {
                "products_listed": products_listed,
                "orders_received": orders_received,
                "total_revenue": float(total_revenue)
            }
    
    return {
        "customer_stats": customer_stats,
        "seller_stats": seller_stats
    }


@router.get("/dashboard/")
@router.get("/dashboard")
def get_seller_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get detailed seller dashboard statistics"""
    
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    # Basic counts
    total_products = db.query(models.Product).filter(
        models.Product.seller_id == seller.id
    ).count()
    
    active_products = db.query(models.Product).filter(
        models.Product.seller_id == seller.id,
        models.Product.is_active == True
    ).count()
    
    # Order statistics
    total_orders = db.query(models.OrderItem).join(
        models.Product
    ).filter(
        models.Product.seller_id == seller.id
    ).distinct(models.OrderItem.order_id).count()
    
    # Revenue calculations
    total_revenue = db.query(
        func.sum(models.OrderItem.unit_price * models.OrderItem.quantity)
    ).join(models.Product).filter(
        models.Product.seller_id == seller.id
    ).scalar() or 0.0
    
    # Recent orders (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_orders = db.query(models.OrderItem).join(
        models.Product
    ).join(models.Order).filter(
        models.Product.seller_id == seller.id,
        models.Order.created_at >= thirty_days_ago
    ).distinct(models.OrderItem.order_id).count()
    
    recent_revenue = db.query(
        func.sum(models.OrderItem.unit_price * models.OrderItem.quantity)
    ).join(models.Product).join(models.Order).filter(
        models.Product.seller_id == seller.id,
        models.Order.created_at >= thirty_days_ago
    ).scalar() or 0.0
    
    # Order status breakdown
    order_statuses = db.query(
        models.Order.status,
        func.count(models.Order.id).label('count')
    ).join(models.OrderItem).join(models.Product).filter(
        models.Product.seller_id == seller.id
    ).group_by(models.Order.status).all()
    
    status_breakdown = {status: count for status, count in order_statuses}
    
    # Top selling products
    top_products = db.query(
        models.Product.title,
        func.sum(models.OrderItem.quantity).label('total_sold'),
        func.sum(models.OrderItem.unit_price * models.OrderItem.quantity).label('revenue')
    ).join(models.OrderItem).filter(
        models.Product.seller_id == seller.id
    ).group_by(models.Product.id, models.Product.title).order_by(
        func.sum(models.OrderItem.quantity).desc()
    ).limit(5).all()
    
    top_products_list = [
        {
            "title": title,
            "total_sold": int(total_sold),
            "revenue": float(revenue)
        }
        for title, total_sold, revenue in top_products
    ]
    
    return {
        "overview": {
            "total_products": total_products,
            "active_products": active_products,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "recent_orders": recent_orders,
            "recent_revenue": float(recent_revenue)
        },
        "order_status_breakdown": status_breakdown,
        "top_products": top_products_list
    }
