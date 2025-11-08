"""Report product counts and image protection stats after trimming.

Outputs:
  - total_products
  - products_with_JSON_images (products.images JSON not null/empty)
  - products_with_ProductImage_rows (distinct product_ids in product_images)
  - protected_products_union (unique products having any images)
  - products_without_images
  - sample_without_images (first 10 IDs)
"""
from __future__ import annotations
import sys
from pathlib import Path
from sqlalchemy import func

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app import models


def main():
    db = SessionLocal()
    try:
        total = db.query(func.count(models.Product.id)).scalar() or 0
        json_image_ids = [pid for (pid,) in db.query(models.Product.id)
                          .filter(models.Product.images.isnot(None))
                          .filter(models.Product.images != '[]')
                          .all()]
        pm_ids = [pid for (pid,) in db.query(models.ProductImage.product_id).distinct().all()]
        protected_union = sorted(set(json_image_ids) | set(pm_ids))
        without_images = [pid for (pid,) in db.query(models.Product.id).all() if pid not in set(protected_union)]
        print({
            "total_products": total,
            "products_with_JSON_images": len(json_image_ids),
            "products_with_ProductImage_rows": len(pm_ids),
            "protected_products_union": len(protected_union),
            "products_without_images": len(without_images),
            "sample_without_images": without_images[:10],
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()
