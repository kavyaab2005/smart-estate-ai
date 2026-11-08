from fastapi import HTTPException
from typing import Dict, List
from app.database import SessionLocal
from app.models.common import ForecastCache
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

CACHE_TTL_HOURS = 24


def get_cached_forecast(db: Session, property_id: str, city: str, years: int):
    cache = db.query(ForecastCache).filter(
        ForecastCache.property_id == property_id,
        ForecastCache.city == city,
        ForecastCache.years == years
    ).first()
    if not cache:
        return None
    if datetime.utcnow() - cache.updated_at > timedelta(hours=24):
        return None
    return cache.forecast_json


def save_forecast_cache(db: Session, property_id: str, city: str, years: int, forecast_data: dict):
    cache = db.query(ForecastCache).filter(
        ForecastCache.property_id == property_id,
        ForecastCache.city == city,
        ForecastCache.years == years
    ).first()
    if cache:
        cache.forecast_json = forecast_data
        cache.updated_at = datetime.utcnow()
    else:
        cache = ForecastCache(
            property_id=property_id,
            city=city,
            years=years,
            forecast_json=forecast_data
        )
        db.add(cache)
    db.commit()


def forecast_property_value(current_price: float, city: str, years: int = 5, property_id: str = None) -> Dict:
    if current_price <= 0:
        raise HTTPException(status_code=422, detail="current_price must be greater than 0")

    # Check cache if property_id is provided
    db = SessionLocal()
    try:
        if property_id:
            cached = get_cached_forecast(db, property_id, city, years)
            if cached:
                return {**cached, "from_cache": True}

        annual_growth_rates = {
            "mumbai": 0.075,
            "delhi": 0.068,
            "bangalore": 0.082,
            "bengaluru": 0.082,
            "new york": 0.055,
            "san francisco": 0.060,
            "default": 0.060
        }

        rate = annual_growth_rates.get(city.lower(), annual_growth_rates["default"])
        yearly_projections = []

        running_price = current_price
        for year in range(1, years + 1):
            running_price = running_price * (1 + rate)
            yearly_projections.append({
                "year": year,
                "projected_price": round(running_price, 2),
                "estimated_roi_percent": round(((running_price - current_price) / current_price) * 100, 2)
            })

        result = {
            "current_price": current_price,
            "city": city,
            "assumed_annual_growth_rate": f"{rate * 100:.1f}%",
            "price_after_5_years": round(running_price, 2),
            "total_expected_appreciation": round(running_price - current_price, 2),
            "projections": yearly_projections
        }

        # Save to cache if property_id provided
        if property_id:
            save_forecast_cache(db, property_id, city, years, result)

        return {**result, "from_cache": False}
    finally:
        db.close()


if __name__ == "__main__":
    result = forecast_property_value(10000000, "Bangalore")
    print(result)