from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.common import Favorite, PropertyImage
from app.models.property import Property
from app.schemas.property import FavoriteCreate, PropertyResponse
from app.core.deps import get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("")
def add_favorite(
    payload: FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == payload.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.property_id == payload.property_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Property already in favorites")

    new_favorite = Favorite(user_id=current_user.id, property_id=payload.property_id)
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    return {"message": "Added to favorites", "id": str(new_favorite.id)}


@router.get("")
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorites = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
    property_map = {f.property_id: f.id for f in favorites}
    property_ids = list(property_map.keys())
    properties = db.query(Property).filter(Property.id.in_(property_ids)).all()

    images = db.query(PropertyImage).filter(PropertyImage.property_id.in_(property_ids)).all()
    images_by_property = {}
    for img in images:
        images_by_property.setdefault(img.property_id, []).append(img.image_url)

    results = []
    for p in properties:
        item = PropertyResponse.model_validate(p).model_dump()
        item["images"] = images_by_property.get(p.id, [])
        item["favorite_id"] = str(property_map[p.id])
        results.append(item)

    return {"properties": results}


@router.delete("/{favorite_id}")
def remove_favorite(
    favorite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorite = db.query(Favorite).filter(
        Favorite.id == favorite_id,
        Favorite.user_id == current_user.id,
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()
    return {"message": "Removed from favorites"}