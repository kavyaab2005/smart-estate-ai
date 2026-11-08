from app.database import SessionLocal
from app.models.property import Property
from app.models.common import Amenity, PropertyAmenity, DocumentVerification, Document, AnalysisCache
from app.location.location_intel import get_location_intel
from app.recommendation.content_based import build_user_profile, score_property
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

# ---- REAL Part 2 calls (swapped in from mocks) ----

from ml.price_predictor import predictor
from ml.fraud_scorer import fraud_scorer

CACHE_TTL_HOURS = 24


def get_property_amenity_names(db, property_obj: Property):
    rows = (
        db.query(Amenity.name)
        .join(PropertyAmenity, PropertyAmenity.amenity_id == Amenity.id)
        .filter(PropertyAmenity.property_id == property_obj.id)
        .all()
    )
    return [r[0] for r in rows]


def real_predict_price(db, property_obj: Property):
    """Calls Part 2's real price prediction model directly."""
    if not property_obj.price:
        return None
    try:
        amenities = get_property_amenity_names(db, property_obj)
        result = predictor.predict(
            property_type=property_obj.property_type or "apartment",
            listing_type=property_obj.listing_type.value if property_obj.listing_type else "buy",
            area_sqft=float(property_obj.area_sqft) if property_obj.area_sqft else 0,
            bhk=property_obj.bhk or 0,
            bedrooms=property_obj.bhk or 0,
            floor=property_obj.floor or 0,
            total_floors=property_obj.total_floors or 0,
            property_age_years=property_obj.property_age_years or 0,
            furnishing=property_obj.furnishing or "unfurnished",
            parking=1 if property_obj.parking else 0,
            city=property_obj.city or "",
            amenities=amenities,
        )
        return {
            "predicted_price": result["predicted_price"] if isinstance(result, dict) else result.predicted_price,
            "difference_percent": result["difference_percent"] if isinstance(result, dict) else result.difference_percent,
        }
    except Exception as e:
        print(f"Warning: real price prediction failed, skipping: {e}")
        return None


def real_fraud_score(db, property_obj: Property):
    """Calls Part 2's real fraud scoring model directly."""
    try:
        amenities = get_property_amenity_names(db, property_obj)
        result = fraud_scorer.score(
            property_type=property_obj.property_type or "apartment",
            listing_type=property_obj.listing_type.value if property_obj.listing_type else "buy",
            price=float(property_obj.price) if property_obj.price else 0,
            area_sqft=float(property_obj.area_sqft) if property_obj.area_sqft else 0,
            bhk=property_obj.bhk or 0,
            bedrooms=property_obj.bhk or 0,
            floor=property_obj.floor or 0,
            total_floors=property_obj.total_floors or 0,
            property_age_years=property_obj.property_age_years or 0,
            furnishing=property_obj.furnishing or "unfurnished",
            parking=1 if property_obj.parking else 0,
            city=property_obj.city or "",
            amenities=amenities,
        )
        return {
            "trust_score": result["trust_score"] if isinstance(result, dict) else result.trust_score,
            "risk_level": result["risk_level"] if isinstance(result, dict) else result.risk_level,
        }
    except Exception as e:
        print(f"Warning: real fraud scoring failed, using fallback: {e}")
        return {"trust_score": 50, "risk_level": "unknown"}


def get_document_score(db, property_id):
    """Uses REAL data if a document verification exists for this property (Part 3's table), else None."""
    doc = db.query(Document).filter(Document.property_id == property_id).first()
    if not doc:
        return None

    verification = db.query(DocumentVerification).filter(
        DocumentVerification.document_id == doc.id
    ).order_by(DocumentVerification.created_at.desc()).first()

    if not verification:
        return None

    if verification.status.value == "verified":
        return 100
    elif verification.status.value == "mismatch":
        return 30
    else:
        return 50  # pending


# ---- This part's own scoring logic ----

def get_amenity_score(db, property_obj: Property):
    count = db.query(PropertyAmenity).filter(PropertyAmenity.property_id == property_obj.id).count()
    total_amenities = db.query(Amenity).count()
    if total_amenities == 0:
        return 0
    return round(min(count / total_amenities, 1.0) * 100)


