from app.database import SessionLocal
from app.models import Product, ProductVariant

db = SessionLocal()
slug = 'polo-shirt---brown'
product = db.query(Product).filter(Product.slug == slug).first()
if not product:
    print('Product not found:', slug)
    db.close()
    exit(1)

colors = ['Brown', 'Black', 'White']
sizes = ['S','M','L']
variants_created = 0
for color in colors:
    for size in sizes:
        sku = f"{product.sku}-{color[:3].upper()}-{size}"
        name = f"{color} - {size}"
        v = ProductVariant(
            product_id=product.id,
            sku=sku,
            variant_name=name,
            color=color,
            size=size,
            price_adjustment=0.0,
            inventory_count=30,
            images=None
        )
        db.add(v)
        variants_created += 1

# Set has_variants flag
from sqlalchemy import update

db.execute(
    Product.__table__.update().where(Product.id == product.id).values(has_variants=True)
)

db.commit()
print(f"Created {variants_created} variants for product id={product.id} ({product.title})")
db.close()
