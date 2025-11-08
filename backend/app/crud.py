from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from typing import List, Optional
from . import models, schemas, auth
import uuid
from datetime import datetime


# ProductImage CRUD
def create_product_image(db: Session, product_id: int, image_url: str, alt_text: str = None, is_primary: bool = False, sort_order: int = 0) -> models.ProductImage:
    db_image = models.ProductImage(
        product_id=product_id,
        image_url=image_url,
        alt_text=alt_text,
        is_primary=is_primary,
        sort_order=sort_order
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


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
    
    # Only show approved products to customers (not admin/seller views)
    query = query.filter(models.Product.approval_status == "approved")
    
    # Eager load seller to prevent N+1 queries
    query = query.options(joinedload(models.Product.seller))
    
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
    return db.query(models.Product).options(
        joinedload(models.Product.seller)
        # TODO: Re-enable when product_variants table schema is fully migrated
        # joinedload(models.Product.variants)
    ).filter(models.Product.slug == slug).first()


def get_products_by_seller(db: Session, seller_id: int, skip: int = 0, limit: int = 100) -> List[models.Product]:
    return db.query(models.Product).filter(models.Product.seller_id == seller_id).offset(skip).limit(limit).all()


def get_featured_products(db: Session, limit: int = 8) -> List[models.Product]:
    """Get featured products that are active and approved"""
    return db.query(models.Product).filter(
        models.Product.is_featured == True,
        models.Product.is_active == True,
        models.Product.approval_status == "approved"
    ).limit(limit).all()


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


def get_pending_products(db: Session, skip: int = 0, limit: int = 100) -> List[models.Product]:
    """Get all pending products waiting for admin approval"""
    return db.query(models.Product).filter(
        models.Product.approval_status == "pending"
    ).order_by(models.Product.created_at.desc()).offset(skip).limit(limit).all()


def approve_product(db: Session, product_id: int, admin_user_id: int) -> Optional[models.Product]:
    """Approve a product by admin"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        db_product.approval_status = "approved"
        db_product.approved_at = datetime.utcnow()
        db_product.approved_by = admin_user_id
        db.commit()
        db.refresh(db_product)
    return db_product


def reject_product(db: Session, product_id: int, reason: str) -> Optional[models.Product]:
    """Reject a product by admin with a reason"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        db_product.approval_status = "rejected"
        db_product.rejection_reason = reason
        db.commit()
        db.refresh(db_product)
    return db_product


# Cart CRUD
def get_cart_items(db: Session, user_id: int) -> List[models.CartItem]:
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()


def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int, variant_id: Optional[int] = None) -> models.CartItem:
    # Check if item already exists in cart (same product and variant)
    existing_item = db.query(models.CartItem).filter(
        and_(
            models.CartItem.user_id == user_id,
            models.CartItem.product_id == product_id,
            models.CartItem.variant_id == variant_id
        )
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
            quantity=quantity,
            variant_id=variant_id
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
        status="pending",
        total_amount=total_amount,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment_method=order.payment_method
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items with product snapshots
    for item in order.items:
        # Get product to capture name and image
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        
        # Get first image from images array if available
        product_image = None
        if product and product.images:
            try:
                import json
                images = json.loads(product.images) if isinstance(product.images, str) else product.images
                if isinstance(images, list) and len(images) > 0:
                    product_image = images[0]
            except:
                pass
        
        order_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
            product_name=product.title if product else None,
            product_image=product_image
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
             .order_by(desc(models.Order.created_at))\
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


# Return CRUD
def create_return(db: Session, return_data: schemas.ReturnCreate, user_id: int) -> models.Return:
    """Create a new return request"""
    # Generate unique return number
    return_number = f"RET-{uuid.uuid4().hex[:8].upper()}"
    
    # Get the order to calculate refund amount
    order = db.query(models.Order).filter(models.Order.id == return_data.order_id).first()
    if not order:
        raise ValueError("Order not found")
    
    # Calculate refund amount based on return items
    refund_amount = 0.0
    for item in return_data.items:
        order_item = db.query(models.OrderItem).filter(models.OrderItem.id == item.order_item_id).first()
        if order_item:
            refund_amount += order_item.unit_price * item.quantity
    
    # Create return request
    db_return = models.Return(
        return_number=return_number,
        order_id=return_data.order_id,
        user_id=user_id,
        reason=return_data.reason,
        reason_details=return_data.reason_details,
        refund_amount=refund_amount,
        refund_method=return_data.refund_method,
        status="initiated"
    )
    db.add(db_return)
    db.commit()
    db.refresh(db_return)
    
    # Create return items
    for item in return_data.items:
        return_item = models.ReturnItem(
            return_id=db_return.id,
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            quantity=item.quantity,
            reason=item.reason,
            condition=item.condition,
            images=item.images
        )
        db.add(return_item)
    
    db.commit()
    db.refresh(db_return)
    return db_return


def get_returns_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Return]:
    """Get all returns for a user"""
    return db.query(models.Return)\
             .filter(models.Return.user_id == user_id)\
             .options(joinedload(models.Return.return_items))\
             .order_by(desc(models.Return.created_at))\
             .offset(skip).limit(limit).all()


