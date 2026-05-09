from __future__ import annotations

import base64
import json
import logging
import os
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..config import settings
from ..database import get_db
from ..media_paths import make_absolute_media_url, resolve_media_file

router = APIRouter(prefix="/tryon", tags=["tryon"])
logger = logging.getLogger(__name__)

NVIDIA_IMAGE_EDIT_MODEL = "qwen-image-edit"
NVIDIA_IMAGE_EDIT_URL = "https://integrate.api.nvidia.com/v1/images/edits"
NVIDIA_IMAGE_EDIT_URL_CANDIDATES = [
    "https://integrate.api.nvidia.com/v1/images/edits",
    "https://integrate.api.nvidia.com/v1/openai/images/edits",
    "https://integrate.api.nvidia.com/v1/image/edits",
]

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional AI stack
    cv2 = None

try:
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover - optional AI stack
    mp = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional AI stack
    np = None

if mp is not None and not hasattr(mp, "solutions"):
    mp = None


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


def _infer_garment_prompt(product: models.Product) -> str:
    category_name = ((getattr(product.category, "name", None) or "") if getattr(product, "category", None) else "").strip().lower()
    title = (getattr(product, "title", None) or "").strip().lower()
    short_description = (getattr(product, "short_description", None) or "").strip().lower()
    description = (getattr(product, "description", None) or "").strip().lower()
    hint_text = " ".join(part for part in [category_name, title, short_description, description] if part)

    if any(token in hint_text for token in ("dress", "gown", "maxi", "kurti", "abaya", "frock")):
        return (
            "This product is a dress. Keep the dress length, waist placement, neckline, sleeve shape, and skirt drape natural. "
            "Maintain realistic flow from shoulders through waist and hips without turning it into a separate top and skirt."
        )
    if any(token in hint_text for token in ("jacket", "blazer", "coat", "hoodie", "cardigan", "outerwear")):
        return (
            "This product is a jacket or outerwear piece. Preserve the front opening, lapels, collar shape, zipper or button area, hem thickness, and layered structure. "
            "Make it sit naturally over the person's torso like a real outer layer."
        )
    if any(token in hint_text for token in ("shirt", "t-shirt", "tshirt", "tee", "top", "blouse", "polo")):
        return (
            "This product is a shirt or top. Preserve the neckline, shoulder seams, sleeve length, chest fit, and fabric fall across the torso. "
            "Keep the garment fitted like worn clothing rather than a flat overlay."
        )
    return (
        "Preserve the product's original fit, neckline, sleeve structure, hem, and fabric behavior so the result looks like the same garment being worn in real life."
    )


def _build_tryon_edit_prompt(product: models.Product) -> str:
    product_title = (getattr(product, "title", None) or "this product").strip()
    category_name = ((getattr(product.category, "name", None) or "") if getattr(product, "category", None) else "").strip()
    garment_context = f"Product name: {product_title}. "
    if category_name:
        garment_context += f"Category: {category_name}. "

    return (
        garment_context +
        "Transform this fashion preview into a photorealistic virtual try-on image. "
        "The garment already visible in the preview is the exact product that must be worn by the person. "
        "Keep the person's face, identity, body shape, pose, skin tone, hair, and background unchanged. "
        "Preserve the clothing category, neckline, sleeve length, silhouette, fabric texture, color, print placement, and brand details from the garment already shown. "
        "Blend the garment naturally onto the torso with realistic drape, folds, stitching, lighting, occlusion, and shadows so it looks truly worn instead of pasted. "
        f"{_infer_garment_prompt(product)} "
        "Do not add a second garment, do not replace the person, do not change the camera angle, and do not alter the lower body or background."
    )


def _encode_image_as_jpeg_bytes(img: Image.Image, quality: int = 92) -> bytes:
    buffer = BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _decode_image_from_b64(image_b64: str) -> Optional[Image.Image]:
    try:
        raw = base64.b64decode(image_b64)
        return Image.open(BytesIO(raw)).convert("RGBA")
    except Exception:
        return None


