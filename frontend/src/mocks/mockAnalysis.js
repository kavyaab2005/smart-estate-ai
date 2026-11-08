// mockAnalysis.js
// Mock data matching Part 4's "Analyze This Property" shape exactly:
// { price_score, location_score, amenity_score, market_price_score,
//   document_score, fraud_score, requirement_match_score,
//   overall_score, recommendation_text }
//
// Keyed by property id so pages can do: mockAnalysis[propertyId]

const mockAnalysis = {
  1: {
    price_score: 82,
    location_score: 90,
    amenity_score: 78,
    market_price_score: 85,
    document_score: 95,
    fraud_score: 92,
    requirement_match_score: 88,
    overall_score: 87,
    recommendation_text:
      "Strong buy — priced close to fair market value with excellent location score and clean documentation.",
  },
  2: {
    price_score: 74,
    location_score: 88,
    amenity_score: 60,
    market_price_score: 70,
    document_score: 90,
    fraud_score: 85,
    requirement_match_score: 72,
    overall_score: 76,
    recommendation_text:
      "Good option overall, though slightly above market price for the area — worth a bit of negotiation.",
  },
  3: {
    price_score: 65,
    location_score: 80,
    amenity_score: 95,
    market_price_score: 60,
    document_score: 88,
    fraud_score: 90,
    requirement_match_score: 80,
    overall_score: 79,
    recommendation_text:
      "Premium villa with top-tier amenities, but priced above comparable listings in Whitefield.",
  },
  5: {
    price_score: 78,
    location_score: 85,
    amenity_score: 82,
    market_price_score: 80,
    document_score: 93,
    fraud_score: 91,
    requirement_match_score: 85,
    overall_score: 85,
    recommendation_text:
      "Well-balanced listing — fair pricing, solid amenities, and a low fraud risk profile.",
  },
  7: {
    price_score: 55,
    location_score: 92,
    amenity_score: 98,
    market_price_score: 50,
    document_score: 97,
    fraud_score: 94,
    requirement_match_score: 68,
    overall_score: 76,
    recommendation_text:
      "Excellent luxury property, but significantly overpriced relative to nearby comparables.",
  },
  9: {
    price_score: 88,
    location_score: 75,
    amenity_score: 84,
    market_price_score: 90,
    document_score: 80,
    fraud_score: 82,
    requirement_match_score: 79,
    overall_score: 83,
    recommendation_text:
      "Solid value pick — priced below market average with good community amenities.",
  },
};

export default mockAnalysis;