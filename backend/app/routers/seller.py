from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Any, List
from .. import crud, schemas, auth
from ..database import get_db
from ..media_paths import make_absolute_media_url
from typing import cast
from datetime import datetime
import json

router = APIRouter(prefix="/seller", tags=["seller"])


def _seller_product_filter(current_user_id: int, seller_id: int):
    """Support both normalized and legacy product ownership mapping.

    Normalized data uses products.seller_id == sellers.id.
    Some legacy datasets used products.seller_id == users.id.
    """
    return or_(
        crud.models.Product.seller_id == seller_id,
        crud.models.Product.seller_id == current_user_id
    )


def _serialize_dt(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _normalize_address(value: Any) -> Any:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"address": text}
    return {"address": str(value)}


def _extract_product_image_urls(product: Any, db: Session) -> list[str]:
    image_urls: list[str] = []
    images = getattr(product, "images", None)

    parsed_images: list[Any] = []
    if isinstance(images, list):
        parsed_images = images
    elif isinstance(images, str) and images.strip():
        try:
            parsed = json.loads(images)
            if isinstance(parsed, list):
                parsed_images = parsed
            else:
                parsed_images = [images]
        except Exception:
            parsed_images = [images]

    if not parsed_images:
        return image_urls

    if all(isinstance(x, int) for x in parsed_images):
        image_ids = cast(list[int], parsed_images)
        product_images = db.query(crud.models.ProductImage).filter(
            crud.models.ProductImage.id.in_(image_ids)
        ).all()
        id_to_url = {
            int(img.id): make_absolute_media_url(getattr(img, "image_url", ""))
            for img in product_images
        }
        return [id_to_url[i] for i in image_ids if i in id_to_url]

    for entry in parsed_images:
        if entry is None:
            continue
        url = make_absolute_media_url(str(entry))
        if url:
            image_urls.append(url)
    return image_urls


def _serialize_product_for_order(product: Any, db: Session) -> dict[str, Any]:
    image_urls = _extract_product_image_urls(product, db)
    return {
        "id": getattr(product, "id", 0),
        "seller_id": getattr(product, "seller_id", 0),
        "category_id": getattr(product, "category_id", 0),
        "title": getattr(product, "title", ""),
        "slug": getattr(product, "slug", ""),
        "description": getattr(product, "description", ""),
        "short_description": getattr(product, "short_description", ""),
        "price": float(getattr(product, "price", 0) or 0),
        "compare_price": (
            float(getattr(product, "compare_price", 0))
            if getattr(product, "compare_price", None) is not None
            else None
        ),
        "sku": getattr(product, "sku", ""),
        "inventory_count": int(getattr(product, "inventory_count", 0) or 0),
        "images": image_urls,
        "primary_image_url": image_urls[0] if image_urls else None,
        "is_active": bool(getattr(product, "is_active", False)),
        "is_featured": bool(getattr(product, "is_featured", False)),
        "rating": float(getattr(product, "rating", 0) or 0),
        "review_count": int(getattr(product, "review_count", 0) or 0),
        "created_at": _serialize_dt(getattr(product, "created_at", None)),
        "updated_at": _serialize_dt(getattr(product, "updated_at", None)),
    }


