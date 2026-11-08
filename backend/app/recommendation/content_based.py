from app.database import SessionLocal
from app.models.property import Property
from app.models.common import Favorite, PropertyView, SavedSearch


def build_user_profile(db, user_id):
    """Gather signals from favorites, views, and saved searches to build a preference profile."""
    favorited_ids = [f.property_id for f in db.query(Favorite).filter(Favorite.user_id == user_id).all()]
    viewed_ids = [v.property_id for v in db.query(PropertyView).filter(PropertyView.user_id == user_id).all()]

    signal_ids = list(set(favorited_ids + viewed_ids))
    signal_properties = db.query(Property).filter(Property.id.in_(signal_ids)).all() if signal_ids else []

    saved_searches = db.query(SavedSearch).filter(SavedSearch.user_id == user_id).all()

    cities = [p.city for p in signal_properties if p.city]
    bhks = [p.bhk for p in signal_properties if p.bhk]
    prices = [float(p.price) for p in signal_properties if p.price]
    parking_prefs = [p.parking for p in signal_properties if p.parking is not None]

    for s in saved_searches:
        filters = s.filters_json or {}
        if filters.get("city"):
            cities.append(filters["city"])
        if filters.get("bhk"):
            bhks.append(filters["bhk"])
        if filters.get("max_price"):
            prices.append(filters["max_price"])

    profile = {
        "preferred_city": max(set(cities), key=cities.count) if cities else None,
        "preferred_bhk": max(set(bhks), key=bhks.count) if bhks else None,
        "avg_budget": sum(prices) / len(prices) if prices else None,
        "wants_parking": (sum(parking_prefs) / len(parking_prefs) > 0.5) if parking_prefs else None,
        "seen_property_ids": set(favorited_ids + viewed_ids),
    }
    return profile


def score_property(profile, prop: Property):
    """Weighted content-based score (0-100) + list of reasons that matched."""
    score = 0
    reasons = []

    if profile["preferred_city"] and prop.city == profile["preferred_city"]:
        score += 30
        reasons.append(f"preferred location ({prop.city})")

    if profile["preferred_bhk"] and prop.bhk == profile["preferred_bhk"]:
        score += 25
        reasons.append(f"{prop.bhk}BHK requirement")

    if profile["avg_budget"] and prop.price:
        diff_ratio = abs(float(prop.price) - profile["avg_budget"]) / profile["avg_budget"]
        if diff_ratio <= 0.15:
            score += 25
            reasons.append("budget")
        elif diff_ratio <= 0.30:
            score += 12
            reasons.append("similar budget range")

    if profile["wants_parking"] is not None and prop.parking == profile["wants_parking"] and prop.parking:
        score += 20
        reasons.append("parking preference")

    return min(score, 100), reasons


def generate_reason_text(reasons):
    if not reasons:
        return "Recommended based on general popularity among similar listings."
    if len(reasons) == 1:
        return f"Recommended because this property matches your {reasons[0]}."
    return f"Recommended because this property matches your {', '.join(reasons[:-1])} and {reasons[-1]}."


def get_recommendations(user_id, top_k=10):
    db = SessionLocal()
    try:
        profile = build_user_profile(db, user_id)

        candidates = db.query(Property).filter(
            Property.status == "approved",
            ~Property.id.in_(profile["seen_property_ids"]) if profile["seen_property_ids"] else True,
        ).all()

        scored = []
        for prop in candidates:
            score, reasons = score_property(profile, prop)
            if score > 0:
                scored.append({
                    "property_id": str(prop.id),
                    "match_score": score,
                    "reason_text": generate_reason_text(reasons),
                })

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:top_k]
    finally:
        db.close()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        from app.models.user import User
        test_user = db.query(User).first()
        if test_user:
            print(f"Testing with user: {test_user.id}")
            results = get_recommendations(str(test_user.id))
            for r in results:
                print(r)
        else:
            print("No users found in DB to test with.")
    finally:
        db.close()