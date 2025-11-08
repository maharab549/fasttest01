from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.sql import expression
from typing import List, Optional, Dict, Any, cast
from .. import crud, schemas, auth
from ..database import get_db
from ..config import settings
from app import models

# Whether to run AI-powered semantic search. Read from settings if available,
# otherwise default to False to avoid NameError when the setting is not present.
ai_search = getattr(settings, 'ai_search', False)
from ..ai_recommendations import get_product_recommendations
from ..utils import get_semantic_search_query # Import new utility
import uuid
import math
import os
import shutil
import json

router = APIRouter(prefix="/products", tags=["products"])


# Image search endpoint removed - image search feature has been deprecated and the related
# utility moved/removed. If you need to re-enable image-based search, reintroduce a
# purpose-built, tested module. For now, keep product endpoints focused on text-based
# search and recommendations.


def _format_variant_for_response(variant, db):
    """Convert a ProductVariant ORM object into a dict with image URLs resolved.
    - The model stores `images` as JSON string of ProductImage IDs or URLs (in Text column).
    - This resolves IDs to URLs and orders: primary first, non-placeholder next, placeholders last.
    """
    # Base fields
    variant_dict = {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": getattr(variant, "sku", None),
        "variant_name": getattr(variant, "variant_name", None),
        "color": getattr(variant, "color", None),
        "size": getattr(variant, "size", None),
        "material": getattr(variant, "material", None),
        "style": getattr(variant, "style", None),
        "storage": getattr(variant, "storage", None),
        "ram": getattr(variant, "ram", None),
        "other_attributes": getattr(variant, "other_attributes", None),
        "price_adjustment": getattr(variant, "price_adjustment", 0.0),
        "inventory_count": getattr(variant, "inventory_count", 0),
        "is_active": getattr(variant, "is_active", True),
        "created_at": getattr(variant, "created_at", None),
        "updated_at": getattr(variant, "updated_at", None),
        "images": []
    }

    # Helper to normalize relative URLs into served /uploads paths
    def _norm(u: str) -> str:
        try:
            s = str(u)
        except Exception:
            return str(u)
        if s.startswith('http'):
            return s
        if s.startswith('/uploads/'):
            return s
        if s.startswith('uploads/'):
            return '/' + s
        if s.startswith('/products/'):
            return '/uploads' + s
        if s.startswith('products/'):
            return '/uploads/' + s
        return s

    # Resolve images from JSON/Text
    try:
        raw = getattr(variant, "images", None)
        imgs = None
        if isinstance(raw, list):
            imgs = raw
        elif isinstance(raw, str) and raw.strip():
            try:
                imgs = json.loads(raw)
            except Exception:
                imgs = None
        if isinstance(imgs, list) and imgs:
            if all(isinstance(x, int) for x in imgs):
                image_objs = db.query(models.ProductImage).filter(models.ProductImage.id.in_(imgs)).all()
                def image_sort_key(img):
                    placeholder_penalty = 1 if "placeholder-" in str(img.image_url) else 0
                    primary_rank = 0 if getattr(img, "is_primary", False) else 1
                    return (primary_rank, placeholder_penalty, getattr(img, "sort_order", 0))
                image_objs_sorted = sorted(image_objs, key=image_sort_key)
                variant_dict["images"] = [_norm(str(img.image_url)) for img in image_objs_sorted]
            else:
                urls = [_norm(str(x)) for x in imgs]
                if len(urls) > 1:
                    non_placeholder = [u for u in urls if "placeholder-" not in u]
                    if non_placeholder:
                        first_real = non_placeholder[0]
                        urls = [first_real] + [u for u in urls if u != first_real]
                variant_dict["images"] = urls
    except Exception as e:
        if settings.debug:
            print(f"[IMG_DEBUG] Variant {getattr(variant,'id','?')} image resolution error: {e}")

    return variant_dict


