from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.property import Property, PropertyStatusEnum

router = APIRouter(prefix="/analytics", tags=["Market Analytics"])

@router.get("/market-summary")
def get_market_summary(db: Session = Depends(get_db)):
    total_properties = db.query(Property).count()
    approved_properties = db.query(Property).filter(Property.status == PropertyStatusEnum.approved).count()
    avg_price = db.query(func.avg(Property.price)).scalar() or 0
    avg_price_sqft = db.query(func.avg(Property.price / Property.area_sqft)).filter(Property.area_sqft > 0).scalar() or 0

    return {
        "total_listings": total_properties,
        "active_listings": approved_properties,
        "average_property_price": round(float(avg_price), 2),
        "average_price_per_sqft": round(float(avg_price_sqft), 2)
    }
