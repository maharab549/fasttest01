from __future__ import annotations

from pathlib import Path

from .config import settings


BACKEND_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_ROOT = BACKEND_ROOT / "uploads"

# Legacy seed data still references a few old filenames that were never copied
# into the deployed uploads directory. Map them to real files so older rows keep
# working without forcing manual DB surgery.
MEDIA_PATH_ALIASES = {
    "/uploads/headphones.jpg": "/uploads/wireless-headphones.jpg",
    "/uploads/tshirt.jpg": "/uploads/cotton-t-shirt-basic-14.png",
    "/sliders/hero-slider-1.png": "/uploads/banners/banner_20251105_141916.png",
    "/sliders/hero-slider-2.png": "/uploads/banners/banner_20251105_141949.jpg",
    "/sliders/hero-slider-3.png": "/uploads/banners/banner_20251105_142026.png",
    "/sliders/hero-slider-4.png": "/uploads/banners/banner_20251105_141916.png",
    "/banners/sale-banner-1.jpg": "/uploads/banners/banner_20251105_141949.jpg",
}


def _normalize_slashes(path: str) -> str:
    return path.replace("\\", "/")


def _ensure_leading_slash(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def _uploads_file_for_path(path: str) -> Path | None:
    clean = _normalize_slashes(path)
    if clean.startswith("/uploads/"):
        return UPLOADS_ROOT / clean.removeprefix("/uploads/")
    if clean.startswith("uploads/"):
        return UPLOADS_ROOT / clean.removeprefix("uploads/")
    return None


def normalize_media_path(path: str | None) -> str:
    if not path:
        return ""

    clean = _ensure_leading_slash(_normalize_slashes(str(path).strip()))
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean

    aliased = MEDIA_PATH_ALIASES.get(clean)
    if aliased:
        return aliased

    # Some rows stored banner-like paths without the /uploads prefix.
    if clean.startswith("/banners/") or clean.startswith("/sliders/"):
        uploads_candidate = f"/uploads{clean}"
        uploads_file = _uploads_file_for_path(uploads_candidate)
        if uploads_file and uploads_file.is_file():
            return uploads_candidate

    uploads_file = _uploads_file_for_path(clean)
    if uploads_file and uploads_file.is_file():
        return clean

    return clean


def make_absolute_media_url(path: str | None) -> str:
    clean = normalize_media_path(path)
    if not clean:
        return ""
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean

    base = settings.api_base_url.rstrip("/")
    if clean.startswith("/"):
        return f"{base}{clean}"
    return f"{base}/{clean}"


def resolve_media_file(path: str | None) -> Path | None:
    clean = normalize_media_path(path)
    uploads_file = _uploads_file_for_path(clean)
    if uploads_file and uploads_file.is_file():
        return uploads_file
    return None
