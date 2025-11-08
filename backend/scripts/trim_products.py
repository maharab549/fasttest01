"""Trim the products table to a target count, deleting the rest safely.

Defaults:
- Keep the most recently created products (by created_at desc) up to --keep
- Exclude products that appear in OrderItem unless --force is used
- Deletes dependent rows (images, variants, cart_items, favorites, reviews, messages, return_items)
    before removing products to satisfy FKs

Usage (PowerShell):
    cd backend
    # Preview actions only
    venv/Scripts/python.exe scripts/trim_products.py --keep 500 --dry-run

    # Execute (safe mode: keeps products that have order history)
    venv/Scripts/python.exe scripts/trim_products.py --keep 500

    # Execute (force mode: also deletes OrderItem rows referencing products to be removed)
    venv/Scripts/python.exe scripts/trim_products.py --keep 500 --force
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app import models
from sqlalchemy import func


def parse_args():
    p = argparse.ArgumentParser(description="Trim products to target count.")
    p.add_argument("--keep", type=int, default=500, help="Number of products to keep.")
    p.add_argument("--strategy", choices=["recent", "oldest", "random"], default="recent",
                   help="Selection strategy for products to keep.")
    p.add_argument("--force", action="store_true", help="Also delete OrderItem rows for removed products.")
    p.add_argument("--dry-run", action="store_true", help="Preview actions without committing changes.")
    return p.parse_args()


def choose_keep_ids_no_image_pool(db, pool_ids: list[int], keep_needed: int, strategy: str) -> list[int]:
    if keep_needed <= 0:
        return []
    q = db.query(models.Product.id, models.Product.created_at).filter(models.Product.id.in_(pool_ids))
    if strategy == "recent":
        rows = q.order_by(models.Product.created_at.desc().nullslast(), models.Product.id.desc()).limit(keep_needed).all()
    elif strategy == "oldest":
        rows = q.order_by(models.Product.created_at.asc().nullsfirst(), models.Product.id.asc()).limit(keep_needed).all()
    else:  # random
        try:
            from sqlalchemy.sql import func as sa_func
            rows = q.order_by(sa_func.random()).limit(keep_needed).all()
        except Exception:
            rows = q.order_by(models.Product.id.asc()).limit(keep_needed).all()
    return [r[0] for r in rows]


def main():
    args = parse_args()
    db = SessionLocal()
    try:
        total = db.query(func.count(models.Product.id)).scalar() or 0
        if total <= args.keep:
            print(f"No action needed. Total products={total} <= keep={args.keep}")
            return

        # Identify products with any images (either JSON images column not empty OR related ProductImage rows)
        image_json_ids = [pid for (pid,) in db.query(models.Product.id)
                          .filter(models.Product.images.isnot(None))
                          .filter(models.Product.images != '[]')
                          .all()]
        product_image_ids = [pid for (pid,) in db.query(models.ProductImage.product_id).distinct().all()]
        protected_image_ids = set(image_json_ids) | set(product_image_ids)

        if len(protected_image_ids) > args.keep:
            print(f"Cannot trim to {args.keep}: there are {len(protected_image_ids)} products with images which must be kept.")
            print("Either increase --keep or relax the image protection requirement.")
            return

        # We must retain all protected image products, then fill remaining slots with no-image products per strategy
        remaining_slots = args.keep - len(protected_image_ids)
        # pool of no-image product IDs
        no_image_ids = [pid for (pid,) in db.query(models.Product.id).all() if pid not in protected_image_ids]
        chosen_no_image = choose_keep_ids_no_image_pool(db, no_image_ids, remaining_slots, args.strategy)
        keep_ids = list(protected_image_ids) + chosen_no_image
        keep_set = set(keep_ids)

        # Deletion candidates are only no-image products not chosen
        delete_ids = [pid for pid in no_image_ids if pid not in set(chosen_no_image)]

        # If not forcing, exclude products that are referenced by OrderItem
        if not args.force:
            ordered_ids = [pid for (pid,) in db.query(models.OrderItem.product_id)
                           .filter(models.OrderItem.product_id.in_(delete_ids)).distinct().all()]
            if ordered_ids:
                print(f"[SAFE] Excluding {len(ordered_ids)} products with order history from deletion.")
                delete_ids = [pid for pid in delete_ids if pid not in set(ordered_ids)]

        print(f"Planned delete count: {len(delete_ids)} out of total {total} (keeping {len(keep_ids)}). Protected (has images): {len(protected_image_ids)}")
        if args.dry_run:
            # Show a quick breakdown of dependent rows
            counts = {}
            for name, model, field in [
                ("ProductImage", models.ProductImage, models.ProductImage.product_id),
                ("ProductVariant", models.ProductVariant, models.ProductVariant.product_id),
                ("CartItem", models.CartItem, models.CartItem.product_id),
                ("Favorite", models.Favorite, models.Favorite.product_id),
                ("Review", models.Review, models.Review.product_id),
                ("Message", models.Message, models.Message.related_product_id),
                ("ReturnItem", models.ReturnItem, models.ReturnItem.product_id),
                ("OrderItem", models.OrderItem, models.OrderItem.product_id),
            ]:
                cnt = db.query(func.count(model.id)).filter(field.in_(delete_ids)).scalar() or 0
                counts[name] = cnt
            print("Dependent rows (to be deleted in this order, OrderItem only if --force):")
            for k in ["ProductImage", "ProductVariant", "CartItem", "Favorite", "Review", "Message", "ReturnItem", "OrderItem"]:
                print(f"  {k}: {counts[k]}")
            return

        # Delete dependents first in safe order
        batch_ids = delete_ids
        if not batch_ids:
            print("Nothing to delete after safety filters.")
            return

        # 1) Product images and variants (cascades exist, but explicit deletion ensures consistency)
        db.query(models.ProductImage).filter(models.ProductImage.product_id.in_(batch_ids)).delete(synchronize_session=False)
        db.query(models.ProductVariant).filter(models.ProductVariant.product_id.in_(batch_ids)).delete(synchronize_session=False)

        # 2) Cart, favorites, reviews, messages, returns
        db.query(models.CartItem).filter(models.CartItem.product_id.in_(batch_ids)).delete(synchronize_session=False)
        db.query(models.Favorite).filter(models.Favorite.product_id.in_(batch_ids)).delete(synchronize_session=False)
        db.query(models.Review).filter(models.Review.product_id.in_(batch_ids)).delete(synchronize_session=False)
        db.query(models.Message).filter(models.Message.related_product_id.in_(batch_ids)).delete(synchronize_session=False)
        db.query(models.ReturnItem).filter(models.ReturnItem.product_id.in_(batch_ids)).delete(synchronize_session=False)

        # 3) Order items (only if forced)
        if args.force:
            db.query(models.OrderItem).filter(models.OrderItem.product_id.in_(batch_ids)).delete(synchronize_session=False)

        # 4) Finally, delete products
        deleted = db.query(models.Product).filter(models.Product.id.in_(batch_ids)).delete(synchronize_session=False)
        db.commit()
        print(f"Deleted {deleted} products. Kept {len(keep_ids)}.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
