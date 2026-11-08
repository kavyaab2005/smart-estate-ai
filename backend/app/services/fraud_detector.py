from typing import Dict

def analyze_listing_fraud_risk(title: str, description: str, price: float, area_sqft: float, city: str) -> Dict:
    """
    AI-driven fraud & spam detection for real estate listings.
    """
    risk_score = 0
    flags = []

    price_per_sqft = (price / area_sqft) if area_sqft > 0 else 0

    # Suspiciously cheap threshold
    if price_per_sqft > 0 and price_per_sqft < 500:
        risk_score += 40
        flags.append("Abnormally low price per sq.ft - Potential scam or mislisting.")

    desc_lower = description.lower() if description else ""
    suspicious_keywords = ["wire transfer", "western union", "cash only advance", "no viewing allowed", "urgent deposit"]
    
    for kw in suspicious_keywords:
        if kw in desc_lower:
            risk_score += 30
            flags.append(f"Suspicious phrasing detected: '{kw}'.")

    if not description or len(description) < 20:
        risk_score += 15
        flags.append("Extremely short property description.")

    risk_level = "LOW"
    if risk_score >= 60:
        risk_level = "HIGH"
    elif risk_score >= 30:
        risk_level = "MEDIUM"

    return {
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "is_flagged": risk_score >= 50,
        "flagged_reasons": flags
    }