def get_return(db: Session, return_id: int) -> Optional[models.Return]:
    """Get a single return by ID"""
    return db.query(models.Return)\
             .filter(models.Return.id == return_id)\
             .options(joinedload(models.Return.return_items))\
             .first()


def get_return_by_number(db: Session, return_number: str) -> Optional[models.Return]:
    """Get a single return by return number"""
    return db.query(models.Return)\
             .filter(models.Return.return_number == return_number)\
             .options(joinedload(models.Return.return_items))\
             .first()


def update_return_status(db: Session, return_id: int, status: str, admin_notes: Optional[str] = None) -> Optional[models.Return]:
    """Update return status"""
    db_return = db.query(models.Return).filter(models.Return.id == return_id).first()
    if db_return:
        db_return.status = status
        if admin_notes:
            db_return.admin_notes = admin_notes
        
        # If status is refunded, update refund date and status
        if status == "refunded" or status == "completed":
            db_return.refund_status = "completed"
            if not db_return.refund_date:
                db_return.refund_date = datetime.now()
        
        db.commit()
        db.refresh(db_return)
    return db_return


def update_return(db: Session, return_id: int, return_update: schemas.ReturnUpdate) -> Optional[models.Return]:
    """Update return details"""
    db_return = db.query(models.Return).filter(models.Return.id == return_id).first()
    if db_return:
        update_data = return_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_return, field, value)
        
        db.commit()
        db.refresh(db_return)
    return db_return


def get_all_returns(db: Session, skip: int = 0, limit: int = 100) -> List[models.Return]:
    """Get all returns (for admin)"""
    return db.query(models.Return)\
             .options(joinedload(models.Return.return_items))\
             .order_by(desc(models.Return.created_at))\
             .offset(skip).limit(limit).all()




# Loyalty & Rewards CRUD
def create_reward_tier(db: Session, tier: schemas.RewardTierCreate) -> models.RewardTier:
    """Create a new reward tier"""
    db_tier = models.RewardTier(**tier.dict())
    db.add(db_tier)
    db.commit()
    db.refresh(db_tier)
    return db_tier


def get_reward_tiers(db: Session) -> List[models.RewardTier]:
    """Get all reward tiers ordered by min_points"""
    return db.query(models.RewardTier).order_by(models.RewardTier.min_points).all()


def get_reward_tier(db: Session, tier_id: int) -> Optional[models.RewardTier]:
    """Get a specific reward tier"""
    return db.query(models.RewardTier).filter(models.RewardTier.id == tier_id).first()


def get_tier_for_points(db: Session, points: int) -> Optional[models.RewardTier]:
    """Get the appropriate tier for a points balance"""
    return db.query(models.RewardTier)\
        .filter(models.RewardTier.min_points <= points)\
        .filter(or_(models.RewardTier.max_points >= points, models.RewardTier.max_points == None))\
        .order_by(desc(models.RewardTier.min_points))\
        .first()


