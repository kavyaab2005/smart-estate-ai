from typing import List, Optional


CITY_PRICE = {
    "Whitefield": 6500, "Koramangala": 9500, "Indiranagar": 11000,
    "HSR Layout": 8500, "Marathahalli": 6000, "Electronic City": 5000,
    "Jayanagar": 10000, "Bannerghatta Road": 5500, "Hebbal": 7500,
    "JP Nagar": 7000, "Yelahanka": 5000, "Sarjapur Road": 6000,
    "Bellandur": 7000, "Banashankari": 8000, "BTM Layout": 7500,
    "Rajajinagar": 8500, "Basavanagudi": 9000, "Malleswaram": 10000,
    "Vijayanagar": 7000, "Hennur": 5500,
}


class FraudScorer:
    def score(self, property_type: str, listing_type: str, price: float,
              area_sqft: float, bhk: int, bedrooms: int, floor: int,
              total_floors: int, property_age_years: int, furnishing: str,
              parking: int, city: str, amenities: List[str],
              is_verified: bool = False) -> dict:

        flags    = []
        reasons  = []
        risk_pts = 0

        # Rule 1: Price vs market rate
        avg_sqft = CITY_PRICE.get(city, 7000)
        expected = avg_sqft * area_sqft
        if listing_type == "sale" and expected > 0:
            ratio = price / expected
            if ratio < 0.50:
                flags.append({"level": "high",
                              "reason": f"Price is {(1-ratio)*100:.0f}% below market rate for {city}"})
                reasons.append("Suspiciously low price — possible scam listing")
                risk_pts += 35
            elif ratio < 0.70:
                flags.append({"level": "medium",
                              "reason": "Price is significantly below market rate"})
                reasons.append("Price is below average — verify with owner before paying")
                risk_pts += 15

        # Rule 2: Floor exceeds total floors
        if floor > total_floors:
            flags.append({"level": "high",
                          "reason": f"Floor ({floor}) exceeds total floors ({total_floors})"})
            reasons.append("Invalid floor data — listing may be fabricated")
            risk_pts += 25

        # Rule 3: Area too small per BHK
        if bhk > 0 and (area_sqft / bhk) < 200:
            flags.append({"level": "medium",
                          "reason": f"Only {area_sqft/bhk:.0f} sqft per BHK — very small"})
            reasons.append("Area per BHK is suspiciously small")
            risk_pts += 15

        # Rule 4: Bedrooms vs BHK mismatch
        if abs(bedrooms - bhk) > 1:
            flags.append({"level": "low",
                          "reason": f"Bedrooms ({bedrooms}) does not match BHK ({bhk})"})
            risk_pts += 5

        # Rule 5: Villa with no parking
        if property_type == "villa" and parking == 0:
            flags.append({"level": "low", "reason": "Villa with zero parking is unusual"})
            risk_pts += 5

        # Owner identity check (based on account verification, not ID number)
        if not is_verified:
            flags.append({"level": "low",
                          "reason": "Listing owner has not verified their account"})
            reasons.append("Owner account is unverified — proceed with extra caution")
            risk_pts += 10

        trust_score = max(0, 100 - risk_pts)
        risk_level  = "low" if trust_score >= 80 else ("medium" if trust_score >= 50 else "high")

        if not reasons:
            reasons.append("No suspicious indicators found. Listing appears genuine.")

        return {
            "trust_score":  trust_score,
            "risk_level":   risk_level,
            "flags":        flags,
            "reasons":      reasons,
            "is_verified": is_verified,
        }


fraud_scorer = FraudScorer()