def _extract_nvidia_image_result(payload: object) -> Optional[dict[str, str]]:
    if not isinstance(payload, dict):
        return None

    direct_keys = ("b64_json", "image_base64", "image_b64", "output_b64")
    for key in direct_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return {"kind": "base64", "value": value.strip()}

    for key in ("url", "image_url", "output_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return {"kind": "url", "value": value.strip()}

    for key in ("data", "images", "outputs"):
        items = payload.get(key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    nested = _extract_nvidia_image_result(item)
                    if nested:
                        return nested

    nested = payload.get("result")
    if isinstance(nested, dict):
        return _extract_nvidia_image_result(nested)

    return None


def _load_image_from_url(image_url: str) -> Optional[Image.Image]:
    try:
        with urlopen(image_url, timeout=30) as response:
            data = response.read()
        return Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def _refine_tryon_with_nvidia(seed_img: Image.Image, product: models.Product) -> tuple[Optional[Image.Image], dict[str, object]]:
    api_key = (settings.nvidia_api_key or "").strip()
    if not api_key:
        return None, {
            "attempted": False,
            "applied": False,
            "reason": "missing_api_key",
            "model": NVIDIA_IMAGE_EDIT_MODEL,
        }

    try:
        import requests  # type: ignore
    except Exception:
        return None, {
            "attempted": False,
            "applied": False,
            "reason": "requests_unavailable",
            "model": NVIDIA_IMAGE_EDIT_MODEL,
        }

    image_bytes = _encode_image_as_jpeg_bytes(seed_img)
    files = {
        "image": ("tryon-seed.jpg", image_bytes, "image/jpeg"),
    }
    data = {
        "model": NVIDIA_IMAGE_EDIT_MODEL,
        "prompt": _build_tryon_edit_prompt(product),
        "response_format": "b64_json",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    custom_endpoint = (
        str(getattr(settings, "nvidia_image_edit_url", "") or "").strip()
        or str(os.getenv("NVIDIA_IMAGE_EDIT_URL", "") or "").strip()
        or str(os.getenv("NVIDIA_TRYON_IMAGE_EDIT_URL", "") or "").strip()
    )
    endpoints = [custom_endpoint] if custom_endpoint else [NVIDIA_IMAGE_EDIT_URL]
    for candidate in NVIDIA_IMAGE_EDIT_URL_CANDIDATES:
        if candidate not in endpoints:
            endpoints.append(candidate)

    last_failure_reason = "request_failed"
    last_failure_endpoint = endpoints[0]
    payload: object = {}
    result: Optional[dict[str, str]] = None

    for endpoint in endpoints:
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
        except Exception:
            last_failure_reason = "request_failed"
            last_failure_endpoint = endpoint
            continue

        if response.status_code >= 400:
            body_excerpt = ""
            try:
                body_excerpt = (response.text or "").strip().replace("\n", " ")[:180]
            except Exception:
                body_excerpt = ""
            last_failure_reason = f"http_{response.status_code}"
            if body_excerpt:
                last_failure_reason = f"{last_failure_reason}:{body_excerpt}"
            last_failure_endpoint = endpoint
            continue

        try:
            payload = response.json()
        except Exception:
            last_failure_reason = "invalid_json"
            last_failure_endpoint = endpoint
            continue

        result = _extract_nvidia_image_result(payload)
        if result:
            last_failure_endpoint = endpoint
            break

        last_failure_reason = "missing_image_output"
        last_failure_endpoint = endpoint

    if not result:
        return None, {
            "attempted": True,
            "applied": False,
            "reason": last_failure_reason,
            "model": NVIDIA_IMAGE_EDIT_MODEL,
            "endpoint": last_failure_endpoint,
        }

    refined_img: Optional[Image.Image] = None
    if result["kind"] == "base64":
        refined_img = _decode_image_from_b64(result["value"])
    elif result["kind"] == "url":
        refined_img = _load_image_from_url(result["value"])

    if refined_img is None:
        return None, {
            "attempted": True,
            "applied": False,
            "reason": f"unreadable_{result['kind']}_output",
            "model": NVIDIA_IMAGE_EDIT_MODEL,
            "endpoint": last_failure_endpoint,
        }

    return refined_img, {
        "attempted": True,
        "applied": True,
        "reason": "ok",
        "model": NVIDIA_IMAGE_EDIT_MODEL,
        "output_kind": result["kind"],
        "endpoint": last_failure_endpoint,
    }


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
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.35))
    rgb = Image.merge("RGB", layer.split()[:3])
    rgb = ImageEnhance.Color(rgb).enhance(1.04)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.03)
    layer = rgb.convert("RGBA")
    layer.putalpha(alpha)
    return layer


def _composite_with_soft_shadow(base: Image.Image, overlay: Image.Image, position: tuple[int, int]) -> Image.Image:
    composed = base.copy()

    shadow_alpha = overlay.getchannel("A").filter(ImageFilter.GaussianBlur(radius=6.0))
    if shadow_alpha.getbbox():
        shadow = Image.new("RGBA", overlay.size, (0, 0, 0, 92))
        shadow.putalpha(shadow_alpha.point(lambda value: int(value * 0.30)))
        composed.alpha_composite(shadow, (position[0] + 5, position[1] + 8))

    composed.alpha_composite(overlay, position)
    return composed


