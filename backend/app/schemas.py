from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str

class UserCreate(UserBase):
    password: str
    is_seller: bool = False

class UserLogin(BaseModel):
    username: str
    password: str

class ChatbotQuery(BaseModel):
    message: str

class ChatbotResponse(BaseModel):
    response: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_seller: Optional[bool] = None
    is_admin: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    is_seller: bool
    is_admin: bool
    created_at: datetime
    class Config: from_attributes = True

# Password Reset Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str
    def __init__(self, **data):
        super().__init__(**data)
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")

class PasswordResetToken(BaseModel):
    id: int
    user_id: int
    token: str
    is_used: bool
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

# Seller Schemas
class SellerBase(BaseModel):
    store_name: str
    store_description: Optional[str] = None
    store_slug: str

class SellerCreate(SellerBase):
    pass

class Seller(SellerBase):
    id: int
    user_id: int
    is_verified: bool
    rating: float
    total_sales: int
    payout_method: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_routing_number: Optional[str] = None
    paypal_email: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    compare_price: Optional[float] = None
    sku: Optional[str] = None # SKU can be optional
    inventory_count: int = 0
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    category_id: Optional[int] = None # Can be optional

class ProductCreate(ProductBase):
    images: Optional[List[str]] = None

class ProductCreateInput(BaseModel):
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    compare_price: Optional[float] = None
    sku: Optional[str] = None
    inventory_count: int = 0
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    category_id: int
    slug: Optional[str] = None

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: Optional[float] = None
    compare_price: Optional[float] = None
    inventory_count: Optional[int] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

# Product Image Schemas
class ProductImageBase(BaseModel):
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0

class ProductImageCreate(ProductImageBase):
    pass

class ProductImage(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime
    class Config: from_attributes = True

# Product Variant Schemas
class ProductVariantBase(BaseModel):
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    other_attributes: Optional[str] = None
    price_adjustment: float = 0.0
    inventory_count: int = 0
    images: Optional[List[str]] = None

class ProductVariantCreate(ProductVariantBase):
    product_id: int
    sku: Optional[str] = None
    variant_name: Optional[str] = None

class ProductVariantUpdate(BaseModel):
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    other_attributes: Optional[str] = None
    price_adjustment: Optional[float] = None
    inventory_count: Optional[int] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None

class ProductVariant(ProductVariantBase):
    id: int
    product_id: int
    sku: Optional[str] = None
    variant_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class Product(ProductBase):
    id: int
    seller_id: int
    seller: Optional[Seller] = None
    is_active: bool
    is_featured: bool
    has_variants: bool = False
    variants: List['ProductVariant'] = []
    approval_status: Optional[str] = "pending"
    rejection_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    rating: float
    review_count: Optional[int] = 0
    view_count: Optional[int] = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ProductRejection(BaseModel):
    reason: str

# Cart Schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int
    variant_id: Optional[int] = None

class CartItemCreate(CartItemBase):
    pass

class CartItem(CartItemBase):
    id: int
    user_id: int
    created_at: datetime
    product: Optional[Product] = None
    variant: Optional['ProductVariant'] = None
    class Config: from_attributes = True

# Order Schemas
class OrderItemBase(BaseModel):
    product_id: Optional[int] = None
    quantity: int
    unit_price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    total_price: float
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    product: Optional[Product] = None
    class Config: from_attributes = True

class OrderBase(BaseModel):
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    payment_method: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]
    discount_code: Optional[str] = None

class Order(OrderBase):
    id: int
    user_id: int
    user: Optional[User] = None
    order_number: str
    status: str
    total_amount: float
    shipping_amount: float
    tax_amount: float
    discount_amount: float
    payment_status: str
    payment_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    order_items: List[OrderItem] = []
    class Config: from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str

# Review Schemas
class ReviewBase(BaseModel):
    product_id: int
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    photos: Optional[List[str]] = None

class ReviewCreate(ReviewBase):
    order_id: Optional[int] = None

class Review(ReviewBase):
    id: int
    user_id: int
    order_id: Optional[int] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    user: Optional[User] = None
    photos: Optional[List[str]] = None
    class Config: from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Search and Filter Schemas
class ProductSearch(BaseModel):
    q: Optional[str] = None
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    page: int = 1
    per_page: int = 20

