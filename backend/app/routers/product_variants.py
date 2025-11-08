"""
Product Images and Variants Router
Handles all endpoints for product images and variants
"""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import uuid
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

def _authorized_for_product(db: Session, product_id: int, current_user: User) -> bool:
    """Check if the current user owns the product or is an admin, using scalar values."""
    owner_id = db.query(Product.seller_id).filter(Product.id == product_id).scalar()
    # current_user.id should already be a plain int from auth; fallback to None
    user_id_val = getattr(current_user, 'id', None)
    is_admin_val = db.query(User.is_admin).filter(User.id == user_id_val).scalar() or False
    return (owner_id is not None and user_id_val is not None and owner_id == user_id_val) or bool(is_admin_val)

router = APIRouter(prefix="/products", tags=["products"])

# Upload directory
UPLOAD_DIR = "uploads/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== PRODUCT IMAGES ====================

@router.post("/{product_id}/images", response_model=ProductImageSchema)
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
    
    # Verify seller owns this product (avoid SQLAlchemy boolean coercion)
    if not _authorized_for_product(db, product_id, current_user):
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


@router.get("/{product_id}/images", response_model=List[ProductImageSchema])
def get_product_images(product_id: int, db: Session = Depends(get_db)):
    """Get all images for a product, sorted by order"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    images = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).order_by(ProductImage.sort_order).all()
    
    return images


@router.put("/{product_id}/images/{image_id}", response_model=ProductImageSchema)
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
    if not _authorized_for_product(db, product_id, current_user):
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

    # Update fields using update() to avoid InstrumentedAttribute assignment issues
    update_values = {}
    if alt_text is not None:
        update_values[ProductImage.alt_text] = alt_text
    if is_primary is not None:
        update_values[ProductImage.is_primary] = bool(is_primary)
    if sort_order is not None:
        update_values[ProductImage.sort_order] = int(sort_order)
    if update_values:
        db.query(ProductImage).filter(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id
        ).update(update_values)
        db.commit()
    # Return fresh row
    updated = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    return updated


@router.delete("/{product_id}/images/{image_id}")
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
    if not _authorized_for_product(db, product_id, current_user):
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


@router.put("/{product_id}/images/{image_id}/set-primary")
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
    if not _authorized_for_product(db, product_id, current_user):
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
    db.query(ProductImage).filter(ProductImage.id == image_id).update({ProductImage.is_primary: True})
    db.commit()
    
    return {"message": "Image set as primary", "image_id": image_id}


# ==================== PRODUCT VARIANTS ====================

@router.post("/{product_id}/variants", response_model=ProductVariantSchema)
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
    if not _authorized_for_product(db, product_id, current_user):
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
    db.query(Product).filter(Product.id == product_id).update({Product.has_variants: True})
    
    db.commit()
    db.refresh(db_variant)
    
    return db_variant


@router.get("/{product_id}/variants", response_model=List[ProductVariantSchema])
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


@router.get("/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
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


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariantSchema)
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
    if not _authorized_for_product(db, product_id, current_user):
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


@router.delete("/{product_id}/variants/{variant_id}")
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
    if not _authorized_for_product(db, product_id, current_user):
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


# ==================== VARIANT IMAGE HANDLING ====================

@router.post("/{product_id}/variants/{variant_id}/upload-image")
def upload_variant_image(
    product_id: int,
    variant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an image for a product variant.
    Creates a ProductImage and associates it with the variant.
    Returns the image ID and URL.
    """
    try:
        # Verify authorization
        if not _authorized_for_product(db, product_id, current_user):
            raise HTTPException(status_code=403, detail="Not authorized to edit this product")
        
        # Verify product exists
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Verify variant exists and belongs to product
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id
        ).first()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")
        
        # Create variants upload directory
        variant_upload_dir = "uploads/variants"
        os.makedirs(variant_upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename or "")[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(variant_upload_dir, unique_filename)
        
        # Save file to disk
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
        
        # Create ProductImage record for the variant
        image_url = f"/uploads/variants/{unique_filename}"
        db_image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            alt_text=f"Variant {variant.variant_name or variant.id}",
            is_primary=False,
            sort_order=0,
        )
        db.add(db_image)
        db.flush()  # Flush to get the image ID
        
        # Add image ID to variant's images list
        import json
        existing_images_str = variant.images or "[]"
        try:
            existing_images = json.loads(existing_images_str) if isinstance(existing_images_str, str) else []
        except Exception:
            existing_images = []
        
        if not isinstance(existing_images, list):
            existing_images = []
        
        # Add the new image ID
        existing_images.append(db_image.id)
        
        # Update variant with new images list using setattr to avoid type checking issues
        setattr(variant, 'images', json.dumps(existing_images))
        db.commit()
        db.refresh(db_image)
        
        # Get created_at value safely
        created_at_value = getattr(db_image, 'created_at', None)
        created_at_str = created_at_value.isoformat() if created_at_value is not None else None
        
        return {
            "id": db_image.id,
            "product_id": db_image.product_id,
            "image_url": db_image.image_url,
            "alt_text": db_image.alt_text or "",
            "is_primary": db_image.is_primary,
            "sort_order": db_image.sort_order,
            "created_at": created_at_str,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading variant image: {str(e)}")


# ==================== ENHANCED PRODUCT ENDPOINTS ====================

@router.get("/{product_id}/full")
def get_product_with_images_and_variants(
    product_id: int,
    db: Session = Depends(get_db),
):
    """Get product with all images and variants - full detail view"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get images
    images = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).order_by(ProductImage.sort_order).all()
    
    # Get variants
    variants = db.query(ProductVariant).filter(
        ProductVariant.product_id == product_id,
        ProductVariant.is_active == True
    ).all()
    
    return {
        **product.__dict__,
        "product_images": images,
        "variants": variants,
    }