def create_loyalty_account(db: Session, user_id: int) -> models.LoyaltyAccount:
    """Create a loyalty account for a new user"""
    # Generate unique referral code
    referral_code = f"{uuid.uuid4().hex[:8].upper()}"
    
    db_account = models.LoyaltyAccount(
        user_id=user_id,
        referral_code=referral_code,
        points_balance=0,
        lifetime_points=0,
        tier_id=None
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    # Award signup bonus
    award_points(
        db=db,
        loyalty_account_id=db_account.id,
        points=100,
        source="signup_bonus",
        description="Welcome bonus for joining!"
    )
    
    return db_account


def get_loyalty_account_by_user(db: Session, user_id: int) -> Optional[models.LoyaltyAccount]:
    """Get loyalty account for a user"""
    return db.query(models.LoyaltyAccount)\
        .options(joinedload(models.LoyaltyAccount.tier))\
        .filter(models.LoyaltyAccount.user_id == user_id)\
        .first()


def get_loyalty_account_by_referral_code(db: Session, referral_code: str) -> Optional[models.LoyaltyAccount]:
    """Get loyalty account by referral code"""
    return db.query(models.LoyaltyAccount)\
        .filter(models.LoyaltyAccount.referral_code == referral_code)\
        .first()


def award_points(
    db: Session,
    loyalty_account_id: int,
    points: int,
    source: str,
    source_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
) -> models.PointsTransaction:
    """Award points to a loyalty account"""
    account = db.query(models.LoyaltyAccount).filter(models.LoyaltyAccount.id == loyalty_account_id).first()
    if not account:
        raise ValueError("Loyalty account not found")
    
    # Apply tier multiplier if account has a tier
    if account.tier and account.tier.points_multiplier:
        points = int(points * account.tier.points_multiplier)
    
    # Update account balance
    account.points_balance += points
    account.lifetime_points += points
    
    # Check if tier upgrade is needed
    new_tier = get_tier_for_points(db, account.lifetime_points)
    if new_tier and (not account.tier_id or new_tier.id != account.tier_id):
        account.tier_id = new_tier.id
    
    # Create transaction record
    transaction = models.PointsTransaction(
        loyalty_account_id=loyalty_account_id,
        transaction_type="earn",
        points_change=points,
        points_balance_after=account.points_balance,
        source=source,
        source_id=source_id,
        description=description or f"Earned {points} points from {source}",
        extra_data=metadata
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.refresh(account)
    
    return transaction


def deduct_points(
    db: Session,
    loyalty_account_id: int,
    points: int,
    source: str,
    source_id: Optional[str] = None,
    description: Optional[str] = None
) -> models.PointsTransaction:
    """Deduct points from a loyalty account"""
    account = db.query(models.LoyaltyAccount).filter(models.LoyaltyAccount.id == loyalty_account_id).first()
    if not account:
        raise ValueError("Loyalty account not found")
    
    if account.points_balance < points:
        raise ValueError("Insufficient points balance")
    
    # Update account balance
    account.points_balance -= points
    
    # Create transaction record
    transaction = models.PointsTransaction(
        loyalty_account_id=loyalty_account_id,
        transaction_type="redeem",
        points_change=-points,
        points_balance_after=account.points_balance,
        source=source,
        source_id=source_id,
        description=description or f"Redeemed {points} points for {source}"
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.refresh(account)
    
    return transaction


def get_points_transactions(
    db: Session,
    loyalty_account_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[models.PointsTransaction]:
    """Get transaction history for a loyalty account"""
    return db.query(models.PointsTransaction)\
        .filter(models.PointsTransaction.loyalty_account_id == loyalty_account_id)\
        .order_by(desc(models.PointsTransaction.created_at))\
        .offset(skip).limit(limit).all()


def create_redemption(
    db: Session,
    loyalty_account_id: int,
    redemption_data: schemas.RedemptionCreate
) -> models.Redemption:
    """Create a redemption and deduct points"""
    from datetime import timedelta
    
    # Deduct points
    deduct_points(
        db=db,
        loyalty_account_id=loyalty_account_id,
        points=redemption_data.points_redeemed,
        source=redemption_data.redemption_type,
        description=f"Redeemed {redemption_data.points_redeemed} points for {redemption_data.redemption_type}"
    )
    
    # Generate reward code
    reward_code = f"{redemption_data.redemption_type[:4].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create redemption record
    redemption = models.Redemption(
        loyalty_account_id=loyalty_account_id,
        redemption_type=redemption_data.redemption_type,
        points_redeemed=redemption_data.points_redeemed,
        reward_value=redemption_data.reward_value,
        reward_code=reward_code,
        status="active",
        expires_at=datetime.now() + timedelta(days=90)  # 90 days expiry
    )
    
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    
    return redemption


def get_redemptions(
    db: Session,
    loyalty_account_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    include_old_used_expired: bool = False
) -> List[models.Redemption]:
    """
    Get redemptions for a loyalty account
    
    By default, hides 'used' and 'expired' rewards that are older than 3 days.
    Set include_old_used_expired=True to show all rewards regardless of age.
    """
    from datetime import datetime, timedelta
    
    query = db.query(models.Redemption)\
        .filter(models.Redemption.loyalty_account_id == loyalty_account_id)
    
    if status:
        query = query.filter(models.Redemption.status == status)
    
    # Get all results first, then filter by date
    all_redemptions = query.order_by(desc(models.Redemption.created_at)).all()
    
    # Filter out used/expired rewards older than 3 days
    if not include_old_used_expired:
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        filtered = []
        
        for redemption in all_redemptions:
            status_val = getattr(redemption, "status", None)
            
            # Keep 'active' rewards always
            if status_val == "active":
                filtered.append(redemption)
                continue
            
            # For 'used' and 'expired', check the timestamp
            if status_val in ["used", "expired"]:
                # Check which timestamp to use
                timestamp = getattr(redemption, "used_at", None)
                if not timestamp:
                    timestamp = getattr(redemption, "expires_at", None)
                if not timestamp:
                    timestamp = getattr(redemption, "created_at", None)
                
                # Only keep if newer than 3 days
                if timestamp and timestamp > three_days_ago:
                    filtered.append(redemption)
            else:
                # Keep any other status
                filtered.append(redemption)
        
        all_redemptions = filtered
    
    # Apply pagination
    return all_redemptions[skip:skip + limit]


def use_redemption(db: Session, redemption_id: int, order_id: Optional[int] = None) -> models.Redemption:
    """Mark a redemption as used"""
    redemption = db.query(models.Redemption).filter(models.Redemption.id == redemption_id).first()
    if not redemption:
        raise ValueError("Redemption not found")
    
    if redemption.status != "active":
        raise ValueError("Redemption is not active")
    
    if redemption.expires_at and redemption.expires_at < datetime.now():
        raise ValueError("Redemption has expired")
    
    redemption.status = "used"
    redemption.used_at = datetime.now()
    if order_id:
        redemption.order_id = order_id
    
    db.commit()
    db.refresh(redemption)
    
    return redemption


def process_referral(db: Session, referral_code: str, new_user_id: int) -> bool:
    """Process a referral when a new user signs up"""
    # Get referrer's loyalty account
    referrer_account = get_loyalty_account_by_referral_code(db, referral_code)
    if not referrer_account:
        return False
    
    # Award points to referrer
    award_points(
        db=db,
        loyalty_account_id=referrer_account.id,
        points=500,  # Referrer gets 500 points
        source="referral",
        source_id=str(new_user_id),
        description=f"Referred a new user"
    )
    
    # Increment referral count
    referrer_account.referrals_count += 1
    db.commit()
    
    # Award bonus points to new user
    new_user_account = get_loyalty_account_by_user(db, new_user_id)
    if new_user_account:
        award_points(
            db=db,
            loyalty_account_id=new_user_account.id,
            points=200,  # New user gets 200 points
            source="referral",
            source_id=str(referrer_account.user_id),
            description=f"Signup bonus from referral"
        )
    
    return True


# Withdrawal CRUD
def create_withdrawal_request(db: Session, seller_id: int, amount: float) -> models.WithdrawalRequest:
    # snapshot seller payout info for audit
    seller = db.query(models.Seller).filter(models.Seller.id == seller_id).first()
    payout_snapshot = None
    if seller:
        payout_snapshot = {
            "payout_method": getattr(seller, "payout_method", None),
            "bank_name": getattr(seller, "bank_name", None),
            "bank_account_name": getattr(seller, "bank_account_name", None),
            "bank_account_number": getattr(seller, "bank_account_number", None),
            "bank_routing_number": getattr(seller, "bank_routing_number", None),
            "paypal_email": getattr(seller, "paypal_email", None)
        }

    withdrawal = models.WithdrawalRequest(
        seller_id=seller_id,
        amount=amount,
        status="pending",
        payout_snapshot=payout_snapshot
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal


def approve_withdrawal(db: Session, withdrawal_id: int, admin_user_id: int) -> Optional[models.WithdrawalRequest]:
    db_withdrawal = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == withdrawal_id).first()
    if not db_withdrawal:
        return None
    if db_withdrawal.status != "pending":
        return None
    db_withdrawal.status = "approved"
    db.commit()
    db.refresh(db_withdrawal)
    return db_withdrawal


def process_withdrawal_payout(db: Session, withdrawal_id: int, admin_user_id: int) -> Optional[models.WithdrawalRequest]:
    """Simulate processing a payout: mark withdrawal as 'paid', set paid_at and payout_reference."""
    db_withdrawal = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == withdrawal_id).first()
    if not db_withdrawal:
        return None
    if db_withdrawal.status not in ("approved", "pending"):
        # already processed or rejected
        return None

    # Simulate external transfer success
    import uuid
    payout_ref = f"PAYOUT-{uuid.uuid4().hex[:12].upper()}"

    # mark as paid and record reference
    db_withdrawal.status = "paid"
    db_withdrawal.payout_reference = payout_ref
    from datetime import datetime
    db_withdrawal.paid_at = datetime.now()

    # Optionally, record in seller ledger or external system here
    db.commit()
    db.refresh(db_withdrawal)
    return db_withdrawal


def get_withdrawal(db: Session, withdrawal_id: int) -> Optional[models.WithdrawalRequest]:
    return db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == withdrawal_id).first()


def cancel_withdrawal(db: Session, withdrawal_id: int) -> Optional[models.WithdrawalRequest]:
    """Cancel a pending withdrawal and refund the seller's balance."""
    db_withdrawal = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == withdrawal_id).first()
    if not db_withdrawal:
        return None
    if db_withdrawal.status != "pending":
        # Only pending withdrawals can be cancelled
        return None
    # Refund seller
    seller = db.query(models.Seller).filter(models.Seller.id == db_withdrawal.seller_id).first()
    if seller:
        seller.balance = (seller.balance or 0.0) + (db_withdrawal.amount or 0.0)
    db_withdrawal.status = "cancelled"
    db.commit()
    db.refresh(db_withdrawal)
    if seller:
        db.refresh(seller)
    return db_withdrawal

def get_withdrawal_requests_by_seller(db: Session, seller_id: int) -> list[models.WithdrawalRequest]:
    return db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.seller_id == seller_id).order_by(models.WithdrawalRequest.created_at.desc()).all()


# Product Approval CRUD
def approve_product(db: Session, product_id: int, admin_user_id: int) -> Optional[models.Product]:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product:
        setattr(product, "approval_status", "approved")
        setattr(product, "approved_by", admin_user_id)
        from sqlalchemy.sql import func
        setattr(product, "approved_at", func.now())
        db.commit()
        db.refresh(product)
    return product

def reject_product(db: Session, product_id: int, reason: str) -> Optional[models.Product]:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product:
        setattr(product, "approval_status", "rejected")
        setattr(product, "rejection_reason", reason)
        db.commit()
        db.refresh(product)
    return product

def get_pending_products(db: Session, skip: int = 0, limit: int = 100) -> List[models.Product]:
    return db.query(models.Product).filter(models.Product.approval_status == "pending").offset(skip).limit(limit).all()

def update_product_images(db: Session, product_id: int, images: list[int]):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise ValueError("Product not found")

    # Assuming `images` is a list of image IDs
    product.images = images  # Store only the IDs
    db.commit()
    db.refresh(product)
    return product
