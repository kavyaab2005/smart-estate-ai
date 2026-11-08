import { Crown } from "lucide-react";

/**
 * Side-by-side comparison table for 2+ properties.
 *
 * "Best match" is determined by analysis.overall_score (highest wins).
 * Properties with no analysis data are shown but can't win the crown —
 * there's nothing to rank them on.
 *
 * Props:
 *  - properties: array of property objects (2 or more)
 *  - analysisData: object mapping property ID to analysis data (from /properties/{id}/analyze)
 */
export default function ComparisonTable({ properties, analysisData = {} }) {
  const scores = properties.map((p) => analysisData[p.id]?.overall_score ?? null);
  const bestScore = Math.max(...scores.filter((s) => s !== null), -Infinity);
  const bestIndex =
    bestScore === -Infinity ? -1 : scores.indexOf(bestScore);

  const rows = [
    {
      label: "Price",
      get: (p) => {
        const formatted = new Intl.NumberFormat("en-IN", {
          style: "currency",
          currency: "INR",
          maximumFractionDigits: 0,
        }).format(p.price);
        return p.listing_type === "rent" ? `${formatted}/month` : formatted;
      },
    },
    { label: "Area", get: (p) => `${p.area_sqft} sqft` },
    { label: "BHK", get: (p) => p.bhk },
    { label: "Bathrooms", get: (p) => p.bathrooms },
    { label: "Address", get: (p) => p.address },
    { label: "Status", get: (p) => p.status },
    {
      label: "Overall Score",
      get: (p) => analysisData[p.id]?.overall_score ?? "Not analyzed",
    },
  ];

  return (
    <div className="overflow-x-auto border border-line rounded-xl shadow-sm">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-ink">
            <th className="text-left p-3 font-medium text-line w-32">
              &nbsp;
            </th>
            {properties.map((p, i) => (
              <th key={p.id} className="text-left p-3 min-w-[180px]">
                <div className="flex items-center gap-1.5">
                  {i === bestIndex && (
                    <Crown size={16} className="text-clay" />
                  )}
                  <span className="font-serif font-semibold text-white">
                    {p.title}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-t border-line">
              <td className="p-3 font-medium text-sage bg-panel">{row.label}</td>
              {properties.map((p, i) => (
                <td
                  key={p.id}
                  className={`p-3 capitalize text-ink ${
                    i === bestIndex ? "bg-clay/10 font-semibold" : "bg-white"
                  }`}
                >
                  {row.get(p)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