def get_price_score(price_prediction, db=None, property_obj=None):
    """
    Score based on how close listed price is to predicted market price.
    If price_prediction is not available, fall back to comparing price per sqft
    against the average price per sqft of other properties in the same city.
    """
    if price_prediction:
        diff = abs(price_prediction["difference_percent"])
        if diff <= 5:
            return 100
        elif diff <= 10:
            return 80
        elif diff <= 15:
            return 60
        elif diff <= 20:
            return 50
        elif diff <= 30:
            return 40
        else:
            return 20

    # Fallback: compare price per sqft with city average
    if property_obj and property_obj.price and property_obj.area_sqft and property_obj.city:
        try:
            db = db or SessionLocal()
            # Find average price per sqft in the same city (approved properties only)
            from app.models.property import Property, PropertyStatusEnum
            avg_price_per_sqft = db.query(
                func.avg(Property.price / Property.area_sqft)
            ).filter(
                Property.city == property_obj.city,
                Property.status == PropertyStatusEnum.approved,
                Property.area_sqft > 0,
                Property.price.isnot(None)
            ).scalar()

            if avg_price_per_sqft:
                listed_ppsf = float(property_obj.price) / float(property_obj.area_sqft)
                diff_pct = abs(listed_ppsf - float(avg_price_per_sqft)) / float(avg_price_per_sqft) * 100

                if diff_pct <= 5:
                    return 100
                elif diff_pct <= 10:
                    return 80
                elif diff_pct <= 15:
                    return 60
                elif diff_pct <= 20:
                    return 50
                elif diff_pct <= 30:
                    return 40
                else:
                    return 20
        except Exception as e:
            print(f"Warning: fallback price score failed: {e}")

    return None


def get_market_price_score(db, property_obj: Property):
    """
    Market score based on how the property's price per sqft compares to
    the average in the same locality/neighborhood (address similarity) or city.
    Higher score = better value (lower price per sqft than average).
    """
    if not property_obj.price or not property_obj.area_sqft or not property_obj.city:
        return None

    try:
        # Find average price per sqft in the same city
        from app.models.property import Property, PropertyStatusEnum

        avg_ppsf = db.query(
            func.avg(Property.price / Property.area_sqft)
        ).filter(
            Property.city == property_obj.city,
            Property.status == PropertyStatusEnum.approved,
            Property.area_sqft > 0,
            Property.price.isnot(None)
        ).scalar()

        if not avg_ppsf:
            return None

        listed_ppsf = float(property_obj.price) / float(property_obj.area_sqft)
        avg_ppsf = float(avg_ppsf)

        # Score: 100 if listed price is 20% below average, 0 if 20% above
        diff_pct = (avg_ppsf - listed_ppsf) / avg_ppsf * 100

        if diff_pct >= 20:
            return 100
        elif diff_pct >= 10:
            return 80
        elif diff_pct >= 0:
            return 60
        elif diff_pct >= -10:
            return 50
        elif diff_pct >= -20:
            return 40
        elif diff_pct >= -30:
            return 30
        else:
            return 20

    except Exception as e:
        print(f"Warning: market price score failed: {e}")
        return None


def get_requirement_match_score(db, user_id, property_obj: Property):
    """Reuses the content-based recommender's scoring for this specific user + property."""
    if not user_id:
        return None
    profile = build_user_profile(db, user_id)
    score, _ = score_property(profile, property_obj)
    return score


def generate_recommendation_text(overall_score, fraud_score_data, price_score):
    if fraud_score_data["risk_level"] == "high":
        return "Exercise caution: this listing shows signs of potential risk. Verify documents carefully before proceeding."
    if overall_score >= 80:
        return "This is a strong listing overall — good value, location, and trust indicators."
    elif overall_score >= 60:
        return "This is a reasonably solid listing, though a few factors could be better."
    else:
        return "This listing has some notable gaps — review the individual scores before deciding."


def get_cached_analysis(db: Session, property_id: str):
    cache = db.query(AnalysisCache).filter(AnalysisCache.property_id == property_id).first()
    if not cache:
        return None
    if datetime.utcnow() - cache.updated_at > timedelta(hours=24):
        return None
    return cache.analysis_json


def save_analysis_cache(db: Session, property_id: str, analysis_data: dict):
    cache = db.query(AnalysisCache).filter(AnalysisCache.property_id == property_id).first()
    if cache:
        cache.analysis_json = analysis_data
        cache.updated_at = datetime.utcnow()
    else:
        cache = AnalysisCache(property_id=property_id, analysis_json=analysis_data)
        db.add(cache)
    db.commit()


