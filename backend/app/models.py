from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON
from .database import Base
from .config import settings


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_seller = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    seller_profile = relationship("Seller", back_populates="user", uselist=False)
    # Returns and notifications (reverse relations)
    returns = relationship("Return", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Seller(Base):
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    store_name = Column(String, nullable=False)
    store_description = Column(Text)
    store_slug = Column(String, unique=True, index=True)
    is_verified = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_sales = Column(Integer, default=0)
    balance = Column(Float, default=0.0)  # Seller's available funds
    # Payout / bank details (optional)
    payout_method = Column(String, nullable=True)  # bank_transfer, paypal, stripe, manual
    bank_name = Column(String, nullable=True)
    bank_account_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    bank_routing_number = Column(String, nullable=True)
    paypal_email = Column(String, nullable=True)
    stripe_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="seller_profile")
    products = relationship("Product", back_populates="seller")


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    parent = relationship("Category", remote_side=[id])
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True)
    description = Column(Text)
    short_description = Column(String)
    price = Column(Float, nullable=False)
    compare_price = Column(Float, nullable=True)
    sku = Column(String, unique=True, index=True)
    inventory_count = Column(Integer, default=0)
    weight = Column(Float, nullable=True)
    dimensions = Column(JSONB if settings.use_supabase else JSON, nullable=True)  # {"length": 10, "width": 5, "height": 2}
    images = Column(JSONB if settings.use_supabase else JSON, nullable=True)  # ["image1.jpg", "image2.jpg"]
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    has_variants = Column(Boolean, default=False)  # NEW: Product has color/size variants
    approval_status = Column(String, default="pending")  # pending, approved, rejected
    rejection_reason = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    seller = relationship("Seller", back_populates="products")
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    product_images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    image_url = Column(String, nullable=False)
    alt_text = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)  # Set one as primary/featured image
    sort_order = Column(Integer, default=0)  # For drag-and-drop ordering
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="product_images")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String, unique=True, index=True)
    variant_name = Column(String)  # e.g., "Red - Medium - 256GB"
    color = Column(String, nullable=True)
    size = Column(String, nullable=True)
    material = Column(String, nullable=True)
    style = Column(String, nullable=True)
    # New variant attributes for electronics and other products
    storage = Column(String, nullable=True)  # e.g., "256GB", "512GB"
    ram = Column(String, nullable=True)  # e.g., "8GB", "16GB"
    other_attributes = Column(Text, nullable=True)  # JSON string for custom attributes
    price_adjustment = Column(Float, default=0.0)  # + or - from base price
    inventory_count = Column(Integer, default=0)
    images = Column(Text, nullable=True)  # JSON array of ProductImage IDs for this variant
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="variants")


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_number = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # pending, confirmed, processing, shipped, delivered, cancelled
    total_amount = Column(Float, nullable=False)
    shipping_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_code = Column(String, nullable=True)  # Applied discount/coupon code
    applied_redemption_id = Column(Integer, ForeignKey("redemptions.id"), nullable=True)  # Link to reward redemption
    
    # Shipping Information
    shipping_address = Column(JSONB if settings.use_supabase else JSON, nullable=False)
    billing_address = Column(JSONB if settings.use_supabase else JSON, nullable=True)
    
    # Payment Information
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid, failed, refunded
    payment_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    applied_redemption = relationship("Redemption", foreign_keys=[applied_redemption_id])
    # Reverse relation for returns
    returns = relationship("Return", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)  # NEW
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Product snapshot fields (for when product is deleted/modified)
    product_name = Column(String, nullable=True)
    product_image = Column(String, nullable=True)
    variant_details = Column(Text, nullable=True)  # NEW: JSON string of variant (color, size, etc.)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    variant = relationship("ProductVariant", foreign_keys=[variant_id])  # NEW


class Return(Base):
    __tablename__ = "returns"
    
    id = Column(Integer, primary_key=True, index=True)
    return_number = Column(String, unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="initiated")  # initiated, approved, rejected, shipped, received, refunded, completed
    reason = Column(String, nullable=False)  # defective, wrong_item, not_as_described, changed_mind, other
    reason_details = Column(Text, nullable=True)
    
    # Refund Information
    refund_amount = Column(Float, nullable=False)
    refund_method = Column(String, default="original")  # original, store_credit
    refund_status = Column(String, default="pending")  # pending, processing, completed, failed
    refund_date = Column(DateTime(timezone=True), nullable=True)
    
    # Shipping Information
    shipping_label_url = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    shipped_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    
    # Admin notes
    admin_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="returns")
    user = relationship("User", back_populates="returns")
    # use `return_obj` on ReturnItem side to avoid using the Python keyword `return`
    return_items = relationship("ReturnItem", back_populates="return_obj")


