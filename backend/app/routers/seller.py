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
    
    # Convert image IDs to URLs (same logic as get_product endpoint)
    from ..models import ProductImage
    result = []
    for product in products:
        product_dict = {
            "id": product.id,
            "seller_id": product.seller_id,
            "category_id": product.category_id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "short_description": product.short_description,
            "price": product.price,
            "compare_price": product.compare_price,
            "sku": product.sku,
            "inventory_count": product.inventory_count,
            "weight": product.weight,
            "dimensions": product.dimensions,
            "images": [],
            "is_active": product.is_active,
            "is_featured": product.is_featured,
            "has_variants": product.has_variants,
            "rating": product.rating,
            "review_count": product.review_count,
            "view_count": product.view_count,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "approval_status": product.approval_status,
            "rejection_reason": product.rejection_reason,
            "approved_at": product.approved_at,
            "approved_by": product.approved_by,
            "variants": product.variants or [],
            "seller": product.seller,
        }
        
        # Fetch actual image URLs from ProductImage table
        if product.images is not None:
            image_ids = product.images if isinstance(product.images, list) else []
            try:
                if len(image_ids) > 0:
                    product_images = db.query(ProductImage).filter(
                        ProductImage.id.in_(image_ids)
                    ).all()
                    product_dict["images"] = [img.image_url for img in product_images] if product_images else []
            except Exception:
                product_dict["images"] = []
        
        result.append(product_dict)
    
    return result


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
    ).order_by(crud.models.Order.created_at.desc()).distinct().offset(skip).limit(limit).all()
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

    # Calculate available balance: 90% of total revenue after 10% commission
    available_balance = total_revenue * 0.90
    
    # Subtract already withdrawn amounts (pending, approved, and paid)
    already_withdrawn = db.query(
        func.sum(crud.models.WithdrawalRequest.amount)
    ).filter(
        crud.models.WithdrawalRequest.seller_id == seller.id,
        crud.models.WithdrawalRequest.status.in_(["pending", "approved", "paid"])
    ).scalar() or 0
    
    # Remaining balance after deducting pending/approved withdrawals
    remaining_balance = available_balance - already_withdrawn

    return {
        "seller_id": seller.id,
        "store_name": seller.store_name,
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "new_orders_since": new_orders_since,
        "total_revenue": total_revenue,
        "balance": remaining_balance,
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
    
    seller_id = getattr(seller, "id", 0)
    
    # Ensure payout info exists
    if not (seller.payout_method and (seller.payout_method == "paypal" and seller.paypal_email or seller.payout_method == "bank_transfer" and seller.bank_account_number)):
        raise HTTPException(status_code=400, detail="Please add payout/bank information before requesting a withdrawal")

    # Calculate available balance: 90% of total revenue after 10% commission
    total_revenue = db.query(
        func.sum(crud.models.OrderItem.total_price)
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Product.seller_id == seller.id
    ).scalar() or 0
    
    available_balance = total_revenue * 0.90
    
    # Subtract already withdrawn amounts (pending and approved)
    already_withdrawn = db.query(
        func.sum(crud.models.WithdrawalRequest.amount)
    ).filter(
        crud.models.WithdrawalRequest.seller_id == seller.id,
        crud.models.WithdrawalRequest.status.in_(["pending", "approved", "paid"])
    ).scalar() or 0
    
    remaining_balance = available_balance - already_withdrawn
    
    if req.amount > remaining_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    withdrawal = crud.create_withdrawal_request(db=db, seller_id=seller_id, amount=req.amount)
    
    # Update seller's balance column for tracking
    seller.balance = remaining_balance - req.amount
    db.commit()
    
    return withdrawal


@router.get("/payout-info")
def get_payout_info(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get seller payout information"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    return {
        "payout_method": getattr(seller, "payout_method", None),
        "bank_account_number": getattr(seller, "bank_account_number", None),
        "bank_routing_number": getattr(seller, "bank_routing_number", None),
        "bank_account_name": getattr(seller, "bank_account_name", None),
        "bank_name": getattr(seller, "bank_name", None),
        "paypal_email": getattr(seller, "paypal_email", None),
        "stripe_email": getattr(seller, "stripe_email", None),
    }


@router.put("/payout-info")
def update_payout_info_put(
    payout: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Update seller payout information (bank or paypal). Example payload:
    {"method_type": "bank_transfer", "bank_code": "SWIFT_CODE", "account_holder_name": "John Doe", "bank_account": "IBAN", "email": "seller@example.com"}
    or
    {"method_type": "paypal", "email": "seller@paypal.com"}
    or
    {"method_type": "stripe", "email": "seller@stripe.com"}
    """
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")

    # Map frontend field names to backend field names
    method_type = payout.get("method_type", "bank_transfer")
    
    # Validate method type
    if method_type not in ("bank_transfer", "paypal", "stripe"):
        raise HTTPException(status_code=400, detail="Invalid payment method type")
    
    # Set payout method
    setattr(seller, "payout_method", method_type)
    
    if method_type == "bank_transfer":
        # Validate required fields
        if not all([payout.get("bank_account"), payout.get("bank_code"), payout.get("account_holder_name")]):
            raise HTTPException(status_code=400, detail="Bank transfer requires bank_account, bank_code, and account_holder_name")
        
        setattr(seller, "bank_account_number", payout.get("bank_account"))
        setattr(seller, "bank_routing_number", payout.get("bank_code"))
        setattr(seller, "bank_account_name", payout.get("account_holder_name"))
        
    elif method_type in ("paypal", "stripe"):
        if not payout.get("email"):
            raise HTTPException(status_code=400, detail=f"{method_type.capitalize()} requires email")
        
        if method_type == "paypal":
            setattr(seller, "paypal_email", payout.get("email"))
        else:  # stripe
            setattr(seller, "stripe_email", payout.get("email"))
    
    db.commit()
    db.refresh(seller)
    return {"message": "Payment method updated successfully", "payout_method": method_type}



@router.put("/withdraw/{withdrawal_id}/cancel")
def cancel_withdrawal_endpoint(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")

    # Ensure the withdrawal belongs to this seller
    wd = crud.get_withdrawal(db=db, withdrawal_id=withdrawal_id)
    if not wd or wd.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Withdrawal not found")

    cancelled = crud.cancel_withdrawal(db=db, withdrawal_id=withdrawal_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Unable to cancel withdrawal (maybe already processed)")
    return cancelled


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

