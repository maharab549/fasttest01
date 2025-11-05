# MegaMart API Documentation

## Overview

MegaMart is a comprehensive e-commerce platform API built with FastAPI, featuring:
- Multi-vendor marketplace support
- AI-powered features (chatbot, recommendations, search)
- Real-time messaging with WebSocket
- Advanced product management
- Payment processing with Stripe
- Order tracking and returns management
- Loyalty program system

**Base URL:** `http://localhost:8000/api/v1`  
**Documentation:** `http://localhost:8000/api/docs`  
**Alternative Docs:** `http://localhost:8000/api/redoc`

---

## Authentication

### Register New User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "is_seller": false,
  "is_admin": false
}
```

### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer {access_token}
```

---

## Products

### Get All Products
```http
GET /products?skip=0&limit=20&search=phone&category_id=1&min_price=100&max_price=1000&sort_by=price_asc
```

**Query Parameters:**
- `skip` (int): Number of items to skip (pagination)
- `limit` (int): Number of items to return
- `search` (string): Search term for product title/description
- `category_id` (int): Filter by category
- `min_price` (float): Minimum price filter
- `max_price` (float): Maximum price filter
- `sort_by` (string): Sort options: `price_asc`, `price_desc`, `rating_desc`, `newest`

**Response:**
```json
[
  {
    "id": 1,
    "title": "Premium Smartphone",
    "slug": "premium-smartphone",
    "price": 799.99,
    "compare_price": 999.99,
    "rating": 4.5,
    "review_count": 128,
    "images": ["image1.jpg", "image2.jpg"],
    "is_featured": true,
    "seller": {
      "id": 1,
      "store_name": "Tech Store",
      "rating": 4.8
    },
    "category": {
      "id": 1,
      "name": "Electronics",
      "slug": "electronics"
    }
  }
]
```

### Get Product by ID
```http
GET /products/{product_id}
```

### Get Featured Products
```http
GET /products/featured?limit=10
```

### Create Product (Seller Only)
```http
POST /products
Authorization: Bearer {seller_token}
Content-Type: application/json

{
  "category_id": 1,
  "title": "New Product",
  "slug": "new-product",
  "description": "Product description",
  "short_description": "Short desc",
  "price": 99.99,
  "compare_price": 129.99,
  "sku": "SKU-001",
  "inventory_count": 100,
  "images": ["image1.jpg"]
}
```

---

## Cart

### Get Cart Items
```http
GET /cart
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "product_id": 10,
      "quantity": 2,
      "product": {
        "id": 10,
        "title": "Product Name",
        "price": 49.99,
        "images": ["image.jpg"]
      }
    }
  ],
  "total_price": 99.98
}
```

### Add to Cart
```http
POST /cart/add
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "product_id": 10,
  "quantity": 2
}
```

### Update Cart Item
```http
PUT /cart/{cart_item_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "quantity": 3
}
```

### Remove from Cart
```http
DELETE /cart/{cart_item_id}
Authorization: Bearer {access_token}
```

---

## Orders

### Create Order
```http
POST /orders
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "shipping_address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip_code": "10001",
    "country": "USA"
  },
  "payment_method": "stripe"
}
```

**Response:**
```json
{
  "id": 1,
  "order_number": "ORD-20231105-001",
  "status": "pending",
  "total_amount": 149.98,
  "order_items": [...],
  "created_at": "2023-11-05T10:30:00Z"
}
```

### Get User Orders
```http
GET /orders
Authorization: Bearer {access_token}
```

### Get Order by ID
```http
GET /orders/{order_id}
Authorization: Bearer {access_token}
```

### Track Order
```http
GET /orders/{order_id}/track
Authorization: Bearer {access_token}
```

---

## Reviews

### Create Review
```http
POST /reviews
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "product_id": 10,
  "order_id": 5,
  "rating": 5,
  "title": "Great product!",
  "comment": "Exactly as described, fast shipping."
}
```

### Get Product Reviews
```http
GET /reviews/product/{product_id}?skip=0&limit=10
```

