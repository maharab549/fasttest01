from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[schemas.Category])
def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get all categories"""
    categories = crud.get_categories(db=db, skip=skip, limit=limit)
    return categories


@router.get("/{category_id}", response_model=schemas.Category)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID"""
    category = crud.get_category(db=db, category_id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=schemas.Category)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_admin)
):
    """Create a new category (admin only)"""
    # Check if category with same slug exists
    existing_category = db.query(crud.models.Category).filter(
        crud.models.Category.slug == category.slug
    ).first()
    
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
    
    return crud.create_category(db=db, category=category)


@router.get("/{category_id}/products", response_model=List[schemas.Product])
def get_category_products(
    category_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get products in a category"""
    category = crud.get_category(db=db, category_id=category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    products = crud.get_products(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id
    )
    
    return products