def _serialize_order_for_seller(order: Any, seller_ids: set[int], db: Session) -> dict[str, Any] | None:
    serialized_items: list[dict[str, Any]] = []

    for item in getattr(order, "order_items", []) or []:
        product = getattr(item, "product", None)
        if not product:
            continue

        product_seller_id = getattr(product, "seller_id", None)
        if product_seller_id not in seller_ids:
            continue

        product_payload = _serialize_product_for_order(product, db)

        product_id = getattr(item, "product_id", None)
        if product_id is None:
            product_id = product_payload.get("id", 0)

        snapshot_image = getattr(item, "product_image", None)
        if isinstance(snapshot_image, str) and snapshot_image.strip():
            item_image = make_absolute_media_url(snapshot_image)
        else:
            item_image = product_payload.get("primary_image_url")

        serialized_items.append({
            "id": getattr(item, "id", 0),
            "product_id": int(product_id or 0),
            "product_name": getattr(item, "product_name", None) or product_payload.get("title", ""),
            "product_image": item_image,
            "quantity": int(getattr(item, "quantity", 0) or 0),
            "unit_price": float(getattr(item, "unit_price", 0) or 0),
            "total_price": float(getattr(item, "total_price", 0) or 0),
            "product": product_payload,
        })

    if not serialized_items:
        return None

    return {
        "id": getattr(order, "id", 0),
        "user_id": getattr(order, "user_id", 0),
        "status": getattr(order, "status", "pending") or "pending",
        "total_amount": float(getattr(order, "total_amount", 0) or 0),
        "shipping_address": _normalize_address(getattr(order, "shipping_address", None)),
        "billing_address": _normalize_address(getattr(order, "billing_address", None)),
        "payment_method": getattr(order, "payment_method", None),
        "payment_status": getattr(order, "payment_status", None),
        "created_at": _serialize_dt(getattr(order, "created_at", None)),
        "updated_at": _serialize_dt(getattr(order, "updated_at", None)),
        "order_items": serialized_items,
    }


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
    limit: int = Query(50, ge=1),
    search: str = Query(None, description="Search by product name or category"),
    status: str = Query(None, description="Filter by status: active, inactive, or out_of_stock"),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get current seller's products with optional search and filters"""
    from ..models import Product, Category
    
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    
    seller_id = cast(int, seller.id)
    
    # Build query
    seller_filter = _seller_product_filter(current_user.id, seller_id)
    query = db.query(Product).filter(seller_filter)
    
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
                if image_ids and all(isinstance(x, int) for x in image_ids):
                    product_images = db.query(ProductImage).filter(
                        ProductImage.id.in_(image_ids)
                    ).all()
                    product_dict["images"] = [make_absolute_media_url(img.image_url) for img in product_images] if product_images else []
                elif image_ids:
                    product_dict["images"] = [make_absolute_media_url(str(img)) for img in image_ids]
            except Exception:
                product_dict["images"] = []
        product_dict["primary_image_url"] = product_dict["images"][0] if product_dict["images"] else None
        
        result.append(product_dict)
    
    return result


@router.get("/orders")
@router.get("/orders/")
def get_seller_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get orders containing seller's products"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    seller_id = cast(int, seller.id)
    seller_filter = _seller_product_filter(current_user.id, seller_id)
    seller_ids = {seller_id, current_user.id}

    # Step 1: Get distinct order IDs (avoids joinedload + distinct conflict)
    order_ids_rows = db.query(crud.models.Order.id).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        seller_filter
    ).distinct().order_by(crud.models.Order.id.desc()).offset(skip).limit(limit).all()

    order_ids = [r[0] for r in order_ids_rows]
    if not order_ids:
        return []

    # Step 2: Load full order data with relationships
    orders = db.query(crud.models.Order).filter(
        crud.models.Order.id.in_(order_ids)
    ).options(
        joinedload(crud.models.Order.order_items).joinedload(crud.models.OrderItem.product),
        joinedload(crud.models.Order.user)
    ).order_by(crud.models.Order.created_at.desc()).all()

    serialized_orders: list[dict[str, Any]] = []
    for order in orders:
        payload = _serialize_order_for_seller(order, seller_ids, db)
        if payload is not None:
            serialized_orders.append(payload)

    return serialized_orders


