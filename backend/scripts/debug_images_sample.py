import json
from app.database import SessionLocal
from app import models
from app.routers.products import format_product_for_response

if __name__ == '__main__':
    session = SessionLocal()
    try:
        # Sample first 20 products
        products = session.query(models.Product).order_by(models.Product.created_at.desc()).limit(20).all()
        rows = []
        for p in products:
            d = format_product_for_response(p, session)
            imgs = d.get('images') or []
            rows.append({
                'id': p.id,
                'slug': p.slug,
                'first_image': imgs[0] if imgs else None,
                'images_len': len(imgs)
            })
        print(json.dumps(rows, indent=2))
        
        # Find a product that has ProductImage rows
        pid = session.query(models.ProductImage.product_id).limit(1).scalar()
        print('\nProduct with ProductImage rows:', pid)
        if pid:
            p = session.query(models.Product).filter(models.Product.id==pid).first()
            d = format_product_for_response(p, session)
            print('detail for pid', pid, 'slug', p.slug)
            print(json.dumps({'images': d.get('images')}, indent=2))
    finally:
        session.close()
