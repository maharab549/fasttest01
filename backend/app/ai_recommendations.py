from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import crud, models, schemas


def _safe_text(*parts: object) -> str:
    values: List[str] = []
    for part in parts:
        if part is None:
            continue
        values.append(str(part))
    return " ".join(values).strip().lower()


def _tokenize(text: str) -> Set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {tok for tok in tokens if len(tok) >= 3}


def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / float(len(union))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _co_purchase_scores(db: Session, product_id: int) -> Dict[int, float]:
    """
    Collaborative signal:
    products bought in the same orders as the target product.
    Returns normalized score in [0,1] per product_id.
    """
    order_ids = [
        int(order_id)
        for (order_id,) in db.query(models.OrderItem.order_id)
        .filter(models.OrderItem.product_id == product_id)
        .distinct()
        .all()
    ]
    if not order_ids:
        return {}

    rows = (
        db.query(models.OrderItem.product_id, func.count(models.OrderItem.id))
        .filter(models.OrderItem.order_id.in_(order_ids))
        .filter(models.OrderItem.product_id != product_id)
        .group_by(models.OrderItem.product_id)
        .all()
    )

    if not rows:
        return {}

    max_count = max(int(count) for _, count in rows)
    if max_count <= 0:
        return {}

    return {int(pid): int(count) / float(max_count) for pid, count in rows}


def _days_since(created_at: datetime | None) -> float:
    if created_at is None:
        return 365.0
    if created_at.tzinfo is None:
        now = datetime.utcnow()
        delta = now - created_at
    else:
        now = datetime.now(timezone.utc)
        delta = now - created_at.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds() / 86400.0)


def _popularity_score(product: models.Product) -> float:
    reviews = max(0, int(getattr(product, "review_count", 0) or 0))
    views = max(0, int(getattr(product, "view_count", 0) or 0))
    # Log scaling keeps extreme values from dominating.
    reviews_part = math.log1p(reviews) / math.log1p(250.0)
    views_part = math.log1p(views) / math.log1p(5000.0)
    return _clamp01(0.65 * reviews_part + 0.35 * views_part)


def get_product_recommendations(db: Session, product_id: int, limit: int = 5) -> List[schemas.Product]:
    """
    Hybrid recommendation algorithm.

    Signals used:
    - Collaborative: co-purchase frequency from order history
    - Content: category match + text similarity (title/description)
    - Price proximity
    - Product quality/popularity (rating + review/view counts)
    - Freshness (slight boost for newer inventory)

    The function returns ORM Product objects (as expected by existing callers).
    """
    target = crud.get_product(db, product_id)
    if not target:
        return []

    # Pull a candidate pool wide enough for ranking/diversity.
    # Only active + approved + in-stock products should be recommended.
    candidate_pool = (
        db.query(models.Product)
        .filter(models.Product.id != product_id)
        .filter(models.Product.is_active == True)
        .filter(models.Product.approval_status == "approved")
        .filter(models.Product.inventory_count > 0)
        .limit(max(300, limit * 40))
        .all()
    )
    if not candidate_pool:
        return []

    co_purchase = _co_purchase_scores(db, product_id)

    target_text = _safe_text(target.title, target.short_description, target.description)
    target_tokens = _tokenize(target_text)
    target_price = float(getattr(target, "price", 0.0) or 0.0)

    scored: List[tuple[float, models.Product]] = []
    for product in candidate_pool:
        # Collaborative signal (0..1)
        co_score = float(co_purchase.get(int(product.id), 0.0))

        # Category affinity (0..1)
        same_category = 1.0 if product.category_id == target.category_id else 0.0

        # Text/content similarity (0..1)
        product_text = _safe_text(product.title, product.short_description, product.description)
        content_score = _jaccard_similarity(target_tokens, _tokenize(product_text))

        # Price similarity (0..1)
        candidate_price = float(getattr(product, "price", 0.0) or 0.0)
        denom = max(target_price, candidate_price, 1.0)
        price_score = _clamp01(1.0 - abs(candidate_price - target_price) / denom)

        # Rating (0..1)
        rating_val = float(getattr(product, "rating", 0.0) or 0.0)
        rating_score = _clamp01(rating_val / 5.0)

        # Popularity (0..1)
        popularity = _popularity_score(product)

        # Freshness: exponential decay (half-life about 60 days)
        age_days = _days_since(getattr(product, "created_at", None))
        freshness = math.exp(-age_days / 60.0)
        freshness = _clamp01(freshness)

        # Gentle boost for manually featured inventory.
        featured_boost = 1.0 if bool(getattr(product, "is_featured", False)) else 0.0

        # Weighted hybrid score. Tuned for practical ecommerce behavior.
        score = (
            0.30 * co_score
            + 0.22 * same_category
            + 0.16 * content_score
            + 0.10 * price_score
            + 0.09 * rating_score
            + 0.08 * popularity
            + 0.03 * freshness
            + 0.02 * featured_boost
        )

        scored.append((score, product))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Lightweight diversity guard: avoid one seller dominating recommendations.
    seller_caps: Dict[int, int] = defaultdict(int)
    picked: List[models.Product] = []
    for _, product in scored:
        seller_id = int(getattr(product, "seller_id", 0) or 0)
        if seller_caps[seller_id] >= 2:
            continue
        picked.append(product)
        seller_caps[seller_id] += 1
        if len(picked) >= limit:
            break

    # Backfill if diversity guard over-filtered.
    if len(picked) < limit:
        picked_ids = {p.id for p in picked}
        for _, product in scored:
            if product.id in picked_ids:
                continue
            picked.append(product)
            if len(picked) >= limit:
                break

    return picked[:limit]