def _compose_tryon_heuristic(selfie_img: Image.Image, product_img: Image.Image) -> Image.Image:
    """Fallback placement when AI pose estimation is unavailable."""
    base = selfie_img.convert("RGBA")
    w, h = base.size

    if w < 256 or h < 256:
        raise HTTPException(status_code=400, detail="Selfie image is too small. Please upload a clearer photo.")

    product_layer = _prepare_product_layer(product_img)

    aspect_ratio = product_layer.width / max(product_layer.height, 1)
    max_width = int(w * 0.72)
    max_height = int(h * 0.56)

    target_h = max(int(h * 0.40), max_height)
    target_w = int(target_h * aspect_ratio)

    if target_w > max_width:
        target_w = max_width
        target_h = int(target_w / max(aspect_ratio, 0.01))

    target_w = max(int(w * 0.48), min(target_w, max_width))
    target_h = max(int(h * 0.34), min(target_h, max_height))

    fitted = product_layer.copy()
    fitted.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    overlay_w, overlay_h = fitted.size

    paste_x = int((w - overlay_w) * 0.5)
    paste_y = int(h * 0.23)
    if aspect_ratio < 0.85:
        paste_y = int(h * 0.20)
    elif aspect_ratio > 1.25:
        paste_y = int(h * 0.26)

    return _composite_with_soft_shadow(base, fitted, (paste_x, paste_y))


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


def _compose_tryon_ai(selfie_img: Image.Image, product_img: Image.Image, product: models.Product) -> tuple[Optional[Image.Image], dict[str, object]]:
    if cv2 is None or np is None:
        return None, {"pose_used": False, "nvidia": {"attempted": False, "applied": False, "reason": "cv_stack_unavailable"}}

    base = selfie_img.convert("RGBA")
    w, h = base.size
    if w < 256 or h < 256:
        raise HTTPException(status_code=400, detail="Selfie image is too small. Please upload a clearer photo.")

    torso_quad = _pose_torso_quad(base)
    if torso_quad is None:
        return None, {"pose_used": False, "nvidia": {"attempted": False, "applied": False, "reason": "pose_not_detected"}}

    garment = _prepare_product_layer(product_img)
    gw, gh = garment.size
    if gw < 4 or gh < 4:
        return None, {"pose_used": False, "nvidia": {"attempted": False, "applied": False, "reason": "garment_invalid"}}

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
    alpha = warped_img.getchannel("A").filter(ImageFilter.GaussianBlur(radius=1.6))
    warped_img.putalpha(alpha)

    seed_preview = _composite_with_soft_shadow(base, warped_img, (0, 0))
    refined, nvidia_debug = _refine_tryon_with_nvidia(seed_preview, product)
    if refined is not None:
        return refined, {"pose_used": True, "nvidia": nvidia_debug}

    return seed_preview, {"pose_used": True, "nvidia": nvidia_debug}


def _compose_tryon(selfie_img: Image.Image, product_img: Image.Image, product: models.Product) -> tuple[Image.Image, str, dict[str, object]]:
    """Prefer AI pose-guided composition and fallback to heuristic if needed."""
    ai_result, ai_debug = _compose_tryon_ai(selfie_img, product_img, product)
    if ai_result is not None:
        if bool(ai_debug.get("nvidia", {}).get("applied")):
            return ai_result, "AI pose-guided placement with NVIDIA refinement", {
                "render_path": "nvidia_refined",
                **ai_debug,
            }
        return ai_result, "AI pose-guided placement", {
            "render_path": "pose_guided",
            **ai_debug,
        }

    heuristic_result = _compose_tryon_heuristic(selfie_img, product_img)
    refined, nvidia_debug = _refine_tryon_with_nvidia(heuristic_result, product)
    if refined is not None:
        return refined, "Heuristic placement with NVIDIA refinement", {
            "render_path": "nvidia_refined",
            "pose_used": False,
            "nvidia": nvidia_debug,
        }

    return heuristic_result, "Smart fallback placement", {
        "render_path": "fallback_heuristic",
        "pose_used": bool(ai_debug.get("pose_used", False)),
        "nvidia": nvidia_debug,
    }


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

    composed, mode, debug_info = _compose_tryon(selfie_img, product_img, product)

    nvidia_debug = debug_info.get("nvidia") if isinstance(debug_info.get("nvidia"), dict) else {}
    render_path = debug_info.get("render_path")
    if render_path != "nvidia_refined":
        log_message = (
            "Try-on used fallback path for product_id=%s user_id=%s render_path=%s "
            "nvidia_attempted=%s nvidia_applied=%s reason=%s"
        )
        log_args = (
            product_id,
            current_user.id if current_user else 0,
            render_path,
            nvidia_debug.get("attempted", False),
            nvidia_debug.get("applied", False),
            nvidia_debug.get("reason", "unknown"),
        )
        if nvidia_debug.get("attempted", False):
            logger.warning(log_message, *log_args)
        else:
            logger.info(log_message, *log_args)

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
        "note": f"{mode} used for this preview.",
        "debug": {
            "used_nvidia_edit": debug_info.get("render_path") == "nvidia_refined",
            "render_path": debug_info.get("render_path"),
            "nvidia_refinement": debug_info.get("nvidia"),
            "pose_used": debug_info.get("pose_used", False),
        },
    }
