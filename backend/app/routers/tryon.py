from __future__ import annotations

import base64
import json
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..media_paths import make_absolute_media_url, resolve_media_file

router = APIRouter(prefix="/tryon", tags=["tryon"])


def _get_product_image_url(product: models.Product, db: Session) -> Optional[str]:
    """Resolve the best available product image URL/path."""
    product_images = (
        db.query(models.ProductImage)
        .filter(models.ProductImage.product_id == product.id)
        .order_by(models.ProductImage.is_primary.desc(), models.ProductImage.sort_order.asc(), models.ProductImage.id.asc())
        .all()
    )
    if product_images:
        return str(product_images[0].image_url)

    raw = getattr(product, "images", None)
    candidates: list[str] = []
    if isinstance(raw, list):
        if raw and all(isinstance(item, int) for item in raw):
            id_rows = db.query(models.ProductImage).filter(models.ProductImage.id.in_(raw)).all()
            id_to_url = {row.id: str(row.image_url) for row in id_rows}
            candidates = [id_to_url[i] for i in raw if i in id_to_url]
        else:
            candidates = [str(item).strip() for item in raw if item is not None and str(item).strip()]
    elif isinstance(raw, str):
        text = raw.strip()
        if text:
            try:
                loaded = json.loads(text)
                if isinstance(loaded, list):
                    candidates = [str(item).strip() for item in loaded if item is not None and str(item).strip()]
                else:
                    candidates = [text]
            except Exception:
                if "," in text:
                    candidates = [part.strip() for part in text.split(",") if part.strip()]
                else:
                    candidates = [text]

    return candidates[0] if candidates else None


def _load_product_image(product_image_ref: str) -> Image.Image:
    """
    Load product image from uploads path, same-host URL path, or absolute URL.
    Returns an RGBA image.
    """
    parsed = urlparse(product_image_ref)

    local_path = resolve_media_file(product_image_ref)
    if local_path and local_path.is_file():
        return Image.open(local_path).convert("RGBA")

    if parsed.path and parsed.path.startswith("/uploads/"):
        mapped = resolve_media_file(parsed.path)
        if mapped and mapped.is_file():
            return Image.open(mapped).convert("RGBA")

    if parsed.scheme in {"http", "https"}:
        with urlopen(product_image_ref, timeout=15) as response:
            data = response.read()
        return Image.open(BytesIO(data)).convert("RGBA")

    raise HTTPException(status_code=400, detail="Product image is unavailable for try-on")


def _remove_white_background(img: Image.Image) -> Image.Image:
    """Simple background cleaner for catalog images with plain white background."""
    rgba = img.convert("RGBA")
    pixels = rgba.getdata()
    cleaned = []
    for r, g, b, a in pixels:
        if r > 245 and g > 245 and b > 245:
            cleaned.append((r, g, b, 0))
        else:
            cleaned.append((r, g, b, a))
    rgba.putdata(cleaned)
    return rgba


def _compose_tryon(selfie_img: Image.Image, product_img: Image.Image) -> Image.Image:
    """
    MVP heuristic placement:
    - Place product roughly on torso region for clothing-like preview.
    - Works best when product photo is front-facing and white-background.
    """
    base = selfie_img.convert("RGBA")
    w, h = base.size

    if w < 256 or h < 256:
        raise HTTPException(status_code=400, detail="Selfie image is too small. Please upload a clearer photo.")

    product_layer = _remove_white_background(product_img.convert("RGBA"))

    # Target torso area
    target_w = int(w * 0.62)
    target_h = int(h * 0.55)
    x = int((w - target_w) * 0.5)
    y = int(h * 0.25)

    product_layer.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    overlay_w, overlay_h = product_layer.size
    paste_x = x + max((target_w - overlay_w) // 2, 0)
    paste_y = y + max((target_h - overlay_h) // 2, 0)

    composed = base.copy()
    composed.alpha_composite(product_layer, (paste_x, paste_y))
    return composed


@router.post("/preview")
async def generate_tryon_preview(
    product_id: int = Form(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    """
    Generate a quick virtual try-on preview using customer selfie + product image.

    This is an MVP heuristic compositor (non-3D, non-body-tracking) to validate
    UX and conversion impact before investing in advanced AR/AI providers.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if selfie.content_type is None or not selfie.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported selfie format. Please upload an image file.")

    selfie_bytes = await selfie.read()
    if len(selfie_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded selfie is empty")
    if len(selfie_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Selfie image is too large. Maximum 10MB allowed.")

    product_image_ref = _get_product_image_url(product, db)
    if not product_image_ref:
        raise HTTPException(status_code=400, detail="This product has no image available for try-on")

    try:
        selfie_img = Image.open(BytesIO(selfie_bytes)).convert("RGBA")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid selfie image")

    try:
        product_img = _load_product_image(product_image_ref)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to load product image for try-on")

    composed = _compose_tryon(selfie_img, product_img)

    # Encode the composed image as JPEG base64 so no disk storage is needed.
    # Render's filesystem is ephemeral — saved files vanish on redeploy.
    buffer = BytesIO()
    composed_rgb = composed.convert("RGB")
    composed_rgb.save(buffer, format="JPEG", quality=85, optimize=True)
    buffer.seek(0)
    preview_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "success": True,
        "message": "Try-on preview generated",
        "preview_url": "",
        "preview_base64": preview_base64,
        "product_image_url": make_absolute_media_url(product_image_ref),
        "product_id": product_id,
        "user_id": current_user.id,
        "note": "MVP preview uses heuristic placement and works best with front-facing selfies."
    }