# Response Schemas
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

# Message Schemas
class MessageBase(BaseModel):
    receiver_id: int
    subject: Optional[str] = None
    content: Optional[str] = None
    related_order_id: Optional[int] = None
    related_product_id: Optional[int] = None
    attachment_type: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_filename: Optional[str] = None
    attachment_size: Optional[int] = None
    attachment_thumbnail: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    sender_id: int
    is_read: bool
    created_at: datetime
    sender: Optional[User] = None
    receiver: Optional[User] = None
    class Config: from_attributes = True

# Notification Schemas
class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"
    related_order_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    class Config: from_attributes = True

# Return Schemas
class ReturnItemBase(BaseModel):
    order_item_id: int
    product_id: int
    quantity: int
    reason: Optional[str] = None
    condition: Optional[str] = None
    images: Optional[List[str]] = None

class ReturnItemCreate(ReturnItemBase):
    pass

class ReturnItem(ReturnItemBase):
    id: int
    return_id: int
    class Config: from_attributes = True

class ReturnBase(BaseModel):
    order_id: int
    reason: str
    reason_details: Optional[str] = None
    refund_method: str = "original"

class ReturnCreate(ReturnBase):
    items: List[ReturnItemCreate]

class ReturnUpdate(BaseModel):
    status: Optional[str] = None
    refund_status: Optional[str] = None
    admin_notes: Optional[str] = None
    shipping_label_url: Optional[str] = None
    tracking_number: Optional[str] = None

class Return(ReturnBase):
    id: int
    return_number: str
    user_id: int
    status: str
    refund_amount: float
    refund_status: str
    refund_date: Optional[datetime] = None
    shipping_label_url: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    return_items: List[ReturnItem] = []
    class Config: from_attributes = True

# Loyalty & Rewards Schemas
class RewardTierBase(BaseModel):
    name: str
    min_points: int
    max_points: Optional[int] = None
    benefits: Optional[Dict[str, Any]] = None
    points_multiplier: float = 1.0
    icon: Optional[str] = None
    color: Optional[str] = None

class RewardTierCreate(RewardTierBase):
    pass

class RewardTier(RewardTierBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True

class LoyaltyAccountBase(BaseModel):
    points_balance: int = 0
    lifetime_points: int = 0
    referrals_count: int = 0

class LoyaltyAccountCreate(BaseModel):
    user_id: int

class LoyaltyAccount(LoyaltyAccountBase):
    id: int
    user_id: int
    tier_id: Optional[int] = None
    referral_code: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    tier: Optional[RewardTier] = None
    class Config: from_attributes = True

class PointsTransactionBase(BaseModel):
    transaction_type: str
    points_change: int
    source: str
    source_id: Optional[str] = None
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class PointsTransactionCreate(PointsTransactionBase):
    loyalty_account_id: int
    points_balance_after: int

class PointsTransaction(PointsTransactionBase):
    id: int
    loyalty_account_id: int
    points_balance_after: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

class RedemptionBase(BaseModel):
    redemption_type: str
    points_redeemed: int
    reward_value: float

class RedemptionCreate(RedemptionBase):
    pass

class RedemptionUpdate(BaseModel):
    status: Optional[str] = None
    used_at: Optional[datetime] = None

class Redemption(RedemptionBase):
    id: int
    loyalty_account_id: int
    reward_code: Optional[str] = None
    status: str
    order_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

class PointsEarnRequest(BaseModel):
    source: str
    source_id: Optional[str] = None
    points: int
    description: Optional[str] = None

class ReferralSignup(BaseModel):
    referral_code: str

class LoyaltyDashboard(BaseModel):
    account: LoyaltyAccount
    recent_transactions: List[PointsTransaction]
    active_redemptions: List[Redemption]
    next_tier: Optional[RewardTier] = None
    points_to_next_tier: Optional[int] = None

# Withdrawal Schemas
class WithdrawalRequestBase(BaseModel):
    amount: float

class WithdrawalRequestCreate(WithdrawalRequestBase):
    pass

class WithdrawalRequest(WithdrawalRequestBase):
    id: int
    seller_id: int
    status: str
    payout_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    payout_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


Product.model_rebuild()
CartItem.model_rebuild()
