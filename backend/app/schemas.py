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
    
    class Config:
        from_attributes = True


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
    created_at: datetime
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True


# Product Schemas
class ProductBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    compare_price: Optional[float] = None
    sku: str
    inventory_count: int = 0
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    category_id: int


class ProductCreate(ProductBase):
    images: List[str]


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


class Product(ProductBase):
    id: int
    seller_id: int
    seller: Optional[Seller] = None
    is_active: bool
    is_featured: bool
    rating: float
    review_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Cart Schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int


class CartItemCreate(CartItemBase):
    pass


class CartItem(CartItemBase):
    id: int
    user_id: int
    created_at: datetime
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True


# Order Schemas
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int
    order_id: int
    total_price: float
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    payment_method: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class Order(OrderBase):
    id: int
    user_id: int
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
    
    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str


# Review Schemas
class ReviewBase(BaseModel):
    product_id: int
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    order_id: Optional[int] = None  # Will be set automatically by the API


class Review(ReviewBase):
    id: int
    user_id: int
    order_id: Optional[int] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    user: Optional[User] = None
    
    class Config:
        from_attributes = True


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
    sort_by: Optional[str] = "created_at"  # created_at, price, rating, title
    sort_order: Optional[str] = "desc"  # asc, desc
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
    content: Optional[str] = None  # Made optional for media-only messages
    related_order_id: Optional[int] = None
    related_product_id: Optional[int] = None
    
    # Media attachment fields
    attachment_type: Optional[str] = None  # 'image', 'video', 'sticker', 'file'
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
    
    class Config:
        from_attributes = True


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
    
    class Config:
        from_attributes = True