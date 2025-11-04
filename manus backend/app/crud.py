from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from typing import List, Optional
from . import models, schemas, auth
import uuid
from datetime import datetime


# User CRUD
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_seller=user.is_seller
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> models.User:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "is_seller" and value is True and not db_user.is_seller:
            # If user is becoming a seller, create a seller profile
            seller_data = schemas.SellerCreate(
                store_name=f"{db_user.full_name}\'s Store",
                store_slug=db_user.username.lower().replace(" ", "-"),
                store_description=f"Welcome to {db_user.full_name}\'s store!"
            )
            create_seller(db=db, seller=seller_data, user_id=db_user.id)
        setattr(db_user, field, value)

    
    db.commit()
    db.refresh(db_user)
    return db_user


# Seller CRUD
def get_seller_by_user_id(db: Session, user_id: int) -> Optional[models.Seller]:
    return db.query(models.Seller).filter(models.Seller.user_id == user_id).first()


def create_seller(db: Session, seller: schemas.SellerCreate, user_id: int) -> models.Seller:
    db_seller = models.Seller(
        user_id=user_id,
        store_name=seller.store_name,
        store_description=seller.store_description,
        store_slug=seller.store_slug
    )
    db.add(db_seller)
    db.commit()
    db.refresh(db_seller)
    return db_seller


# Category CRUD
def get_categories(db: Session, skip: int = 0, limit: int = 100) -> List[models.Category]:
    return db.query(models.Category).filter(models.Category.is_active == True).offset(skip).limit(limit).all()


def get_category(db: Session, category_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def create_category(db: Session, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


# Product CRUD
def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    semantic_search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> List[models.Product]:
    query = db.query(models.Product).filter(models.Product.is_active == True)
    
    # Apply filters
    if search:
        if semantic_search:
            query = query.filter(models.Product.title.ilike(f"%{semantic_search}%"))
        elif search:
            query = query.filter(models.Product.title.ilike(f"%{search}%"))
    
    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)
    
    # Apply sorting
    if sort_by == "price":
        order_column = models.Product.price
    elif sort_by == "rating":
        order_column = models.Product.rating
    elif sort_by == "title":
        order_column = models.Product.title
    else:
        order_column = models.Product.created_at
    
    if sort_order == "asc":
        query = query.order_by(asc(order_column))
    else:
        query = query.order_by(desc(order_column))
    
    return query.offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).options(joinedload(models.Product.seller)).filter(models.Product.id == product_id).first()


def get_product_by_slug(db: Session, slug: str) -> Optional[models.Product]:
    return db.query(models.Product).options(joinedload(models.Product.seller)).filter(models.Product.slug == slug).first()


def get_products_by_seller(db: Session, seller_id: int, skip: int = 0, limit: int = 100) -> List[models.Product]:
    return db.query(models.Product).filter(models.Product.seller_id == seller_id).offset(skip).limit(limit).all()


def create_product(db: Session, product: schemas.ProductCreate, seller_id: int) -> models.Product:
    db_product = models.Product(
        **product.dict(),
        seller_id=seller_id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate) -> Optional[models.Product]:
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        db.commit()
        db.refresh(db_product)
    return db_product


