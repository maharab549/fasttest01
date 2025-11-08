"""
Quick script to add test variants to a product
"""
from app.database import SessionLocal
from app.models import Product, ProductVariant
import json

db = SessionLocal()

# Get first active product
product = db.query(Product).filter(Product.is_active == True).first()

if not product:
    print("❌ No active products found!")
    exit()

print(f"✅ Found product: {product.title} (ID: {product.id})")

# Create test variants
variants_data = [
    {
        "color": "Red",
        "size": "Small",
        "sku": f"{product.sku}-RED-S",
        "variant_name": "Red - Small",
        "price_adjustment": 0.0,
        "inventory_count": 50
    },
    {
        "color": "Red",
        "size": "Medium",
        "sku": f"{product.sku}-RED-M",
        "variant_name": "Red - Medium",
        "price_adjustment": 0.0,
        "inventory_count": 100
    },
    {
        "color": "Red",
        "size": "Large",
        "sku": f"{product.sku}-RED-L",
        "variant_name": "Red - Large",
        "price_adjustment": 0.0,
        "inventory_count": 75
    },
    {
        "color": "Blue",
        "size": "Small",
        "sku": f"{product.sku}-BLU-S",
        "variant_name": "Blue - Small",
        "price_adjustment": 2.0,
        "inventory_count": 30
    },
    {
        "color": "Blue",
        "size": "Medium",
        "sku": f"{product.sku}-BLU-M",
        "variant_name": "Blue - Medium",
        "price_adjustment": 2.0,
        "inventory_count": 60
    },
    {
        "color": "Black",
        "size": "Large",
        "sku": f"{product.sku}-BLK-L",
        "variant_name": "Black - Large",
        "price_adjustment": 5.0,
        "inventory_count": 40
    }
]

print(f"\n📦 Creating {len(variants_data)} variants...")

for data in variants_data:
    variant = ProductVariant(
        product_id=product.id,
        **data
    )
    db.add(variant)

# Update product to have variants flag
db.execute(
    Product.__table__.update().
    where(Product.id == product.id).
    values(has_variants=True)
)

db.commit()

print(f"✅ Created {len(variants_data)} variants successfully!")
print(f"✅ Product '{product.title}' now has variants enabled")
print(f"\n📋 Variants created:")
for v in variants_data:
    print(f"   - {v['variant_name']} (${v['price_adjustment']:+.2f}) - Stock: {v['inventory_count']}")

print(f"\n🔗 View product at: http://localhost:5173/products/{product.slug}")
print(f"🔗 Edit product at: http://localhost:5173/seller/products/edit/{product.id}")

db.close()