def format_product_for_response(product, db):
    """Convert a Product ORM object to a response dict with image URLs instead of IDs.
    
    This helper ensures all product endpoints return consistent, valid data:
    - Converts numeric image IDs to actual image URLs from the ProductImage table
    - Follows the schemas.Product response model format
    """
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
        # Variants formatted below for proper image resolution
        "variants": [],
        "seller": product.seller,
    }
    
    # Helper to normalize relative URLs into served /uploads paths
    def _norm(u: str) -> str:
        try:
            s = str(u)
        except Exception:
            return str(u)
        if s.startswith('http'):
            return s
        if s.startswith('/uploads/'):
            return s
        if s.startswith('uploads/'):
            return '/' + s
        if s.startswith('/products/'):
            return '/uploads' + s
        if s.startswith('products/'):
            return '/uploads/' + s
        return s

    # Resolve images: support both legacy URL lists and normalized ID lists
    try:
        if isinstance(product.images, list):
            if all(isinstance(x, int) for x in product.images):
                id_list = list(product.images)
                if id_list:
                    image_objs = db.query(models.ProductImage).filter(
                        models.ProductImage.id.in_(id_list)
                    ).all()
                    def image_sort_key(img):
                        placeholder_penalty = 1 if "placeholder-" in str(img.image_url) else 0
                        primary_rank = 0 if getattr(img, "is_primary", False) else 1
                        return (primary_rank, placeholder_penalty, getattr(img, "sort_order", 0))
                    image_objs_sorted = sorted(image_objs, key=image_sort_key)
                    ordered_urls = [_norm(str(img.image_url)) for img in image_objs_sorted]
                    product_dict["images"] = ordered_urls
                    if settings.debug:
                        print(f"[IMG_DEBUG] Product {product.slug} IDs->{id_list} resolved->{ordered_urls[:3]}")
            else:
                raw_urls = [_norm(str(x)) for x in list(product.images)]
                if len(raw_urls) > 1:
                    non_placeholder = [u for u in raw_urls if "placeholder-" not in u]
                    if non_placeholder:
                        first_real = non_placeholder[0]
                        raw_urls = [first_real] + [u for u in raw_urls if u != first_real]
                product_dict["images"] = raw_urls
                if settings.debug:
                    print(f"[IMG_DEBUG] Product {product.slug} raw URLs->{raw_urls[:3]}")
        # Fallback: if product.images is empty or None but ProductImage rows exist, pull them.
        if (not isinstance(product.images, list) or len(product.images) == 0):
            image_objs = db.query(models.ProductImage).filter(models.ProductImage.product_id == product.id).all()
            if image_objs:
                def image_sort_key(img):
                    placeholder_penalty = 1 if "placeholder-" in str(img.image_url) else 0
                    primary_rank = 0 if getattr(img, "is_primary", False) else 1
                    return (primary_rank, placeholder_penalty, getattr(img, "sort_order", 0))
                image_objs_sorted = sorted(image_objs, key=image_sort_key)
                fallback_urls = [_norm(str(img.image_url)) for img in image_objs_sorted]
                product_dict["images"] = fallback_urls
                if settings.debug:
                    print(f"[IMG_DEBUG] Product {product.slug} fallback ProductImage rows -> {fallback_urls[:3]}")
    except Exception as e:
        product_dict["images"] = []
        if settings.debug:
            print(f"[IMG_DEBUG] Product {getattr(product,'slug','?')} image resolution error: {e}")
    
    # Attach formatted variants (if any), resolving variant images to URLs
    try:
        if getattr(product, "variants", None):
            product_dict["variants"] = [_format_variant_for_response(v, db) for v in product.variants]
    except Exception as e:
        if settings.debug:
            print(f"[IMG_DEBUG] Product {getattr(product,'slug','?')} variant formatting error: {e}")

    return product_dict


