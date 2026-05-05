# will try to implement this so admin can manage banners
# but for now no time  will do later corapted codes are in all my github project folder 
# D:\All github project\fasttest01

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models
from ..media_paths import make_absolute_media_url, normalize_media_path, resolve_media_file

router = APIRouter(prefix="/banners", tags=["Banners"])


@router.get("/", response_model=List[dict])
def get_active_banners(db: Session = Depends(get_db)):
    """Return all active banners ordered by position, with absolute image URLs."""
    banners = (
        db.query(models.Banner)
        .filter(models.Banner.is_active == True)
        .order_by(models.Banner.position)
        .all()
    )
    result = []
    for b in banners:
        normalized_path = normalize_media_path(b.image_url)
        image_url = make_absolute_media_url(normalized_path)
        # Avoid returning guaranteed-404 local URLs when the file is missing in deployment.
        if normalized_path and not normalized_path.startswith(("http://", "https://")):
            if resolve_media_file(normalized_path) is None:
                image_url = ""

        result.append({
            "id": b.id,
            "title": b.title,
            "subtitle": b.subtitle,
            "description": b.description,
            "image_url": image_url,
            "link_url": b.link_url,
            "banner_type": b.banner_type,
            "position": b.position,
            "is_active": b.is_active,
            "button_text": b.button_text,
            "button_link": b.button_link,
            "background_color": b.background_color,
            "text_color": b.text_color,
        })
    return result
