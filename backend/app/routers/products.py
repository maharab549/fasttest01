from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .. import crud, schemas, auth
from ..database import get_db
from ..config import settings

# Whether to run AI-powered semantic search. Read from settings if available,
# otherwise default to False to avoid NameError when the setting is not present.
ai_search = getattr(settings, 'ai_search', False)
from ..ai_recommendations import get_product_recommendations
from ..utils import get_semantic_search_query # Import new utility
import uuid
import math
import os
import shutil

router = APIRouter(prefix="/products", tags=["products"])


# Image search endpoint removed - image search feature has been deprecated and the related
# utility moved/removed. If you need to re-enable image-based search, reintroduce a
# purpose-built, tested module. For now, keep product endpoints focused on text-based
# search and recommendations.


@router.get("/")
def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db)
):
    """Get products with filtering, sorting, and pagination"""
    try:
        skip = (page - 1) * per_page
        products = crud.get_products(
            db=db,
            skip=skip,
            limit=per_page,
            search=q,
            semantic_search=get_semantic_search_query(q) if ai_search and q else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total = crud.count_products(
            db=db,
            search=q,
            semantic_search=get_semantic_search_query(q) if ai_search and q else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price
        )
        
        pages = math.ceil(total / per_page) if total > 0 else 0
        
        # Convert products to dict format
        products_data = []
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
                "images": product.images,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "rating": product.rating,
                "review_count": product.review_count,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            products_data.append(product_dict)
        
        return {
            "items": products_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")


@router.get("/featured/")
@router.get("/featured")
def get_featured_products(limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    """Get featured products"""
    try:
        products = db.query(crud.models.Product).filter(
            crud.models.Product.is_featured == True,
            crud.models.Product.is_active == True,
            crud.models.Product.approval_status == "approved"
        ).limit(limit).all()
        
        # Convert products to dict format
        products_data = []
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
                "images": product.images,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "rating": product.rating,
                "review_count": product.review_count,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            products_data.append(product_dict)
        
        return products_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching featured products: {str(e)}")


@router.get("/search")
def search_products(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("created_at", regex="^(created_at|price|rating|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Search products"""
    try:
        products = crud.get_products(
            db=db,
            skip=skip,
            limit=limit,
            search=q,
            semantic_search=get_semantic_search_query(q) if ai_search and q else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total = crud.count_products(
            db=db,
            search=q,
            semantic_search=get_semantic_search_query(q) if ai_search and q else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price
        )
        
        pages = math.ceil(total / limit) if total > 0 else 0
        page = (skip // limit) + 1
        
        # Convert products to dict format
        products_data = []
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
                "images": product.images,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "rating": product.rating,
                "review_count": product.review_count,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            products_data.append(product_dict)
        
        return {
            "items": products_data,
            "total": total,
            "page": page,
            "per_page": limit,
            "pages": pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching products: {str(e)}")


@router.get("/{product_id}", response_model=schemas.Product)
@router.get("/{product_id}/", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    product = crud.get_product(db=db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/slug/{slug}", response_model=schemas.Product)
@router.get("/slug/{slug}/", response_model=schemas.Product)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get product by slug"""
    product = crud.get_product_by_slug(db=db, slug=slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/{slug}/view")
def track_product_view(slug: str, db: Session = Depends(get_db)):
    """Increment the view count for a product by slug"""
    product = crud.get_product_by_slug(db=db, slug=slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Increment view count in the database
    # Assuming crud.increment_product_view_count exists and handles the update
    # and that the Product model has a 'view_count' field.
    crud.increment_product_view_count(db=db, product_id=product.id)
    
    return {"message": f"View tracked for product: {slug}"}


@router.post("/", response_model=schemas.Product)
async def create_product(
    request: Request,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Create a new product (seller only)"""
    # Get seller profile
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")
    
    # Parse payload (support JSON or multipart/form-data)
    product_dict: Dict[str, Any]
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        def _to_float(val):
            try:
                return float(val) if val not in (None, "", []) else None
            except Exception:
                return None
        def _to_int(val):
            try:
                return int(val) if val not in (None, "", []) else None
            except Exception:
                return None
        product_dict = {
            "title": form.get("title"),
            "description": form.get("description"),
            "short_description": form.get("short_description"),
            "price": _to_float(form.get("price")),
            "compare_price": _to_float(form.get("compare_price")),
            "sku": form.get("sku"),
            "inventory_count": _to_int(form.get("inventory_count")) or 0,
            "weight": _to_float(form.get("weight")),
            # dimensions could be JSON string
            "dimensions": None,
            "images": None,
            "category_id": _to_int(form.get("category_id")),
            "slug": form.get("slug") or None,
        }
        dims = form.get("dimensions")
        if dims:
            try:
                import json
                product_dict["dimensions"] = json.loads(str(dims))
            except Exception:
                product_dict["dimensions"] = None
        imgs = form.get("images")
        if imgs:
            try:
                import json
                product_dict["images"] = json.loads(str(imgs))
            except Exception:
                # allow comma-separated urls
                product_dict["images"] = [s.strip() for s in str(imgs).split(",") if s.strip()]
    else:
        try:
            product_dict = await request.json()
        except Exception:
            product_dict = {}

    # Normalize alternate frontend keys
    # Support 'name' -> 'title', 'stock' -> 'inventory_count', 'image' -> 'images'
    if product_dict.get('title') is None and product_dict.get('name'):
        product_dict['title'] = product_dict.get('name')
    if product_dict.get('inventory_count') is None and product_dict.get('stock') is not None:
        try:
            product_dict['inventory_count'] = int(product_dict.get('stock'))
        except Exception:
            product_dict['inventory_count'] = 0
    if product_dict.get('images') is None and product_dict.get('image'):
        img = product_dict.get('image')
        product_dict['images'] = [img] if isinstance(img, str) else img
    # Coerce numeric strings from JSON
    for key in ('price','compare_price','weight'):
        if key in product_dict and isinstance(product_dict[key], str):
            try:
                product_dict[key] = float(product_dict[key]) if product_dict[key] != '' else None
            except Exception:
                product_dict[key] = None
    for key in ('inventory_count','category_id'):
        if key in product_dict and isinstance(product_dict[key], str):
            try:
                product_dict[key] = int(product_dict[key]) if product_dict[key] != '' else None
            except Exception:
                product_dict[key] = None

    # Validate against input schema
    from pydantic import ValidationError, parse_obj_as
    try:
        input_obj = parse_obj_as(schemas.ProductCreateInput, product_dict)
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())

    # Check if product with same SKU exists
    # Auto-generate SKU if missing
    if not input_obj.sku:
        input_obj.sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
    existing_product = db.query(crud.models.Product).filter(crud.models.Product.sku == input_obj.sku).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    # Normalize payload and provide defaults
    product_dict = input_obj.dict()
    if product_dict.get('images') is None:
        product_dict['images'] = []

    # Ensure slug exists; if not, generate a slug from the title + short uuid suffix
    if not product_dict.get('slug'):
        base_slug = (product_dict.get('title') or 'product').lower().strip().replace(' ', '-')
        product_dict['slug'] = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # Validate against strict ProductCreate schema for DB write
    product_create_obj = parse_obj_as(schemas.ProductCreate, product_dict)

    return crud.create_product(db=db, product=product_create_obj, seller_id=int(seller.id))


@router.put("/{product_id}", response_model=schemas.Product)
@router.put("/{product_id}/", response_model=schemas.Product)
async def update_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Update a product (seller only)"""
    # Get seller profile
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")
    
    # Check if product exists and belongs to seller
    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")
    
    # Parse body as JSON or multipart-form; then validate into ProductUpdate
    content_type = request.headers.get("content-type", "")
    payload: Dict[str, Any]
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        def _to_float(val):
            try:
                return float(val) if val not in (None, "", []) else None
            except Exception:
                return None
        def _to_int(val):
            try:
                return int(val) if val not in (None, "", []) else None
            except Exception:
                return None
        payload = {
            "title": form.get("title"),
            "description": form.get("description"),
            "short_description": form.get("short_description"),
            "price": _to_float(form.get("price")),
            "compare_price": _to_float(form.get("compare_price")),
            "inventory_count": _to_int(form.get("inventory_count")),
            "weight": _to_float(form.get("weight")),
            "dimensions": None,
            "images": None,
            "category_id": _to_int(form.get("category_id")),
            "is_active": None if form.get("is_active") in (None, "") else str(form.get("is_active")).lower() in ("1","true","yes","on"),
        }
        dims = form.get("dimensions")
        if dims:
            try:
                import json
                payload["dimensions"] = json.loads(str(dims))
            except Exception:
                payload["dimensions"] = None
        imgs = form.get("images")
        if imgs:
            try:
                import json
                payload["images"] = json.loads(str(imgs))
            except Exception:
                payload["images"] = [s.strip() for s in str(imgs).split(",") if s.strip()]
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    from pydantic import ValidationError, parse_obj_as
    try:
        product_update = parse_obj_as(schemas.ProductUpdate, payload)
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())

    updated_product = crud.update_product(db=db, product_id=product_id, product_update=product_update)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return updated_product


@router.delete("/{product_id}")
@router.delete("/{product_id}/")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Delete a product (seller only)"""
    # Get seller profile
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")

    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")

    try:
        db.delete(product)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {e}")

    return {"message": "Product deleted", "success": True}


@router.get("/{product_id}/reviews", response_model=List[schemas.Review])
@router.get("/{product_id}/reviews/", response_model=List[schemas.Review])
def get_product_reviews(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get reviews for a product"""
    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    reviews = crud.get_reviews_by_product(db=db, product_id=product_id, skip=skip, limit=limit)
    return reviews


@router.post("/{product_id}/reviews", response_model=schemas.Review)
@router.post("/{product_id}/reviews/", response_model=schemas.Review)
def create_product_review(
    product_id: int,
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create a review for a product (only allowed after order delivery)"""
    product = crud.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user has a delivered order containing this product
    delivered_order = db.query(crud.models.Order).join(
        crud.models.OrderItem
    ).filter(
        crud.models.Order.user_id == current_user.id,
        crud.models.Order.status == "delivered",
        crud.models.OrderItem.product_id == product_id
    ).first()
    
    if not delivered_order:
        raise HTTPException(
            status_code=403, 
            detail="You can only review products from delivered orders. Please wait for your order to be delivered."
        )
    
    # Check if user already reviewed this product
    existing_review = db.query(crud.models.Review).filter(
        crud.models.Review.user_id == current_user.id,
        crud.models.Review.product_id == product_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    
    # Override product_id from URL and set order_id for verification
    review.product_id = product_id
    review.order_id = delivered_order.id
    review.is_verified_purchase = True  # Mark as verified since it\'s from a delivered order
    
    return crud.create_review(db=db, review=review, user_id=current_user.id)



@router.get("/{product_id}/recommendations", response_model=List[schemas.Product])
def get_product_recommendations_endpoint(
    product_id: int,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Get AI-powered product recommendations for a given product."""
    recommendations = get_product_recommendations(db, product_id, limit)
    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendations found for this product.")
    return recommendations


@router.post("/upload-image")
def upload_product_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Upload a product image (seller only)"""
    # Ensure the user is a seller
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=403, detail="Only sellers can upload images")


    # Define upload directory
    upload_dir = "uploads/products"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate a unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Return the URL to the uploaded image
    return {"filename": unique_filename, "url": f"/uploads/products/{unique_filename}"}