def increment_product_view_count(db: Session, product_id: int) -> Optional[models.Product]:
    """Increments the view_count for a product"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        # Assuming 'view_count' field exists on models.Product
        if hasattr(db_product, 'view_count'):
            # Defensive: view_count may be None in some records/schema migrations.
            # Treat None as 0 so += doesn't fail.
            if db_product.view_count is None:
                db_product.view_count = 1
            else:
                db_product.view_count += 1
            db.commit()
            db.refresh(db_product)
        else:
            # Log a warning if the field is missing, but continue
            # In a real app, this would be a proper log, but here a print will suffice
            print(f"Warning: 'view_count' attribute not found on product {product_id}. Skipping increment.")
    return db_product


# Cart CRUD
def get_cart_items(db: Session, user_id: int) -> List[models.CartItem]:
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()


def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int) -> models.CartItem:
    # Check if item already exists in cart
    existing_item = db.query(models.CartItem).filter(
        and_(models.CartItem.user_id == user_id, models.CartItem.product_id == product_id)
    ).first()
    
    if existing_item:
        existing_item.quantity += quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        cart_item = models.CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        return cart_item


def update_cart_item(db: Session, user_id: int, product_id: int, quantity: int) -> Optional[models.CartItem]:
    cart_item = db.query(models.CartItem).filter(
        and_(models.CartItem.user_id == user_id, models.CartItem.product_id == product_id)
    ).first()
    
    if cart_item:
        if quantity <= 0:
            db.delete(cart_item)
            db.commit()
            return None
        else:
            cart_item.quantity = quantity
            db.commit()
            db.refresh(cart_item)
            return cart_item
    return None


def remove_from_cart(db: Session, user_id: int, product_id: int) -> bool:
    cart_item = db.query(models.CartItem).filter(
        and_(models.CartItem.user_id == user_id, models.CartItem.product_id == product_id)
    ).first()
    
    if cart_item:
        db.delete(cart_item)
        db.commit()
        return True
    return False


def clear_cart(db: Session, user_id: int) -> bool:
    db.query(models.CartItem).filter(models.CartItem.user_id == user_id).delete()
    db.commit()
    return True


# Order CRUD
def create_order(db: Session, order: schemas.OrderCreate, user_id: int) -> models.Order:
    # Generate unique order number
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # Calculate totals
    total_amount = sum(item.quantity * item.unit_price for item in order.items)
    
    db_order = models.Order(
        user_id=user_id,
        order_number=order_number,
        total_amount=total_amount,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment_method=order.payment_method
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for item in order.items:
        order_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price
        )
        db.add(order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order


from sqlalchemy.orm import joinedload

def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Order]:
    return db.query(models.Order)\
             .filter(models.Order.user_id == user_id)\
             .options(joinedload(models.Order.order_items).joinedload(models.OrderItem.product))\
             .offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int) -> Optional[models.Order]:
    return db.query(models.Order)\
             .filter(models.Order.id == order_id)\
             .options(joinedload(models.Order.order_items).joinedload(models.OrderItem.product))\
             .first()


def update_order_status(db: Session, order_id: int, status: str) -> Optional[models.Order]:
    order = db.query(models.Order)\
             .filter(models.Order.id == order_id)\
             .options(joinedload(models.Order.order_items).joinedload(models.OrderItem.product))\
             .first()
    if order:
        order.status = status
        db.commit()
        db.refresh(order)
    return order


# Review CRUD
def create_review(db: Session, review: schemas.ReviewCreate, user_id: int) -> models.Review:
    db_review = models.Review(
        **review.dict(),
        user_id=user_id
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Update product rating
    update_product_rating(db, review.product_id)
    
    return db_review


def get_reviews_by_product(db: Session, product_id: int, skip: int = 0, limit: int = 100) -> List[models.Review]:
    return db.query(models.Review).filter(
        and_(models.Review.product_id == product_id, models.Review.is_approved == True)
    ).offset(skip).limit(limit).all()


def update_product_rating(db: Session, product_id: int):
    """Update product rating based on reviews"""
    reviews = db.query(models.Review).filter(
        and_(models.Review.product_id == product_id, models.Review.is_approved == True)
    ).all()
    
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
        product = db.query(models.Product).filter(models.Product.id == product_id).first()
        if product:
            product.rating = round(avg_rating, 1)
            product.review_count = len(reviews)
            db.commit()


def count_products(
    db: Session,
    search: Optional[str] = None,
    semantic_search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
) -> int:
    """Count products with filters"""
    query = db.query(models.Product).filter(models.Product.is_active == True)
    
    if search:
        if semantic_search:
            query = query.filter(models.Product.title.ilike(f"%{semantic_search}%"))
        elif search:
            query = query.filter(models.Product.title.ilike(f"%{search}%"))
    
    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)
    
    return query.count()

