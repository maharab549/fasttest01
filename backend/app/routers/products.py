from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .. import crud, schemas, auth
from ..database import get_db
from ..config import settings

# Whether to run AI-powered semantic search. Read from settings if available,
# otherwise default to False to avoid NameError when the setting is not present.
ai_search = getattr(settings, 'ai_search', False)
from ..ai_recommendations import get_product_recommendations
from ..utils import image_to_text_description, get_semantic_search_query # Import new utility
import uuid
import math
import os
import shutil

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/image-search")
async def image_search(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Performs image-to-product search using color and visual analysis (NO LLM).
    1. Extracts dominant colors from uploaded image
    2. Searches products by matching colors in titles/descriptions
    3. Returns visually similar products based on color palette
    """
    temp_file_path = None
    try:
        from PIL import Image
        import colorsys
        from collections import Counter
        
        # Save uploaded file temporarily
        temp_dir = "uploads/temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"search_{file.filename}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract dominant colors using PIL
        img = Image.open(temp_file_path)
        img = img.convert('RGB')
        img.thumbnail((150, 150))  # Reduce size for faster processing
        
        pixels = list(img.getdata())
        
        # Get most common colors
        color_counter = Counter(pixels)
        dominant_colors = color_counter.most_common(5)
        
        # Convert RGB to color names and keywords
        def rgb_to_color_name(rgb):
            """Convert RGB to approximate color name"""
            r, g, b = [x/255.0 for x in rgb]
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            # Determine color based on HSV
            if v < 0.2:
                return ["black", "dark"]
            elif s < 0.1:
                if v > 0.8:
                    return ["white", "light"]
                else:
                    return ["gray", "grey"]
            else:
                # Determine hue-based color
                hue_degree = h * 360
                if hue_degree < 15 or hue_degree >= 345:
                    return ["red", "crimson"]
                elif 15 <= hue_degree < 45:
                    return ["orange", "coral"]
                elif 45 <= hue_degree < 75:
                    return ["yellow", "gold", "golden"]
                elif 75 <= hue_degree < 155:
                    return ["green", "emerald"]
                elif 155 <= hue_degree < 200:
                    return ["cyan", "turquoise", "aqua"]
                elif 200 <= hue_degree < 260:
                    return ["blue", "navy"]
                elif 260 <= hue_degree < 300:
                    return ["purple", "violet"]
                else:
                    return ["pink", "magenta", "rose"]
        
        # Extract color keywords
        color_keywords = set()
        for color_rgb, count in dominant_colors[:3]:  # Top 3 colors
            color_names = rgb_to_color_name(color_rgb)
            color_keywords.update(color_names)
        
        # Build search query from colors
        search_terms = list(color_keywords)
        search_query = " ".join(search_terms)
        
        # Search products matching these color terms
        all_products = crud.get_products(
            db=db,
            skip=0,
            limit=200,  # Get more to filter
            search=None,
            semantic_search=None,
            sort_by="created_at",
            sort_order="desc"
        )
        
        # Score products based on color keyword matches
        scored_products = []
        for product in all_products:
            score = 0
            text_to_search = f"{product.title} {product.description} {product.short_description}".lower()
            
            for keyword in color_keywords:
                if keyword in text_to_search:
                    score += 10
            
            if score > 0:
                scored_products.append((product, score))
        
        # Sort by score and limit results
        scored_products.sort(key=lambda x: x[1], reverse=True)
        products = [p[0] for p in scored_products[:limit]]
        
        # If no color matches, return recent products
        if not products:
            products = all_products[:limit]
        
        # Convert to dict format
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
            "query": search_query,
            "detected_colors": list(color_keywords),
            "message": f"Found {len(products_data)} products matching detected colors: {', '.join(color_keywords)}"
        }

    except Exception as e:
        print(f"Error in image_search: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error performing image search: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass


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
    # Ensure images default to empty list if not provided
    if getattr(product, 'images', None) is None:
        # pydantic BaseModel is immutable by default when coming from request; create a dict copy
        product_dict = product.dict()
        product_dict['images'] = []
    else:
        product_dict = product.dict()

    # Ensure slug exists; if not, generate a slug from the title + short uuid suffix
    if not product_dict.get('slug'):
        base_slug = (product_dict.get('title') or 'product').lower().strip().replace(' ', '-')
        product_dict['slug'] = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # Use crud.create_product with normalized dict -> construct a ProductCreate-like object
    # crud.create_product expects a schemas.ProductCreate-like object, but it uses product.dict() internally
    from pydantic import parse_obj_as
    product_create_obj = parse_obj_as(schemas.ProductCreate, product_dict)

    return crud.create_product(db=db, product=product_create_obj, seller_id=seller.id)


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