@router.get("/orders/{order_id}")
def get_seller_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Get a specific order by ID if it contains current seller's products"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    seller_id = cast(int, seller.id)
    seller_filter = _seller_product_filter(current_user.id, seller_id)

    order = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        crud.models.Order.id == order_id,
        seller_filter
    ).options(
        joinedload(crud.models.Order.order_items).joinedload(crud.models.OrderItem.product),
        joinedload(crud.models.Order.user)
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this seller")

    payload = _serialize_order_for_seller(order, {seller_id, current_user.id}, db)
    if payload is None:
        raise HTTPException(status_code=404, detail="Order not found for this seller")
    return payload


@router.get("/dashboard")
@router.get("/dashboard/")
def get_seller_dashboard(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller),
    since: str | None = Query(None, description="ISO datetime to count new orders since")
):
    """Get seller dashboard statistics"""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    seller_filter = _seller_product_filter(current_user.id, seller.id)
    
    # Get statistics
    total_products = db.query(crud.models.Product).filter(
        seller_filter
    ).count()
    
    active_products = db.query(crud.models.Product).filter(
        seller_filter,
        crud.models.Product.is_active == True
    ).count()
    
    # Get orders containing seller's products
    total_orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        seller_filter
    ).distinct().count()

    # Pending orders count
    pending_orders = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).join(
        crud.models.Product
    ).filter(
        seller_filter,
        crud.models.Order.status == "pending"
    ).distinct().count()
    
    # Calculate total revenue
    from sqlalchemy import func
    total_revenue = db.query(
        func.sum(crud.models.OrderItem.total_price)
    ).join(
        crud.models.Product
    ).filter(
        seller_filter
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
                seller_filter,
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
    seller_filter = _seller_product_filter(current_user.id, seller.id)
    
    # Get top selling products
    top_products = db.query(
        crud.models.Product.title,
        func.sum(crud.models.OrderItem.quantity).label('total_sold'),
        func.sum(crud.models.OrderItem.total_price).label('total_revenue')
    ).join(
        crud.models.OrderItem
    ).filter(
        seller_filter
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
        seller_filter
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
    seller_filter = _seller_product_filter(current_user.id, seller.id)
    
    seller_id = getattr(seller, "id", 0)
    
    # Ensure payout info exists
    mobile_methods = ("bkash", "nagad", "rocket", "upay")
    payout_ok = seller.payout_method and (
        (seller.payout_method == "paypal" and seller.paypal_email) or
        (seller.payout_method == "bank_transfer" and seller.bank_account_number) or
        (seller.payout_method in mobile_methods and seller.bank_account_number)
    )
    if not payout_ok:
        raise HTTPException(status_code=400, detail="Please add payout/bank information before requesting a withdrawal")

    # Calculate available balance: 90% of total revenue after 10% commission
    total_revenue = db.query(
        func.sum(crud.models.OrderItem.total_price)
    ).join(
        crud.models.Product
    ).filter(
        seller_filter
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
    mobile_methods = ("bkash", "nagad", "rocket", "upay")
    all_methods = ("bank_transfer", "paypal", "stripe") + mobile_methods
    if method_type not in all_methods:
        raise HTTPException(status_code=400, detail="Invalid payment method type")
    
    # Set payout method
    setattr(seller, "payout_method", method_type)
    
    if method_type == "bank_transfer":
        # Validate required fields
        if not all([payout.get("bank_account"), payout.get("account_holder_name")]):
            raise HTTPException(status_code=400, detail="Bank transfer requires bank_account and account_holder_name")
        
        setattr(seller, "bank_account_number", payout.get("bank_account"))
        setattr(seller, "bank_routing_number", payout.get("bank_code", ""))
        setattr(seller, "bank_account_name", payout.get("account_holder_name"))
        setattr(seller, "bank_name", payout.get("bank_name", ""))

    elif method_type in mobile_methods:
        # Mobile banking methods: store number in bank_account_number field
        if not payout.get("mobile_number"):
            raise HTTPException(status_code=400, detail=f"{method_type} requires mobile_number")
        setattr(seller, "bank_account_number", payout.get("mobile_number"))
        setattr(seller, "bank_account_name", payout.get("account_holder_name", ""))
        
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
