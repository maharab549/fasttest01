from __future__ import annotations

import base64
import json
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageFilter
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..media_paths import make_absolute_media_url, resolve_media_file

router = APIRouter(prefix="/tryon", tags=["tryon"])

try:
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional AI stack
    cv2 = None
    mp = None
    np = None


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


def _crop_to_visible_pixels(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _prepare_product_layer(product_img: Image.Image) -> Image.Image:
    # Clean catalog background, crop to garment bounds, and feather hard edges.
    layer = _remove_white_background(product_img.convert("RGBA"))
    layer = _crop_to_visible_pixels(layer)
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.2))
    layer.putalpha(alpha)
    return layer


def _compose_tryon_heuristic(selfie_img: Image.Image, product_img: Image.Image) -> Image.Image:
    """Fallback placement when AI pose estimation is unavailable."""
    base = selfie_img.convert("RGBA")
    w, h = base.size

    if w < 256 or h < 256:
        raise HTTPException(status_code=400, detail="Selfie image is too small. Please upload a clearer photo.")

    product_layer = _prepare_product_layer(product_img)

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


def _pose_torso_quad(selfie_img: Image.Image) -> Optional["np.ndarray"]:
    if mp is None or np is None:
        return None

    rgb = selfie_img.convert("RGB")
    w, h = rgb.size
    img_np = np.array(rgb)

    with mp.solutions.pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.45,
    ) as pose:
        result = pose.process(img_np)

    if not result.pose_landmarks:
        return None

    lms = result.pose_landmarks.landmark

    # MediaPipe pose landmarks indices.
    l_sh, r_sh, l_hp, r_hp = lms[11], lms[12], lms[23], lms[24]

    def is_valid(lm):
        return (getattr(lm, "visibility", 1.0) or 0.0) >= 0.35

    if not (is_valid(l_sh) and is_valid(r_sh) and is_valid(l_hp) and is_valid(r_hp)):
        return None

    def to_px(lm):
        return np.array([
            float(max(0.0, min(1.0, lm.x))) * (w - 1),
            float(max(0.0, min(1.0, lm.y))) * (h - 1),
        ], dtype=np.float32)

    left_sh = to_px(l_sh)
    right_sh = to_px(r_sh)
    left_hp = to_px(l_hp)
    right_hp = to_px(r_hp)

    center = (left_sh + right_sh + left_hp + right_hp) / 4.0

    # Expand quadrilateral so the garment covers shoulders/chest naturally.
    top_expand = 0.18
    bottom_expand = 0.10
    up_shift = 0.08
    down_shift = 0.06

    shoulder_vec = right_sh - left_sh
    hip_vec = right_hp - left_hp
    shoulder_up = np.array([0.0, -abs(shoulder_vec[0]) * up_shift], dtype=np.float32)
    hip_down = np.array([0.0, abs(hip_vec[0]) * down_shift], dtype=np.float32)

    tl = left_sh - shoulder_vec * top_expand + shoulder_up
    tr = right_sh + shoulder_vec * top_expand + shoulder_up
    br = right_hp + hip_vec * bottom_expand + hip_down
    bl = left_hp - hip_vec * bottom_expand + hip_down

    quad = np.array([tl, tr, br, bl], dtype=np.float32)

    quad[:, 0] = np.clip(quad[:, 0], 0, w - 1)
    quad[:, 1] = np.clip(quad[:, 1], 0, h - 1)

    # Reject degenerate quads.
    width_top = np.linalg.norm(quad[1] - quad[0])
    width_bottom = np.linalg.norm(quad[2] - quad[3])
    height_left = np.linalg.norm(quad[3] - quad[0])
    height_right = np.linalg.norm(quad[2] - quad[1])
    if min(width_top, width_bottom, height_left, height_right) < 24:
        return None

    if np.linalg.norm(center - quad.mean(axis=0)) > max(w, h):
        return None

    return quad


def _compose_tryon_ai(selfie_img: Image.Image, product_img: Image.Image) -> Optional[Image.Image]:
    if cv2 is None or np is None:
        return None

    base = selfie_img.convert("RGBA")
    w, h = base.size
    if w < 256 or h < 256:
        raise HTTPException(status_code=400, detail="Selfie image is too small. Please upload a clearer photo.")

    torso_quad = _pose_torso_quad(base)
    if torso_quad is None:
        return None

    garment = _prepare_product_layer(product_img)
    gw, gh = garment.size
    if gw < 4 or gh < 4:
        return None

    src = np.array(
        [[0, 0], [gw - 1, 0], [gw - 1, gh - 1], [0, gh - 1]],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(src, torso_quad.astype(np.float32))
    garment_np = np.array(garment)
    warped = cv2.warpPerspective(
        garment_np,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    warped_img = Image.fromarray(warped, mode="RGBA")

    # Soften edges to avoid sticker look.
    alpha = warped_img.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.0))
    warped_img.putalpha(alpha)

    composed = base.copy()
    composed.alpha_composite(warped_img)
    return composed


def _compose_tryon(selfie_img: Image.Image, product_img: Image.Image) -> Image.Image:
    """Prefer AI pose-guided composition and fallback to heuristic if needed."""
    ai_result = _compose_tryon_ai(selfie_img, product_img)
    if ai_result is not None:
        return ai_result
    return _compose_tryon_heuristic(selfie_img, product_img)


@router.post("/preview")
async def generate_tryon_preview(
    product_id: int = Form(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[schemas.User] = Depends(auth.get_current_active_user_optional),
):
    """
    Generate a virtual try-on preview using customer selfie + product image.

    Uses AI pose landmarks for garment placement when available and gracefully
    falls back to a heuristic compositor if AI dependencies are unavailable.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if selfie.content_type is None or not selfie.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported selfie format. Please upload an image file.")

    selfie_bytes = await selfie.read()
    if len(selfie_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded selfie is empty")
    if len(selfie_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Selfie image is too large. Maximum 25MB allowed.")

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
        "user_id": current_user.id if current_user else 0,
        "note": "AI try-on placement enabled when pose detection is available; fallback mode is used otherwise."
    }
