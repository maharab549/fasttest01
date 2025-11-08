# Product Variants & Multiple Images Implementation Guide

## Current Status
✅ Backend Database: `Product` and `ProductVariant` models exist
✅ Database schema supports: color, size, material, style, price adjustments, variant-specific images
✅ Order/Cart models linked to variants

## What Needs to Be Done

### 1. **Backend API Enhancements** (Priority: HIGH)
- [ ] Create `ProductVariantCreate` and `ProductVariant` Pydantic schemas
- [ ] Create `ProductImage` model to store multiple images separately
- [ ] Add endpoints:
  - `POST /api/v1/products/{product_id}/images` - Upload/add images
  - `DELETE /api/v1/products/{product_id}/images/{image_id}` - Remove image
  - `PUT /api/v1/products/{product_id}/images/{image_id}/set-primary` - Set primary image
  - `POST /api/v1/products/{product_id}/variants` - Create variant
  - `PUT /api/v1/products/{product_id}/variants/{variant_id}` - Update variant
  - `DELETE /api/v1/products/{product_id}/variants/{variant_id}` - Delete variant
  - `GET /api/v1/products/{product_id}` - Return full product with images and variants

### 2. **Frontend Seller Dashboard** (Priority: HIGH)
- [ ] Create `SellerProductForm.jsx` - Form to add/edit products
  - Multiple image upload with preview
  - Drag-to-reorder images
  - Set primary image
  - Variant management (add/remove/edit color, size, RAM, storage, etc.)
  - Variant-specific pricing (base price + adjustment)
  - Variant inventory tracking
- [ ] Create `ProductImageUpload.jsx` - Image management component
- [ ] Create `VariantManager.jsx` - Variant CRUD UI

### 3. **Frontend Product Display** (Priority: MEDIUM)
- [ ] Update `ProductCard.jsx` - Show first image, badge showing variant count
- [ ] Create `ProductImageGallery.jsx` - Multi-image carousel with thumbnails
- [ ] Create `VariantSelector.jsx` - UI to select color/size/etc.
  - Show variant availability (in stock, out of stock, low stock)
  - Update price based on variant selection
  - Display variant-specific images

### 4. **Data Models** (Priority: HIGH)

#### ProductImage Table (New)
```
- id (primary key)
- product_id (foreign key to Product)
- image_url (string)
- alt_text (string)
- is_primary (boolean)
- sort_order (integer)
- created_at
```

#### ProductVariant (Already exists - needs schema)
```
- id
- product_id
- sku
- variant_name (e.g., "Red iPhone 15 Pro Max - 256GB")
- color
- size
- material
- storage (for electronics)
- ram (for electronics)
- style
- other_attributes (JSON for custom fields)
- price_adjustment
- inventory_count
- images (JSON array of image IDs)
- is_active
```

## Implementation Priority

### Phase 1 (Essential - Do First)
1. Create ProductImage model and migration
2. Add ProductVariant Pydantic schemas
3. Create API endpoints for images and variants
4. Test endpoints with Postman

### Phase 2 (UI - Do Second)
1. Create image upload component for sellers
2. Create variant manager UI
3. Integrate into seller product form

### Phase 3 (Display - Do Third)
1. Update product display to show all images
2. Add variant selector UI
3. Update cart/order to track selected variant

## Example Alibaba-Style Product Structure

```json
{
  "id": 1,
  "title": "iPhone 15 Pro Max",
  "description": "Latest Apple iPhone",
  "price": 999,
  "images": [
    {
      "id": 1,
      "url": "/uploads/iphone-1.jpg",
      "is_primary": true,
      "sort_order": 1
    },
    {
      "id": 2,
      "url": "/uploads/iphone-2.jpg",
      "is_primary": false,
      "sort_order": 2
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
      "images": [1, 2]
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
      "images": [2]
    }
  ]
}
```

## Next Steps
1. Start with Phase 1 (database + API)
2. Then Phase 2 (seller UI)
3. Finally Phase 3 (buyer UI)

---
**Estimated Timeline**: 2-3 hours for complete implementation
**Complexity**: Medium-High (requires DB changes + API updates + UI)
