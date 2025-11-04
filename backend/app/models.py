from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_seller = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    seller_profile = relationship("Seller", back_populates="user", uselist=False)


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
    is_active = Column(Boolean, default=True)
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
    dimensions = Column(JSON, nullable=True)  # {"length": 10, "width": 5, "height": 2}
    images = Column(JSON, nullable=True)  # ["image1.jpg", "image2.jpg"]
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
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
    
    # Shipping Information
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=True)
    
    # Payment Information
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid, failed, refunded
    payment_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


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
    user = relationship("User")
    order = relationship("Order")
    return_items = relationship("ReturnItem", back_populates="return_request")


class ReturnItem(Base):
    __tablename__ = "return_items"
    
    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)  # Specific reason for this item
    condition = Column(String, nullable=True)  # unopened, used, damaged
    images = Column(JSON, nullable=True)  # Photos of the item/issue
    
    # Relationships
    return_request = relationship("Return", back_populates="return_items")
    order_item = relationship("OrderItem")
    product = relationship("Product")


class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Link to order for delivery verification
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")
    order = relationship("Order")



class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, order_update, new_order, etc.
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    related_order = relationship("Order")



class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=True)  # Made nullable for media-only messages
    is_read = Column(Boolean, default=False)
    related_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    related_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    # Media attachment fields
    attachment_type = Column(String, nullable=True)  # 'image', 'video', 'sticker', 'file'
    attachment_url = Column(String, nullable=True)
    attachment_filename = Column(String, nullable=True)
    attachment_size = Column(Integer, nullable=True)  # in bytes
    attachment_thumbnail = Column(String, nullable=True)  # thumbnail URL for videos
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    related_order = relationship("Order")
    related_product = relationship("Product")




class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    product = relationship("Product")
    
    # Unique constraint to prevent duplicate favorites
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='unique_user_product_favorite'),)




class SMSMessage(Base):
    __tablename__ = "sms_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_phone = Column(String, nullable=False)
    message_content = Column(Text, nullable=False)
    sms_message_id = Column(String, nullable=True)  # External SMS provider message ID
    status = Column(String, default="pending")  # pending, sent, delivered, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sender = relationship("User")




class RewardTier(Base):
    __tablename__ = "reward_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Bronze, Silver, Gold, Platinum
    min_points = Column(Integer, nullable=False, default=0)
    max_points = Column(Integer, nullable=True)  # Null for highest tier
    benefits = Column(JSON, nullable=True)  # {"discount_percentage": 5, "free_shipping": true}
    points_multiplier = Column(Float, default=1.0)  # Earn points faster at higher tiers
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)  # Hex color for UI
    created_at = Column(DateTime(timezone=True), server_default=func.now())




class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    points_balance = Column(Integer, default=0)
    lifetime_points = Column(Integer, default=0)  # Total points ever earned
    tier_id = Column(Integer, ForeignKey("reward_tiers.id"), nullable=True)
    referral_code = Column(String, unique=True, index=True, nullable=False)
    referrals_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    tier = relationship("RewardTier")
    transactions = relationship("PointsTransaction", back_populates="loyalty_account")
    redemptions = relationship("Redemption", back_populates="loyalty_account")




class PointsTransaction(Base):
    __tablename__ = "points_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    transaction_type = Column(String, nullable=False)  # earn, redeem, expire, adjustment
    points_change = Column(Integer, nullable=False)  # Positive for earn, negative for spend
    points_balance_after = Column(Integer, nullable=False)
    source = Column(String, nullable=False)  # purchase, review, referral, signup_bonus, admin_adjustment
    source_id = Column(String, nullable=True)  # Order ID, Review ID, etc.
    description = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Additional context (renamed from metadata)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For expiring points
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="transactions")




class Redemption(Base):
    __tablename__ = "redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    redemption_type = Column(String, nullable=False)  # discount_code, free_shipping, gift_card, cashback
    points_redeemed = Column(Integer, nullable=False)
    reward_value = Column(Float, nullable=False)  # Monetary value or percentage
    reward_code = Column(String, unique=True, nullable=True)  # Discount/gift card code
    status = Column(String, default="active")  # active, used, expired, cancelled
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # If applied to an order
    expires_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="redemptions")
    order = relationship("Order")