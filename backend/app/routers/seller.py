from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from .. import crud, schemas, auth
from ..database import get_db
from typing import cast
from datetime import datetime

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
    search: str = Query(None, description="Search by product name or category"),
    status: str = Query(None, description="Filter by status: active, inactive, or out_of_stock"),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get current seller's products with optional search and filters"""
    from sqlalchemy import or_
    from ..models import Product, Category
    
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    seller_id = cast(int, seller.id)
    
    # Build query
    query = db.query(Product).filter(Product.seller_id == seller_id)
    
    # Apply search filter
    if search:
        search_term = f"%{search.lower()}%"
        query = query.outerjoin(Category).filter(
            or_(
                Product.title.ilike(search_term),
                Category.name.ilike(search_term)
            )
        )
    
    # Apply status filter
    if status:
        if status == "active":
            query = query.filter(Product.is_active == True, Product.inventory_count > 0)
        elif status == "inactive":
            query = query.filter(Product.is_active == False)
        elif status == "out_of_stock":
            query = query.filter(Product.inventory_count == 0)
    
    # Get products with pagination
    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/orders", response_model=List[schemas.Order])
@router.get("/orders/", response_model=List[schemas.Order])
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
        joinedload(crud.models.Order.order_items).joinedload(crud.models.OrderItem.product),
        joinedload(crud.models.Order.user)
    ).distinct().offset(skip).limit(limit).all()
    
    return orders


@router.get("/orders/{order_id}", response_model=schemas.Order)
def get_seller_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get a specific order by ID if it contains current seller's products"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")

    order = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Order.id == order_id,
        crud.models.Product.seller_id == seller.id
    ).options(
        joinedload(crud.models.Order.order_items).joinedload(crud.models.OrderItem.product),
        joinedload(crud.models.Order.user)
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this seller")

    return order


@router.get("/dashboard")
def get_seller_dashboard(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller),
    since: str | None = Query(None, description="ISO datetime to count new orders since")
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

    # Pending orders count
    pending_orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id,
        crud.models.Order.status == "pending"
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
    
    # New orders since 'since' timestamp (if provided)
    new_orders_since = 0
    if since:
        try:
            # Accept ISO format (with/without Z). Fast parsing without external deps.
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            new_orders_since = db.query(crud.models.Order).join(
                crud.models.OrderItem
            ).join(
                crud.models.Product
            ).filter(
                crud.models.Product.seller_id == seller.id,
                crud.models.Order.created_at >= since_dt
            ).distinct().count()
        except Exception:
            new_orders_since = 0

    return {
        "seller_id": seller.id,
        "store_name": seller.store_name,
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "new_orders_since": new_orders_since,
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
        func.sum(crud.models.OrderItem.quantity).label('total_sold'),
        func.sum(crud.models.OrderItem.total_price).label('total_revenue')
    ).join(
        crud.models.OrderItem
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).group_by(
        crud.models.Product.id, crud.models.Product.title
    ).order_by(
        func.sum(crud.models.OrderItem.quantity).desc()
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


@router.post("/withdraw", response_model=schemas.WithdrawalRequest)
def request_withdrawal(
    req: schemas.WithdrawalRequestCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    seller_balance = getattr(seller, "balance", 0.0)
    seller_id = getattr(seller, "id", 0)
    if req.amount > seller_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    withdrawal = crud.create_withdrawal_request(db=db, seller_id=seller_id, amount=req.amount)
    setattr(seller, "balance", seller_balance - req.amount)
    db.commit()
    return withdrawal


@router.get("/withdrawals", response_model=list[schemas.WithdrawalRequest])
def list_withdrawals(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    seller_id = getattr(seller, "id", 0)
    return crud.get_withdrawal_requests_by_seller(db=db, seller_id=seller_id)

