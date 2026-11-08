// mockRecommendations.js
// Mock data matching Part 4's recommendation shape exactly:
// { property_id, match_score, reason_text }
//
// Keyed by the *source* property id (the one being viewed), with an
// array of recommended properties. Used for "Similar Properties" on
// PropertyDetail.jsx: mockRecommendations[currentPropertyId]

const mockRecommendations = {
  1: [
    { property_id: 5, match_score: 91, reason_text: "Similar 3BHK layout and price range in a comparable neighborhood." },
    { property_id: 9, match_score: 86, reason_text: "Matches your budget with similar amenities and gated community access." },
    { property_id: 2, match_score: 78, reason_text: "Nearby location with slightly smaller area but strong connectivity." },
  ],
  2: [
    { property_id: 12, match_score: 84, reason_text: "Similar 2BHK size and price, slightly quieter locality." },
    { property_id: 6, match_score: 80, reason_text: "Comparable price point with easy access to tech corridors." },
    { property_id: 8, match_score: 72, reason_text: "More affordable 2BHK option with similar amenities." },
  ],
  3: [
    { property_id: 7, match_score: 88, reason_text: "Another premium listing with top-tier amenities and high trust score." },
    { property_id: 11, match_score: 75, reason_text: "Independent house option for buyers wanting more space and privacy." },
  ],
  5: [
    { property_id: 1, match_score: 89, reason_text: "Very similar price and BHK configuration in a nearby locality." },
    { property_id: 9, match_score: 83, reason_text: "Comparable value pick with strong price and location scores." },
  ],
  7: [
    { property_id: 3, match_score: 90, reason_text: "Similarly premium property with excellent amenity score." },
    { property_id: 11, match_score: 70, reason_text: "Alternative for buyers seeking a spacious independent house." },
  ],
  9: [
    { property_id: 1, match_score: 85, reason_text: "Similar 3BHK configuration with strong overall analysis score." },
    { property_id: 5, match_score: 82, reason_text: "Comparable pricing and community amenities." },
  ],
};

export default mockRecommendations;