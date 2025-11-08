"""Generate and attach placeholder product images at scale.

Creates at least N ProductImage rows and corresponding files under uploads/products/.
Standardizes products.images to a list of ProductImage IDs (converts any URL-only lists to IDs).

Usage (PowerShell):
  cd backend
  # Generate at least 500 images, ~2 per product
  python scripts/generate_bulk_product_images.py --min 500 --per-product 2

Options:
  --min INT           Minimum images to create (default 500)
  --per-product INT   Target images to add per product in this pass (default 2)
  --max-per-product INT  Maximum total images allowed per product after this pass (default 5)
  --dry-run           Show plan only

Works with both SQLite and Postgres via SQLAlchemy.
"""
from __future__ import annotations
import argparse
import random
import sys
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app import models


def parse_args():
    p = argparse.ArgumentParser(description="Generate placeholder product images and link them to products.")
    p.add_argument("--min", type=int, default=500, help="Minimum number of ProductImage rows to create.")
    p.add_argument("--per-product", type=int, default=2, help="Desired images to add per product in this pass.")
    p.add_argument("--max-per-product", type=int, default=5, help="Maximum total images per product after this pass.")
    p.add_argument("--dry-run", action="store_true", help="Preview actions without writing.")
    return p.parse_args()


def ensure_dirs() -> Path:
    uploads = BASE_DIR / "uploads"
    products_dir = uploads / "products"
    products_dir.mkdir(parents=True, exist_ok=True)
    return products_dir


def load_font(size: int = 28) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        # Try a common font if available
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def make_placeholder_image(title: str, out_path: Path, seed: int | None = None) -> None:
    rnd = random.Random(seed)
    w, h = 800, 800
    # Random pleasant background
    bg = (rnd.randint(80, 200), rnd.randint(80, 200), rnd.randint(80, 200))
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    font = load_font(36)
    subtitle_font = load_font(18)

    # Title text with wrap
    text = (title or "Product").strip()[:40]
    # Centered title
    # Compute text size via textbbox for wider Pillow compatibility
    title_bbox = draw.textbbox((0, 0), text, font=font)
    tw = title_bbox[2] - title_bbox[0]
    th = title_bbox[3] - title_bbox[1]
    draw.text(((w - tw) / 2, (h - th) / 2 - 20), text, fill=(255, 255, 255), font=font)

    # Footer brand bar
    bar_h = 60
    draw.rectangle([0, h - bar_h, w, h], fill=(0, 0, 0, 160))
    footer = "MegaMart"
    footer_bbox = draw.textbbox((0, 0), footer, font=subtitle_font)
    fw = footer_bbox[2] - footer_bbox[0]
    fh = footer_bbox[3] - footer_bbox[1]
    draw.text(((w - fw) / 2, h - bar_h + (bar_h - fh) / 2), footer, fill=(255, 255, 255), font=subtitle_font)

    img.save(out_path, format="JPEG", quality=85)


def standardize_product_images(db, product: models.Product) -> Tuple[list, bool]:
    """Ensure product.images is an ID list; convert URL strings into ProductImage rows.
    Returns (id_list, changed_flag)."""
    changed = False
    ids: list = []
    current_raw = getattr(product, "images", None)
    current = current_raw if isinstance(current_raw, list) else []
    if not current:
        return ids, changed

    if all(isinstance(x, int) for x in current):
        ids = list(current)
        return ids, changed

    order = 0
    for item in current:
        url = str(item)
        existing = db.query(models.ProductImage).filter(
            models.ProductImage.product_id == getattr(product, "id"),
            models.ProductImage.image_url == url
        ).first()
        if existing is None:
            existing = models.ProductImage(
                product_id=getattr(product, "id"),
                image_url=url,
                alt_text=getattr(product, "title", None),
                is_primary=False,
                sort_order=order,
            )
            db.add(existing)
            db.flush()
        ids.append(getattr(existing, "id"))
        order += 1

    setattr(product, "images", ids)
    changed = True
    return ids, changed


def has_primary(db, product_id: int) -> bool:
    return db.query(models.ProductImage.id).filter(
        models.ProductImage.product_id == product_id,
        models.ProductImage.is_primary.is_(True)
    ).first() is not None


def next_sort_order(db, product_id: int) -> int:
    row = db.query(models.ProductImage.sort_order).filter(
        models.ProductImage.product_id == product_id
    ).order_by(models.ProductImage.sort_order.desc()).first()
    return int(row[0]) + 1 if row else 0


def main() -> None:
    args = parse_args()
    products_dir = ensure_dirs()
    db = SessionLocal()
    created_images = 0
    touched_products = 0

    try:
        products = db.query(models.Product).order_by(models.Product.id.asc()).all()
        if not products:
            print("No products found. Seed products first.")
            return

        for product in products:
            if created_images >= args.min:
                break

            # Standardize existing images to ID list if necessary
            ids, changed = standardize_product_images(db, product)
            if changed and not args.dry_run:
                db.flush()

            # Determine how many we can add for this product
            current_total = len(ids)
            can_add = max(0, min(args.per_product, args.max_per_product - current_total))
            if can_add == 0:
                continue

            # Ensure one primary image exists at end
            product_id = getattr(product, "id")
            primary_exists = has_primary(db, product_id)

            for i in range(can_add):
                if created_images >= args.min:
                    break

                # Generate file
                filename = f"{product.id}_{created_images}_{random.getrandbits(40):010x}.jpg"
                out_path = products_dir / filename
                if not args.dry_run:
                    title_val = getattr(product, "title", None)
                    make_placeholder_image(title_val if isinstance(title_val, str) and title_val else f"Product {product_id}", out_path)

                url = f"/uploads/products/{filename}"
                is_primary = False if primary_exists or (current_total + i) > 0 else True
                sort_order = next_sort_order(db, product_id)

                # Create DB row
                if not args.dry_run:
                    img = models.ProductImage(
                        product_id=product.id,
                        image_url=url,
                        alt_text=product.title,
                        is_primary=is_primary,
                        sort_order=sort_order,
                    )
                    db.add(img)
                    db.flush()
                    ids.append(getattr(img, "id"))
                    setattr(product, "images", ids)

                created_images += 1

            if not args.dry_run:
                db.flush()
                touched_products += 1

            if created_images and created_images % 100 == 0:
                if not args.dry_run:
                    db.commit()
                print(f"Progress: created {created_images} images across ~{touched_products} products...")

        if not args.dry_run:
            db.commit()
        print(f"Done. Created {created_images} ProductImage rows. Touched products: {touched_products}.")
        print("Files saved under: uploads/products/")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
