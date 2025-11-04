from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth, models
from ..database import get_db

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/")
def add_to_favorites(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Add a product to user's favorites"""
    # Check if product exists
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already in favorites
    existing_favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.product_id == product_id
    ).first()
    
    if existing_favorite:
        raise HTTPException(status_code=400, detail="Product already in favorites")
    
    # Add to favorites
    favorite = models.Favorite(
        user_id=current_user.id,
        product_id=product_id
    )
    
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return {"message": "Product added to favorites", "favorite_id": favorite.id}


@router.delete("/{product_id}")
def remove_from_favorites(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Remove a product from user's favorites"""
    favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.product_id == product_id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Product not in favorites")
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Product removed from favorites"}


@router.get("/")
def get_user_favorites(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get user's favorite products"""
    favorites = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    # Get the products
    favorite_products = []
    for favorite in favorites:
        product = db.query(models.Product).filter(models.Product.id == favorite.product_id).first()
        if product:
            favorite_products.append({
                "favorite_id": favorite.id,
                "product": product,
                "added_at": favorite.created_at
            })
    
    return {
        "data": favorite_products,
        "total": len(favorite_products)
    }


@router.get("/check/{product_id}")
def check_if_favorite(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Check if a product is in user's favorites"""
    favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.product_id == product_id
    ).first()
    
    return {"is_favorite": favorite is not None}