def get_property_amenity_names(db, property_obj: Property):
    rows = (
        db.query(Amenity.name)
        .join(PropertyAmenity, PropertyAmenity.amenity_id == Amenity.id)
        .filter(PropertyAmenity.property_id == property_obj.id)
        .all()
    )
    return [r[0] for r in rows]


def analyze_property(property_id: str, user_id: str = None):
    db = SessionLocal()
    try:
        # Check cache first
        cached = get_cached_analysis(db, property_id)
        if cached:
            return {**cached, "from_cache": True}

        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            return {"error": "Property not found"}

        # Real Part 2 calls
        price_prediction = real_predict_price(db, prop)
        fraud_data = real_fraud_score(db, prop)

        # Real DB-backed Part 3 check
        document_score = get_document_score(db, property_id)

        # This part's own logic - use SAME cached location result as Location tab
        location_score = 0
        location_data_source = "unavailable"
        if prop.latitude and prop.longitude:
            try:
                # Use the SAME function as Location tab - passes db session and property_id
                location_result = get_location_intel(db, float(prop.latitude), float(prop.longitude), str(property_id), city=prop.city)
                location_score = location_result["location_score"] if location_result else 0
                location_data_source = location_result.get("data_source", "unavailable")
            except Exception as e:
                print(f"Location intelligence failed for property {property_id}: {e}")
                location_score = 0
                location_data_source = "unavailable"

        amenity_score = get_amenity_score(db, prop)
        price_score = get_price_score(price_prediction, db=db, property_obj=prop)
        market_price_score = get_market_price_score(db, prop)  # NEW: separate calculation
        fraud_score = fraud_data["trust_score"]
        requirement_match_score = get_requirement_match_score(db, user_id, prop)

        # Documented weighting (used for overall_score)
        weights = {
            "price_score": 0.20,
            "location_score": 0.20,
            "amenity_score": 0.10,
            "market_price_score": 0.15,
            "document_score": 0.15,
            "fraud_score": 0.15,
            "requirement_match_score": 0.05,
        }

        scores = {
            "price_score": price_score,
            "location_score": location_score,
            "amenity_score": amenity_score,
            "market_price_score": market_price_score,
            "document_score": document_score,
            "fraud_score": fraud_score,
            "requirement_match_score": requirement_match_score,
        }

        # Only average the weights of scores that actually exist (skip None values, e.g. no docs yet)
        total_weight = sum(weights[k] for k, v in scores.items() if v is not None)
        weighted_sum = sum(weights[k] * v for k, v in scores.items() if v is not None)
        overall_score = round(weighted_sum / total_weight) if total_weight > 0 else 0

        recommendation_text = generate_recommendation_text(overall_score, fraud_data, price_score)

        result = {
            "price_score": price_score,
            "location_score": location_score,
            "amenity_score": amenity_score,
            "market_price_score": market_price_score,
            "document_score": document_score,
            "fraud_score": fraud_score,
            "requirement_match_score": requirement_match_score,
            "overall_score": overall_score,
            "recommendation_text": recommendation_text,
        }

        # Only save to cache if location data was available (not unavailable)
        location_result = None
        if prop.latitude and prop.longitude:
            try:
                location_result = get_location_intel(db, float(prop.latitude), float(prop.longitude), str(property_id), city=prop.city)
            except:
                pass

        if location_result and location_result.get("data_source") != "unavailable":
            save_analysis_cache(db, str(prop.id), result)

        return {**result, "from_cache": False}
    finally:
        db.close()


def generate_recommendation_text(overall_score, fraud_score_data, price_score):
    if fraud_score_data["risk_level"] == "high":
        return "Exercise caution: this listing shows signs of potential risk. Verify documents carefully before proceeding."
    if overall_score >= 80:
        return "This is a strong listing overall — good value, location, and trust indicators."
    elif overall_score >= 60:
        return "This is a reasonably solid listing, though a few factors could be better."
    else:
        return "This listing has some notable gaps — review the individual scores before deciding."


if __name__ == "__main__":
    db = SessionLocal()
    try:
        test_prop = db.query(Property).first()
        if test_prop:
            print(f"Testing with property: {test_prop.title}")
            result = analyze_property(str(test_prop.id))
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print("No properties found in DB")
    finally:
        db.close()