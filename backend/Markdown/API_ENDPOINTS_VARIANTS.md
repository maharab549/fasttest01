# API Endpoints Implementation Guide

## Summary
This document outlines the REST API endpoints needed for the multi-image, multi-variant product system.

## Endpoints to Create

### 1. Product Images

#### Add Image to Product
```
POST /api/v1/products/{product_id}/images
Content-Type: multipart/form-data

Parameters:
  - image_url: str (uploaded file or URL)
  - alt_text: str (optional)
  - is_primary: bool (optional, default: false)

Response (201):
{
  "id": 1,
  "product_id": 1,
  "image_url": "/uploads/products/image1.jpg",
  "alt_text": "Product front view",
  "is_primary": true,
  "sort_order": 0,
  "created_at": "2025-11-06T12:00:00Z"
}
```

#### Get All Product Images
```
GET /api/v1/products/{product_id}/images

Response (200):
{
  "images": [
    {
      "id": 1,
      "product_id": 1,
      "image_url": "/uploads/products/image1.jpg",
      "alt_text": "Front view",
      "is_primary": true,
      "sort_order": 0
    },
    {
      "id": 2,
      "product_id": 1,
      "image_url": "/uploads/products/image2.jpg",
      "alt_text": "Side view",
      "is_primary": false,
      "sort_order": 1
    }
  ]
}
```

#### Update Image
```
PUT /api/v1/products/{product_id}/images/{image_id}

Body:
{
  "alt_text": "New alt text",
  "is_primary": false,
  "sort_order": 2
}

Response (200): Updated ProductImage object
```

#### Delete Image
```
DELETE /api/v1/products/{product_id}/images/{image_id}

Response (204): No content
```

#### Set Primary Image
```
PUT /api/v1/products/{product_id}/images/{image_id}/set-primary

Response (200):
{
  "message": "Image set as primary",
  "image_id": 1
}
```

---

### 2. Product Variants

#### Create Variant
```
POST /api/v1/products/{product_id}/variants

Body:
{
  "sku": "IPHONE-15-GOLD-256",
  "variant_name": "Gold 256GB",
  "color": "Gold",
  "storage": "256GB",
  "ram": "8GB",
  "price_adjustment": 0.0,
  "inventory_count": 50
}

Response (201): ProductVariant object
```

#### Get All Variants
```
GET /api/v1/products/{product_id}/variants

Response (200):
{
  "variants": [
    {
      "id": 1,
      "sku": "IPHONE-15-GOLD-256",
      "variant_name": "Gold 256GB",
      "color": "Gold",
      "storage": "256GB",
      "ram": "8GB",
      "price_adjustment": 0,
      "inventory_count": 50,
      "is_active": true
    }
  ]
}
```

#### Get Single Variant
```
GET /api/v1/products/{product_id}/variants/{variant_id}

Response (200): ProductVariant object
```

#### Update Variant
```
PUT /api/v1/products/{product_id}/variants/{variant_id}

Body:
{
  "inventory_count": 45,
  "price_adjustment": 50.0,
  "is_active": true
}

Response (200): Updated ProductVariant object
```

#### Delete Variant
```
DELETE /api/v1/products/{product_id}/variants/{variant_id}

Response (204): No content
```

---

### 3. Enhanced Product Endpoints

#### Get Product with Images and Variants
```
GET /api/v1/products/{product_id}

Response (200):
{
  "id": 1,
  "title": "iPhone 15 Pro Max",
  "price": 999,
  "has_variants": true,
  "product_images": [
    {
      "id": 1,
      "image_url": "/uploads/iphone-1.jpg",
      "alt_text": "Front view",
      "is_primary": true,
      "sort_order": 0
    },
    {
      "id": 2,
      "image_url": "/uploads/iphone-2.jpg",
      "alt_text": "Back view",
      "is_primary": false,
      "sort_order": 1
    }
  ],
  "variants": [
    {
      "id": 1,
      "sku": "IPHONE-15-GOLD-256",
      "variant_name": "Gold 256GB",
      "color": "Gold",
      "storage": "256GB",
      "ram": "8GB",
      "price_adjustment": 0,
      "inventory_count": 50,
      "is_active": true
    },
    {
      "id": 2,
      "sku": "IPHONE-15-SILVER-512",
      "variant_name": "Silver 512GB",
      "color": "Silver",
      "storage": "512GB",
      "ram": "8GB",
      "price_adjustment": 100,
      "inventory_count": 30,
      "is_active": true
    }
  ]
}
```

#### Create Product with Variants
```
POST /api/v1/products

Body:
{
  "title": "iPhone 15 Pro Max",
  "description": "Latest iPhone",
  "price": 999,
  "category_id": 1,
  "sku": "IPHONE-15-BASE",
  "has_variants": true,
  "variants": [
    {
      "sku": "IPHONE-15-GOLD-256",
      "variant_name": "Gold 256GB",
      "color": "Gold",
      "storage": "256GB",
      "ram": "8GB",
      "price_adjustment": 0,
      "inventory_count": 50
    }
  ]
}

Response (201): Product object with variants
```

---

## Implementation Files

Create/Update these files in `backend/app/routers/`:

1. `products.py` - Add new endpoints for images and variants
2. Or create new router file: `product_images.py` and `product_variants.py`

## Database Changes

Run migration:
```bash
cd backend
python app/migration_product_images.py
```

## Testing with cURL

```bash
# Create product
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15",
    "price": 999,
    "category_id": 1,
    "sku": "IPHONE-15",
    "has_variants": true
  }'

# Add image
curl -X POST http://localhost:8000/api/v1/products/1/images \
  -F "image_url=@/path/to/image.jpg" \
  -F "alt_text=iPhone front view" \
  -F "is_primary=true"

# Create variant
curl -X POST http://localhost:8000/api/v1/products/1/variants \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "IPHONE-15-GOLD-256",
    "variant_name": "Gold 256GB",
    "color": "Gold",
    "storage": "256GB",
    "ram": "8GB",
    "price_adjustment": 0,
    "inventory_count": 50
  }'
```

---

**Next Step**: Implement these endpoints in `routers/products.py`
