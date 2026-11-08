from typing import Dict

def calculate_green_building_score(area_sqft: float, total_floors: int, parking: bool) -> Dict:
    """
    Computes sustainability rating, solar rooftop potential, and eco score.
    """
    roof_area_estimate = (area_sqft / max(total_floors, 1)) if total_floors else area_sqft
    solar_capacity_kw = round(roof_area_estimate * 0.012, 1)  # approx 12W per sqft
    annual_power_generation_kwh = round(solar_capacity_kw * 1400, 0)
    co2_offset_tons = round(annual_power_generation_kwh * 0.0007, 2)

    eco_score = 75
    if parking:
        eco_score += 5  # EV charging potential

    return {
        "sustainability_score": min(eco_score, 100),
        "green_rating": "A+" if eco_score >= 80 else "A",
        "estimated_rooftop_solar_capacity_kw": solar_capacity_kw,
        "estimated_annual_solar_generation_kwh": annual_power_generation_kwh,
        "co2_reduction_tons_per_year": co2_offset_tons
    }
