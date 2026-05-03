"""
Product Images and Variants Router
Handles all endpoints for product images and variants
"""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime
import shutil

from app.database import get_db
from app.models import Product, ProductImage, ProductVariant, User
from app.schemas import (
    ProductImage as ProductImageSchema,
    ProductImageCreate,
    ProductVariant as ProductVariantSchema,
    ProductVariantCreate,
    ProductVariantUpdate,
)
from app.auth import get_current_user
from app.crud import get_user
from sqlalchemy import desc as sql_desc
from app.config import settings


# Helper to convert stored image paths to absolute URLs
def _abs_url(u: str) -> str:
    if not u:
        return u
    u = str(u)
    if u.startswith("http://") or u.startswith("https://"):
        return u
    base = settings.api_base_url.rstrip("/")
    if u.startswith("/"):
        return f"{base}{u}"
    return f"{base}/{u}"

router = APIRouter(prefix="/api/v1", tags=["products"])

# Upload directory
UPLOAD_DIR = "uploads/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== PRODUCT IMAGES ====================

@router.post("/products/{product_id}/images", response_model=ProductImageSchema)
def add_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image_url: str = Form(...),
    alt_text: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    sort_order: int = Form(0),
):
    """Add an image to a product"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify seller owns this product
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
    # If marking as primary, unset other primaries
    if is_primary:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True
        ).update({ProductImage.is_primary: False})
    
    # Create image record
    db_image = ProductImage(
        product_id=product_id,
        image_url=image_url,
        alt_text=alt_text,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    
    return db_image


@router.get("/products/{product_id}/images", response_model=List[ProductImageSchema])
def get_product_images(product_id: int, db: Session = Depends(get_db)):
    """Get all images for a product, sorted by order"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Order deterministically: primary images first, then by sort_order, then by creation time
    images = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).order_by(
        ProductImage.is_primary.desc(),
        ProductImage.sort_order.asc(),
        ProductImage.created_at.asc()
    ).all()
    
    out = [
        {
            "id": img.id,
            "image_url": _abs_url(str(img.image_url)),
            "alt_text": img.alt_text,
            "is_primary": img.is_primary,
            "sort_order": img.sort_order,
            "created_at": img.created_at,
        }
        for img in images
    ]

    return out


@router.put("/products/{product_id}/images/{image_id}", response_model=ProductImageSchema)
def update_product_image(
    product_id: int,
    image_id: int,
    alt_text: Optional[str] = None,
    is_primary: Optional[bool] = None,
    sort_order: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a product image"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get image
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # If marking as primary, unset others
    if is_primary:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True
        ).update({ProductImage.is_primary: False})
    
    # Update fields
    if alt_text is not None:
        image.alt_text = alt_text
    if is_primary is not None:
        image.is_primary = is_primary
    if sort_order is not None:
        image.sort_order = sort_order
    
    db.commit()
    db.refresh(image)
    return image


@router.delete("/products/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a product image"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get and delete image
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.delete(image)
    db.commit()
    
    return {"message": "Image deleted successfully"}


@router.put("/products/{product_id}/images/{image_id}/set-primary")
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set an image as the primary/featured image"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get image
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Unset other primaries
    db.query(ProductImage).filter(
        ProductImage.product_id == product_id,
        ProductImage.is_primary == True
    ).update({ProductImage.is_primary: False})
    
    # Set this as primary
    image.is_primary = True
    db.commit()
    
    return {"message": "Image set as primary", "image_id": image_id}


# ==================== PRODUCT VARIANTS ====================

@router.post("/products/{product_id}/variants", response_model=ProductVariantSchema)
def create_product_variant(
    product_id: int,
    variant_data: ProductVariantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new variant for a product"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create variant
    db_variant = ProductVariant(
        product_id=product_id,
        sku=variant_data.sku or f"{product.sku}-{datetime.now().timestamp()}",
        variant_name=variant_data.variant_name,
        color=variant_data.color,
        size=variant_data.size,
        material=variant_data.material,
        style=variant_data.style,
        storage=variant_data.storage,
        ram=variant_data.ram,
        other_attributes=variant_data.other_attributes,
        price_adjustment=variant_data.price_adjustment,
        inventory_count=variant_data.inventory_count,
    )
    
    db.add(db_variant)
    
    # Mark product as having variants
    product.has_variants = True
    
    db.commit()
    db.refresh(db_variant)
    
    return db_variant


@router.get("/products/{product_id}/variants", response_model=List[ProductVariantSchema])
def get_product_variants(
    product_id: int,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get all variants for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    query = db.query(ProductVariant).filter(ProductVariant.product_id == product_id)
    
    if active_only:
        query = query.filter(ProductVariant.is_active == True)
    
    variants = query.all()
    return variants


@router.get("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
def get_product_variant(
    product_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific variant"""
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    return variant


@router.put("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
def update_product_variant(
    product_id: int,
    variant_id: int,
    variant_update: ProductVariantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a product variant"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get variant
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    # Update fields
    update_data = variant_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variant, field, value)
    
    db.commit()
    db.refresh(variant)
    
    return variant


@router.delete("/products/{product_id}/variants/{variant_id}")
def delete_product_variant(
    product_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a product variant"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify authorization
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get and delete variant
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    db.delete(variant)
    db.commit()
    
    return {"message": "Variant deleted successfully"}


# ==================== ENHANCED PRODUCT ENDPOINTS ====================

@router.get("/products/{product_id}/full")
def get_product_with_images_and_variants(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Get product with all images and variants - full detail view"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get images
    # Order deterministically so the frontend receives a stable first image
    images = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).order_by(
        ProductImage.is_primary.desc(),
        ProductImage.sort_order.asc(),
        ProductImage.created_at.asc()
    ).all()
    
    # Get variants
    variants = db.query(ProductVariant).filter(
        ProductVariant.product_id == product_id,
        ProductVariant.is_active == True
    ).all()
    # Build a clean serializable product dict (avoid SQLAlchemy internal attrs)
    product_data = {col.name: getattr(product, col.name) for col in product.__table__.columns}

    # Serialize images and variants to simple dicts
    product_images = [
        {
            "id": img.id,
            "image_url": _abs_url(str(img.image_url)),
            "alt_text": img.alt_text,
            "is_primary": img.is_primary,
            "sort_order": img.sort_order,
            "created_at": img.created_at,
        }
        for img in images
    ]

    variant_list = [
        {col.name: getattr(v, col.name) for col in v.__table__.columns}
        for v in variants
    ]

    return {
        **product_data,
        "product_images": product_images,
        "variants": variant_list,
    }
