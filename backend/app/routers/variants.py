"""
Product Variants Router - API endpoints for managing product variants
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, auth
from app.database import get_db
import json

router = APIRouter(prefix="/products", tags=["product-variants"])


@router.post("/{product_id}/variants", response_model=schemas.ProductVariant, status_code=status.HTTP_201_CREATED)
def create_product_variant(
    product_id: int,
    variant: schemas.ProductVariantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new product variant"""
    # Get product and verify ownership
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user is seller of this product
    seller = db.query(models.Seller).filter(models.Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(status_code=403, detail="Seller account not found")
    
    # Check ownership using direct comparison
    if product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to add variants to this product")
    
    # Generate SKU if not provided
    sku = variant.sku
    if not sku:
        # Auto-generate SKU: PRODUCT_SKU-COLOR-SIZE
        product_sku = product.sku if product.sku else f"PROD{product_id}"
        parts = [str(product_sku)]
        if variant.color:
            parts.append(str(variant.color[:3]).upper())
        if variant.size:
            parts.append(str(variant.size).upper())
        sku = "-".join(parts)
    
    # Generate variant name if not provided
    variant_name = variant.variant_name
    if not variant_name:
        parts = []
        if variant.color:
            parts.append(str(variant.color))
        if variant.size:
            parts.append(str(variant.size))
        if variant.material:
            parts.append(str(variant.material))
        variant_name = " - ".join(parts) if parts else "Default"
    
    # Convert images list to JSON string
    images_json = json.dumps(variant.images) if variant.images else None
    
    # Create variant
    db_variant = models.ProductVariant(
        product_id=product_id,
        sku=sku,
        variant_name=variant_name,
        color=variant.color,
        size=variant.size,
        material=variant.material,
        style=variant.style,
        other_attributes=variant.other_attributes,
        price_adjustment=variant.price_adjustment,
        inventory_count=variant.inventory_count,
        images=images_json
    )
    
    db.add(db_variant)
    
    # Mark product as having variants using update query
    current_has_variants = product.has_variants
    if not current_has_variants:
        db.execute(
            models.Product.__table__.update().
            where(models.Product.id == product_id).
            values(has_variants=True)
        )
    
    db.commit()
    db.refresh(db_variant)
    
    # Build response dict to avoid SQLAlchemy attribute access issues
    response_data = {
        "id": db_variant.id,
        "product_id": db_variant.product_id,
        "sku": db_variant.sku,
        "variant_name": db_variant.variant_name,
        "color": db_variant.color,
        "size": db_variant.size,
        "material": db_variant.material,
        "style": db_variant.style,
        "other_attributes": db_variant.other_attributes,
        "price_adjustment": db_variant.price_adjustment,
        "inventory_count": db_variant.inventory_count,
        "is_active": db_variant.is_active,
        "created_at": db_variant.created_at,
        "images": []
    }
    
    # Parse images back to list for response
    if db_variant.images:
        try:
            response_data["images"] = json.loads(str(db_variant.images))
        except:
            response_data["images"] = []
    
    return response_data


@router.get("/{product_id}/variants", response_model=List[schemas.ProductVariant])
def get_product_variants(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get all variants for a product"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get all active variants
    variants = db.query(models.ProductVariant).filter(
        models.ProductVariant.product_id == product_id,
        models.ProductVariant.is_active == True
    ).all()
    
    # Convert each variant to dict and parse images
    result = []
    for variant in variants:
        variant_dict = {
            "id": variant.id,
            "product_id": variant.product_id,
            "sku": variant.sku,
            "variant_name": variant.variant_name,
            "color": variant.color,
            "size": variant.size,
            "material": variant.material,
            "style": variant.style,
            "other_attributes": variant.other_attributes,
            "price_adjustment": variant.price_adjustment,
            "inventory_count": variant.inventory_count,
            "is_active": variant.is_active,
            "created_at": variant.created_at,
            "images": []
        }
        
        if variant.images:
            try:
                variant_dict["images"] = json.loads(str(variant.images))
            except:
                variant_dict["images"] = []
        
        result.append(variant_dict)
    
    return result


@router.get("/{product_id}/variants/{variant_id}", response_model=schemas.ProductVariant)
def get_product_variant(
    product_id: int,
    variant_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific product variant"""
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id,
        models.ProductVariant.product_id == product_id,
        models.ProductVariant.is_active == True
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    # Build response dict
    variant_dict = {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "variant_name": variant.variant_name,
        "color": variant.color,
        "size": variant.size,
        "material": variant.material,
        "style": variant.style,
        "other_attributes": variant.other_attributes,
        "price_adjustment": variant.price_adjustment,
        "inventory_count": variant.inventory_count,
        "is_active": variant.is_active,
        "created_at": variant.created_at,
        "images": []
    }
    
    if variant.images:
        try:
            variant_dict["images"] = json.loads(str(variant.images))
        except:
            variant_dict["images"] = []
    
    return variant_dict


@router.put("/{product_id}/variants/{variant_id}", response_model=schemas.ProductVariant)
def update_product_variant(
    product_id: int,
    variant_id: int,
    variant_update: schemas.ProductVariantUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Update a product variant"""
    # Get product and verify ownership
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    seller = db.query(models.Seller).filter(models.Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(status_code=403, detail="Seller account not found")
    
    if product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this product variant")
    
    # Get the variant
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id,
        models.ProductVariant.product_id == product_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    # Update fields using setattr to avoid type checker issues
    update_data = variant_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "images" and value is not None:
            # Convert images list to JSON string
            setattr(variant, field, json.dumps(value))
        elif field != "images":
            setattr(variant, field, value)
    
    db.commit()
    db.refresh(variant)
    
    # Build response dict
    variant_dict = {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "variant_name": variant.variant_name,
        "color": variant.color,
        "size": variant.size,
        "material": variant.material,
        "style": variant.style,
        "other_attributes": variant.other_attributes,
        "price_adjustment": variant.price_adjustment,
        "inventory_count": variant.inventory_count,
        "is_active": variant.is_active,
        "created_at": variant.created_at,
        "images": []
    }
    
    if variant.images:
        try:
            variant_dict["images"] = json.loads(str(variant.images))
        except:
            variant_dict["images"] = []
    
    return variant_dict


@router.delete("/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_variant(
    product_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Soft delete a product variant"""
    # Get product and verify ownership
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    seller = db.query(models.Seller).filter(models.Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(status_code=403, detail="Seller account not found")
    
    if product.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product variant")
    
    # Get the variant
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id,
        models.ProductVariant.product_id == product_id
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    # Soft delete using update query
    db.execute(
        models.ProductVariant.__table__.update().
        where(models.ProductVariant.id == variant_id).
        values(is_active=False)
    )
    
    # Check if product still has active variants
    active_variants_count = db.query(models.ProductVariant).filter(
        models.ProductVariant.product_id == product_id,
        models.ProductVariant.is_active == True
    ).count()
    
    if active_variants_count == 0:
        # No more active variants, mark product as not having variants
        db.execute(
            models.Product.__table__.update().
            where(models.Product.id == product_id).
            values(has_variants=False)
        )
    
    db.commit()
    
    return None