@router.get("/")
def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    with_meta: bool = Query(False),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """Get products with filtering, sorting, and pagination"""
    try:
        skip = (page - 1) * per_page
        # Support both `q` and `search` query params for compatibility with different clients/tests
        search_query = q or search
        products = crud.get_products(
            db=db,
            skip=skip,
            limit=per_page,
            search=search_query,
            semantic_search=get_semantic_search_query(search_query) if ai_search and search_query else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total = crud.count_products(
            db=db,
            search=search_query,
            semantic_search=get_semantic_search_query(search_query) if ai_search and search_query else None,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price
        )
        
        pages = math.ceil(total / per_page) if total > 0 else 0
        
        # Convert products to dict format using the helper
        products_data = [format_product_for_response(product, db) for product in products]
        
        # Add caching headers for better performance
        if response:
            response.headers["Cache-Control"] = "public, max-age=300"
        
        if with_meta:
            return {
                "items": products_data,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages
            }

        # Historically some clients expect a plain list; return list for compatibility
        return products_data
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
        
        # Convert products to dict format using the helper
        return [format_product_for_response(product, db) for product in products]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching featured products: {str(e)}")



@router.get("/search")
@router.get("/search/")
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
            # Use unified formatter for consistency (includes image ordering logic)
            formatted = format_product_for_response(product, db)
            image_urls: list[str] = formatted.get("images", [])

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
                "images": image_urls,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "rating": product.rating,
                "review_count": product.review_count,
                "created_at": product.created_at.isoformat() if product.created_at is not None else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at is not None else None
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


@router.get("/slug/{slug}", response_model=schemas.Product)
@router.get("/slug/{slug}/", response_model=schemas.Product)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get product by slug using unified formatter for consistent image ordering."""
    product = crud.get_product_by_slug(db=db, slug=slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return format_product_for_response(product, db)


@router.get("/{product_id}", response_model=schemas.Product)
@router.get("/{product_id}/", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID using unified formatter for consistent image ordering."""
    product = crud.get_product(db=db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return format_product_for_response(product, db)


# -----------------------------
# Image management endpoints
# -----------------------------
class ReorderImagesRequest(BaseModel):
    image_ids: list[int]


@router.post("/{product_id}/images/{image_id}/primary")
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Mark one image as primary for a product (seller-owned)."""
    # Validate seller owns product
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")

    product = crud.get_product(db=db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    # Compare by value explicitly to avoid SQLAlchemy boolean coercion
    if int(getattr(product, "seller_id")) != int(getattr(seller, "id")):
        raise HTTPException(status_code=403, detail="Not authorized to modify this product")

    # Validate image belongs to product
    img = db.query(models.ProductImage).filter(
        models.ProductImage.id == image_id,
        models.ProductImage.product_id == product_id
    ).first()
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found for this product")

    # Set all non-primary, then desired primary
    db.query(models.ProductImage).filter(
        models.ProductImage.product_id == product_id
    ).update({models.ProductImage.is_primary: False})
    db.query(models.ProductImage).filter(models.ProductImage.id == image_id).update({
        models.ProductImage.is_primary: True
    })
    db.commit()
    return {"message": "Primary image updated."}


@router.post("/{product_id}/images/reorder")
def reorder_images(
    product_id: int,
    payload: ReorderImagesRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Reorder images for a product by specifying the exact sequence of image IDs.
    Only reorders the provided IDs (others keep their current sort_order)."""
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")

    product = crud.get_product(db=db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if int(getattr(product, "seller_id")) != int(getattr(seller, "id")):
        raise HTTPException(status_code=403, detail="Not authorized to modify this product")

    # Ensure all IDs belong to product
    imgs = db.query(models.ProductImage).filter(
        models.ProductImage.product_id == product_id,
        models.ProductImage.id.in_(payload.image_ids)
    ).all()
    found_ids = {img.id for img in imgs}
    missing = [i for i in payload.image_ids if i not in found_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Image IDs not found for this product: {missing}")

    for order, iid in enumerate(payload.image_ids):
        db.query(models.ProductImage).filter(
            models.ProductImage.id == iid
        ).update({models.ProductImage.sort_order: order})
    db.commit()
    return {"message": "Images reordered.", "order": payload.image_ids}


@router.post("/{slug}/view")
def track_product_view(slug: str, db: Session = Depends(get_db)):
    """Increment the view count for a product by slug"""
    product = crud.get_product_by_slug(db=db, slug=slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_id = db.query(models.Product.id).filter(models.Product.slug == slug).scalar()
    crud.increment_product_view_count(db=db, product_id=product_id)

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
    
    seller_id = db.query(models.Seller.id).filter(models.Seller.user_id == current_user.id).scalar()

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
        product_dict['inventory_count'] = int(product_dict.get('stock', 0))
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

    return crud.create_product(db=db, product=product_create_obj, seller_id=seller_id)


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
    
    seller_id = db.query(models.Product.seller_id).filter(models.Product.id == product_id).scalar()
    if seller_id != seller.id:
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
    
    # Query the seller_id to avoid ColumnElement[bool] comparison issue
    seller_id = db.query(models.Product.seller_id).filter(models.Product.id == product_id).scalar()
    if seller_id != seller.id:
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
    review.order_id = delivered_order.id if isinstance(delivered_order.id, int) else None

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
    # Convert ORM objects to dicts with image URLs
    return [format_product_for_response(product, db) for product in recommendations]



from fastapi import Query

@router.post("/upload-image")
def upload_product_image(
    file: UploadFile = File(...),
    product_id: int = Query(..., description="ID of the product this image belongs to"),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Upload a product image (seller only) and save to DB"""
    try:
        # Ensure the user is a seller
        seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
        if not seller:
            raise HTTPException(status_code=403, detail="Only sellers can upload images")

        # Verify product exists
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Define upload directory
        upload_dir = "uploads/products"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate a unique filename
        file_extension = os.path.splitext(file.filename or "")[1]  # Ensure filename is not None
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save the file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

        # Save ProductImage in DB
        image_url = f"/uploads/products/{unique_filename}"
        db_image = crud.create_product_image(db=db, product_id=product_id, image_url=image_url)
        
        if not db_image:
            raise HTTPException(status_code=500, detail="Failed to create product image record")

        # Append the new image ID to the product's images list
        # Defensive: product.images may contain non-numeric values (data URIs or temporary client-side blobs).
        # Only keep numeric IDs and ignore any non-numeric entries so int() conversion doesn't fail.
        existing_images = product.images if isinstance(product.images, list) else []
        cleaned_images: list[int] = []
        for image in existing_images:
            try:
                cleaned_images.append(int(image))
            except Exception:
                # ignore values that cannot be converted to int (e.g., data URIs)
                continue

        # Cast to satisfy static type checkers; runtime values are ints.
        updated_images = cast(list[int], cleaned_images + [db_image.id])
        crud.update_product_images(db=db, product_id=product_id, images=updated_images)

        # Verify the image was saved to DB
        db_image_data = db.query(models.ProductImage).filter(models.ProductImage.id == db_image.id).first()
        if not db_image_data:
            raise HTTPException(status_code=500, detail="Image was not saved to database")

        # Fetch actual values for timestamps (defensive: model may not have these columns)
        created_at = getattr(db_image_data, "created_at", None)
        updated_at = getattr(db_image_data, "updated_at", None)

        return {
            "id": db_image_data.id,
            "product_id": db_image_data.product_id,
            "image_url": db_image_data.image_url,
            "alt_text": db_image_data.alt_text or "",
            "is_primary": db_image_data.is_primary,
            "sort_order": db_image_data.sort_order,
            "created_at": created_at.isoformat() if created_at is not None else None,
            "updated_at": updated_at.isoformat() if updated_at is not None else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

