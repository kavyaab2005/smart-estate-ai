/**
 * Renders the 7-factor "Analyze This Property" breakdown.
 * Matches Part 4's analyze shape exactly:
 * { price_score, location_score, amenity_score, market_price_score,
 *   document_score, fraud_score, requirement_match_score,
 *   overall_score, recommendation_text }
 *
 * Props:
 *  - analysis: the analysis object, or undefined/null if this
 *    property hasn't been analyzed yet (see mockAnalysis.js — not
 *    every property has an entry).
 */

const FACTORS = [
  { key: "price_score", label: "Price" },
  { key: "location_score", label: "Location" },
  { key: "amenity_score", label: "Amenities" },
  { key: "market_price_score", label: "Market Price Fit" },
  { key: "document_score", label: "Document Quality" },
  { key: "fraud_score", label: "Fraud Risk" },
  { key: "requirement_match_score", label: "Requirement Match" },
];

function scoreColor(score) {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
}

export default function AnalysisPanel({ analysis }) {
  if (!analysis) {
    return (
      <div className="p-4 border border-gray-200 rounded-xl bg-gray-50 text-sm text-gray-500">
        This property hasn't been analyzed yet. Check back soon for a full
        AI breakdown.
      </div>
    );
  }

  const { overall_score, recommendation_text } = analysis;

  return (
    <div className="p-4 border border-gray-200 rounded-xl bg-white space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Analyze This Property</h3>
        <span className="text-lg font-bold text-gray-900">
          {overall_score}
          <span className="text-sm font-normal text-gray-500">/100</span>
        </span>
      </div>

      <div className="space-y-2">
        {FACTORS.map(({ key, label }) => {
          const score = analysis[key];
          return (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-600 mb-0.5">
                <span>{label}</span>
                <span>{score}</span>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${scoreColor(score)}`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {recommendation_text && (
        <p className="text-sm text-gray-700 border-t border-gray-100 pt-3">
          {recommendation_text}
        </p>
      )}
    </div>
  );
}