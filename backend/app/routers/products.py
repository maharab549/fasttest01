from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .. import crud, schemas, auth
from ..database import get_db
import math
import os
import shutil

router = APIRouter(prefix="/products", tags=["products"])


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
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total = crud.count_products(
            db=db,
            search=q,
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


@router.get("/featured")
def get_featured_products(limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    """Get featured products"""
    try:
        products = db.query(crud.models.Product).filter(
            crud.models.Product.is_featured == True,
            crud.models.Product.is_active == True
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
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        total = crud.count_products(
            db=db,
            search=q,
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
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    product = crud.get_product(db=db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/slug/{slug}", response_model=schemas.Product)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get product by slug"""
    product = crud.get_product_by_slug(db=db, slug=slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=schemas.Product)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Create a new product (seller only)"""
    # Get seller profile
    seller = crud.get_seller_by_user_id(db=db, user_id=current_user.id)
    if not seller:
        raise HTTPException(status_code=400, detail="Seller profile not found")
    
    # Check if product with same SKU exists
    existing_product = db.query(crud.models.Product).filter(crud.models.Product.sku == product.sku).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    return crud.create_product(db=db, product=product, seller_id=seller.id)


@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
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
    
    updated_product = crud.update_product(db=db, product_id=product_id, product_update=product_update)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return updated_product


@router.get("/{product_id}/reviews", response_model=List[schemas.Review])
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
    review.is_verified_purchase = True  # Mark as verified since it's from a delivered order
    
    return crud.create_review(db=db, review=review, user_id=current_user.id)



@router.post("/upload-image")
def upload_product_image(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(auth.get_current_seller)
):
    """Upload a product image (seller only)"""
    # Ensure the user is a seller
    seller = crud.get_seller_by_user_id(db=Depends(get_db), user_id=current_user.id)
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


