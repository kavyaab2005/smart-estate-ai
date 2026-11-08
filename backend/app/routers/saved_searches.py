from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.common import SavedSearch
from app.core.deps import get_current_user

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


class SavedSearchCreate(BaseModel):
    filters_json: dict


@router.post("")
def create_saved_search(
    payload: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_search = SavedSearch(user_id=current_user.id, filters_json=payload.filters_json)
    db.add(new_search)
    db.commit()
    db.refresh(new_search)
    return {"message": "Search saved", "id": str(new_search.id)}


@router.get("")
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    searches = db.query(SavedSearch).filter(SavedSearch.user_id == current_user.id).all()
    return {
        "searches": [
            {"id": str(s.id), "filters_json": s.filters_json, "created_at": s.created_at.isoformat()}
            for s in searches
        ]
    }


@router.delete("/{search_id}")
def delete_saved_search(
    search_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    search = db.query(SavedSearch).filter(
        SavedSearch.id == search_id,
        SavedSearch.user_id == current_user.id,
    ).first()
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")

    db.delete(search)
    db.commit()
    return {"message": "Saved search deleted"}