---

## Seller Dashboard

### Become a Seller
```http
POST /seller/register
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "store_name": "My Store",
  "store_description": "Best products",
  "store_slug": "my-store"
}
```

### Get Seller Dashboard Stats
```http
GET /seller/dashboard
Authorization: Bearer {seller_token}
```

**Response:**
```json
{
  "total_products": 45,
  "total_sales": 1250,
  "total_revenue": 45678.90,
  "pending_orders": 12,
  "balance": 38500.00,
  "recent_orders": [...]
}
```

### Get Seller Orders
```http
GET /seller/orders?status=pending
Authorization: Bearer {seller_token}
```

### Update Order Status
```http
PUT /seller/orders/{order_id}/status
Authorization: Bearer {seller_token}
Content-Type: application/json

{
  "status": "shipped",
  "tracking_number": "TRACK123"
}
```

### Request Withdrawal
```http
POST /seller/withdrawal
Authorization: Bearer {seller_token}
Content-Type: application/json

{
  "amount": 1000.00,
  "bank_account": "****1234"
}
```

---

## Admin

### Get All Users
```http
GET /admin/users?skip=0&limit=50
Authorization: Bearer {admin_token}
```

### Get All Orders
```http
GET /admin/orders?status=pending
Authorization: Bearer {admin_token}
```

### Approve Product
```http
PUT /admin/products/{product_id}/approve
Authorization: Bearer {admin_token}
```

### Reject Product
```http
PUT /admin/products/{product_id}/reject
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "rejection_reason": "Does not meet quality standards"
}
```

### System Health Monitoring
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 86400,
  "cpu_usage_percent": 25.5,
  "memory_usage_percent": 45.2,
  "disk_usage_percent": 60.0,
  "database_records": {
    "total_users": 1523,
    "total_products": 8945,
    "total_orders": 3421,
    "active_users_24h": 245,
    "pending_orders": 12
  },
  "network_stats": {
    "bytes_sent_mb": 1245.67,
    "bytes_recv_mb": 3456.89
  },
  "issues": []
}
```

---

## AI Features

### AI Chatbot
```http
POST /chatbot
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "What are the best smartphones under $500?",
  "conversation_id": "optional-conversation-id"
}
```

### AI Product Recommendations
```http
GET /products/recommendations?user_id=1&limit=10
Authorization: Bearer {access_token}
```

### AI Image Search
```http
POST /products/search/image
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file=@image.jpg
```

---

## WebSocket (Real-time Messaging)

### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{user_id}?token={access_token}');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('New message:', message);
};

// Send message
ws.send(JSON.stringify({
  receiver_id: 2,
  content: "Hello!",
  type: "text"
}));
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse:
- **60 requests per minute** per IP address
- **1000 requests per hour** per IP address

Rate limit headers in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699185600
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Too Many Requests (Rate Limit)
- `500` - Internal Server Error

---

## Security

### Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: ...`

### Authentication
JWT tokens are used for authentication:
1. Login to receive a token
2. Include token in `Authorization: Bearer {token}` header
3. Tokens expire after 7 days

### CORS
CORS is configured for allowed origins only:
- Production: `https://megamartcom.netlify.app`
- Development: `http://localhost:5173`

---

## Database Optimization

The API includes comprehensive database optimizations:
- **36 indexes** on frequently queried fields
- **Connection pooling** for PostgreSQL (production)
- **Query optimization** with eager loading
- **Automatic cleanup** of expired data

---

## Testing

Run tests with pytest:
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

---

## Environment Variables

Required environment variables:

```env
# Database
DATABASE_URL=sqlite:///./marketplace.db
# or for PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# AI Services
GOOGLE_API_KEY=your-google-api-key
GROQ_API_KEY=your-groq-api-key

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
```

---

## Support

For issues or questions:
- GitHub Issues: [github.com/maharab549/fasttest01](https://github.com/maharab549/fasttest01)
- API Version: 1.1.1
- Last Updated: November 2023
