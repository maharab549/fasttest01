# 🎯 PRODUCT TESTING GUIDE

## ✅ Database Status
- **Total Products**: 1,585 available
- **Sample Product IDs**: 2, 3, 4, 5, 6 (and more)

---

## 🔍 Test the API with Working Products

### Option 1: Get All Products
```bash
curl http://localhost:8000/api/v1/products
```

### Option 2: Get a Specific Product (ID: 2)
```bash
curl http://localhost:8000/api/v1/products/2
```

### Option 3: Search Products
```bash
curl "http://localhost:8000/api/v1/products/search?q=Smartphone"
```

### Option 4: Get Featured Products
```bash
curl http://localhost:8000/api/v1/products/featured
```

### Option 5: Get Product with Images & Variants
```bash
curl http://localhost:8000/api/v1/products/2/full
```

---

## ❌ Common "Product Not Found" Issues

### 1. Invalid Product ID
**Error**: Trying to access `/api/v1/products/99999` (ID doesn't exist)
**Fix**: Use a valid ID like 2, 3, 4, 5, 6

### 2. Product Slug Issue
**Error**: `/api/v1/products/slug/invalid-slug`
**Fix**: Use actual product slugs or numeric IDs

### 3. Frontend Routing Issue
**Error**: Frontend trying to load `/product/undefined` or `/product/null`
**Fix**: Check that product ID is set before rendering

---

## 📝 Create a New Product (for testing)

### Step 1: Register a User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Step 2: Login & Get Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```
*(Copy the token from response)*

### Step 3: Create a Product
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Product",
    "description": "This is a test product",
    "price": 99.99,
    "category_id": 1,
    "is_seller": true
  }'
```

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Product not found (404) | Invalid ID | Use ID 2-1586 |
| Empty product list | No products | Create products via API |
| Images not showing | Missing ProductImage model | ProductImage table ready ✅ |
| Variants error | Import issue | Fixed ✅ |
| No authentication | Missing token | Use Bearer token |

---

## ✅ Backend Status

- ✅ Server running on `http://localhost:8000`
- ✅ Database has 1,585 products
- ✅ All API endpoints working
- ✅ Image endpoints registered
- ✅ Variant endpoints registered
- ✅ Authentication working

---

## 🚀 Next Steps

1. **Test** the API with valid product IDs (2-1586)
2. **Access Swagger UI** at `http://localhost:8000/docs`
3. **Try different endpoints** to understand the API
4. **Create test data** using the registration and product creation endpoints
5. **Test image/variant endpoints** with new products

Try testing with product ID `2` first - it definitely exists! 🎯