class ReturnItem(Base):
    __tablename__ = "return_items"
    
    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    return_obj = relationship("Return", back_populates="return_items")
    order_item = relationship("OrderItem")


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
    variant = relationship("ProductVariant")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', 'variant_id', name='_user_product_variant_uc'),
    )


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # e.g., 'order_status', 'new_message', 'promotion'
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    related_id = Column(Integer, nullable=True)  # e.g., order_id, message_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notifications")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    related_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Attachments
    attachment_type = Column(String, nullable=True) # e.g., 'image', 'document'
    attachment_url = Column(String, nullable=True)
    attachment_filename = Column(String, nullable=True)
    attachment_size = Column(Integer, nullable=True)
    attachment_thumbnail = Column(String, nullable=True)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    related_order = relationship("Order", foreign_keys=[related_order_id])
    related_product = relationship("Product", foreign_keys=[related_product_id])


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")


class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    product = relationship("Product")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='_user_favorite_uc'),
    )


class Banner(Base):
    __tablename__ = "banners"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=False)
    link_url = Column(String, nullable=True)
    banner_type = Column(String, nullable=True) # e.g., 'slider', 'promo'
    position = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Optional styling fields
    button_text = Column(String, nullable=True)
    button_link = Column(String, nullable=True)
    background_color = Column(String, nullable=True)
    text_color = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SMSMessage(Base):
    __tablename__ = "sms_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_phone = Column(String, nullable=False)
    message_body = Column(Text, nullable=False)
    status = Column(String, default="pending") # pending, sent, failed, delivered
    provider_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending") # pending, approved, rejected, paid
    payout_method = Column(String, nullable=False)
    transaction_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    seller = relationship("Seller", back_populates="withdrawal_requests")

Seller.withdrawal_requests = relationship("WithdrawalRequest", back_populates="seller")
User.returns = relationship("Return", back_populates="user")
Order.returns = relationship("Return", back_populates="order")


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    points_balance = Column(Integer, default=0)
    lifetime_points = Column(Integer, default=0)
    tier_id = Column(Integer, ForeignKey("reward_tiers.id"), nullable=True)
    referral_code = Column(String, unique=True, nullable=True)
    referrals_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="loyalty_account")
    tier = relationship("RewardTier")
    points_transactions = relationship("PointsTransaction", back_populates="loyalty_account")
    redemptions = relationship("Redemption", back_populates="loyalty_account")

User.loyalty_account = relationship("LoyaltyAccount", back_populates="user", uselist=False)


class RewardTier(Base):
    __tablename__ = "reward_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    min_points = Column(Integer, default=0)
    multiplier = Column(Float, default=1.0) # e.g., 1.2x points earning
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PointsTransaction(Base):
    __tablename__ = "points_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    type = Column(String, nullable=False) # e.g., 'earn', 'redeem', 'adjustment'
    points_amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="points_transactions")
    related_order = relationship("Order")


class Redemption(Base):
    __tablename__ = "redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    reward_tier_id = Column(Integer, ForeignKey("reward_tiers.id"), nullable=True) # If redeeming a tier-specific reward
    type = Column(String, nullable=False) # e.g., 'discount_code', 'free_shipping', 'cash_voucher'
    value = Column(Float, nullable=False) # e.g., 10.0 for $10 off or 0.1 for 10% off
    code = Column(String, unique=True, nullable=True) # The actual discount code
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="redemptions")
    reward_tier = relationship("RewardTier")


class ProductVariantOption(Base):
    __tablename__ = "product_variant_options"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    option_name = Column(String, nullable=False) # e.g., 'Color', 'Size'
    option_value = Column(String, nullable=False) # e.g., 'Red', 'Medium'
    
    __table_args__ = (
        UniqueConstraint('variant_id', 'option_name', name='_variant_option_uc'),
    )
    
    # Relationships
    product = relationship("Product")
    variant = relationship("ProductVariant")
