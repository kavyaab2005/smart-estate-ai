from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.property import Property
from app.schemas.property import PropertyResponse
from app.core.deps import require_role
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])


class StatusUpdate(BaseModel):
    status: str
@router.get("/properties")
def list_all_properties(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    query = db.query(Property)
    if status:
        query = query.filter(Property.status == status)
    properties = query.order_by(Property.created_at.desc()).all()

    return {
        "properties": [
            PropertyResponse.model_validate(p).model_dump()
            for p in properties
        ]
    }

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    users = db.query(User).all()
    return {
        "users": [
            {
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "role": u.role.value,
                "is_verified": u.is_verified,
            }
            for u in users
        ]
    }


@router.put("/properties/{property_id}/status")
def update_property_status(
    property_id: UUID,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    prop.status = payload.status
    db.commit()
    db.refresh(prop)
    return {"message": "Property status updated", "status": prop.status.value}


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    total_users = db.query(func.count(User.id)).scalar()
    total_properties = db.query(func.count(Property.id)).scalar()

    by_city = dict(
        db.query(Property.city, func.count(Property.id))
        .group_by(Property.city)
        .all()
    )
    by_type = dict(
        db.query(Property.property_type, func.count(Property.id))
        .group_by(Property.property_type)
        .all()
    )

    return {
        "total_users": total_users,
        "total_properties": total_properties,
        "by_city": by_city,
        "by_type": by_type,
    }