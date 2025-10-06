from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/seller", tags=["seller"])


@router.get("/profile", response_model=schemas.Seller)
def get_seller_profile(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get current seller's profile"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    return seller


@router.get("/products", response_model=List[schemas.Product])
def get_seller_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get current seller's products"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    products = crud.get_products_by_seller(db=db, seller_id=seller.id, skip=skip, limit=limit)
    return products


@router.get("/orders", response_model=List[schemas.Order])
def get_seller_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get orders containing seller's products"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    # Get orders that contain products from this seller
    orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).options(
        joinedload(crud.models.Order.order_items).joinedload(crud.models.OrderItem.product)
    ).distinct().offset(skip).limit(limit).all()
    
    return orders


@router.get("/dashboard")
def get_seller_dashboard(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get seller dashboard statistics"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    # Get statistics
    total_products = db.query(crud.models.Product).filter(
        crud.models.Product.seller_id == seller.id
    ).count()
    
    active_products = db.query(crud.models.Product).filter(
        crud.models.Product.seller_id == seller.id,
        crud.models.Product.is_active == True
    ).count()
    
    # Get orders containing seller's products
    total_orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).distinct().count()
    
    # Calculate total revenue
    from sqlalchemy import func
    total_revenue = db.query(
        func.sum(crud.models.OrderItem.total_price)
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).scalar() or 0
    
    return {
        "seller_id": seller.id,
        "store_name": seller.store_name,
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "rating": seller.rating,
        "total_sales": seller.total_sales,
        "is_verified": seller.is_verified
    }


@router.get("/analytics")
def get_seller_analytics(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get seller analytics data"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    # Get top selling products
    top_products = db.query(
        crud.models.Product.title,
        db.func.sum(crud.models.OrderItem.quantity).label('total_sold'),
        db.func.sum(crud.models.OrderItem.total_price).label('total_revenue')
    ).join(
        crud.models.OrderItem
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).group_by(
        crud.models.Product.id, crud.models.Product.title
    ).order_by(
        db.func.sum(crud.models.OrderItem.quantity).desc()
    ).limit(10).all()
    
    # Get recent orders
    recent_orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).distinct().order_by(
        crud.models.Order.created_at.desc()
    ).limit(10).all()
    
    return {
        "top_products": [
            {
                "title": product.title,
                "total_sold": product.total_sold,
                "total_revenue": float(product.total_revenue)
            }
            for product in top_products
        ],
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
                "created_at": order.created_at
            }
            for order in recent_orders
        ]
    }

