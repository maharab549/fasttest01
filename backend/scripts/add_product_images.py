"""
Add product images into the database and wire them to a product properly.

This script:
- Inserts rows into product_images (one per URL)
- Updates products.images JSON field to hold the inserted ProductImage IDs (in order)
- Marks the first image as primary by default (configurable)

Works with both SQLite and Postgres because it uses the existing SQLAlchemy setup.

Usage (PowerShell):
  cd backend
  # By product ID
  python scripts/add_product_images.py --product-id 123 --urls "https://example.com/a.jpg" "https://example.com/b.jpg"

  # By product slug
  python scripts/add_product_images.py --slug "my-product-slug" --urls "https://example.com/a.jpg" --primary-index 0

Options:
  --product-id INT     Select product by numeric ID
  --slug TEXT          Select product by slug (alternative to --product-id)
  --urls ...           One or more image URLs to add in order
  --primary-index INT  Which URL index should be primary (default 0)
  --alt TEXT           Optional alt text applied to all images (can be edited later)

Exit status is non-zero on error.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app import models


def parse_args():
    p = argparse.ArgumentParser(description="Add product images and link them to a product.")
    sel = p.add_mutually_exclusive_group(required=True)
    sel.add_argument("--product-id", type=int, help="Product numeric ID")
    sel.add_argument("--slug", type=str, help="Product slug")
    p.add_argument("--urls", nargs="+", required=True, help="One or more image URLs")
    p.add_argument("--primary-index", type=int, default=0, help="Index into --urls that is primary (default 0)")
    p.add_argument("--alt", type=str, default=None, help="Alt text applied to all images (optional)")
    return p.parse_args()


def main():
    args = parse_args()
    urls: List[str] = args.urls
    if len(urls) == 0:
        print("ERROR: provide at least one URL", file=sys.stderr)
        sys.exit(1)
    if not (0 <= args.primary_index < len(urls)):
        print("ERROR: --primary-index out of range", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Locate product
        product = None
        if args.product_id is not None:
            product = db.query(models.Product).filter(models.Product.id == args.product_id).first()
        else:
            product = db.query(models.Product).filter(models.Product.slug == args.slug).first()

        if product is None:
            print("ERROR: Product not found", file=sys.stderr)
            sys.exit(1)

        # Insert ProductImage rows
        created_images: List[models.ProductImage] = []
        for idx, url in enumerate(urls):
            img = models.ProductImage(
                product_id=product.id,
                image_url=url,
                alt_text=args.alt,
                is_primary=(idx == args.primary_index),
                sort_order=idx,
            )
            db.add(img)
            created_images.append(img)
        db.flush()  # assign IDs

        # Update product.images JSON to be list of the inserted IDs
        id_list = [img.id for img in created_images]
        existing = product.images if isinstance(product.images, list) else []
        # Replace entirely with the new ordered list; if you prefer to append, do: existing + id_list
        product.images = id_list

        db.commit()
        print(f"OK: Added {len(id_list)} image(s) to product id={product.id}, slug={product.slug}")
        print("IDs:", id_list)
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
