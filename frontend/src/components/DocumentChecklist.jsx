import { CheckCircle2, AlertTriangle } from "lucide-react";

/**
 * Renders match_results as a ✓/⚠ checklist, matching Part 3's
 * document verification shape:
 * { extracted_fields: {...}, match_results: [{field, status}],
 *   overall_status, disclaimer }
 *
 * status is expected to be "match" | "mismatch" (or similar) — we
 * treat anything not explicitly "match" as a mismatch/warning, so an
 * unexpected status string still renders something sensible instead
 * of silently showing nothing.
 *
 * Props:
 *  - matchResults: array of { field, status }
 *  - overallStatus: string, e.g. "verified" | "flagged"
 *  - disclaimer: string
 */
export default function DocumentChecklist({
  matchResults,
  overallStatus,
  disclaimer,
}) {
  const isVerified = overallStatus?.toLowerCase() === "verified";

  return (
    <div className="border border-gray-200 rounded-xl bg-white overflow-hidden">
      <div
        className={`px-4 py-3 flex items-center justify-between ${
          isVerified ? "bg-green-50" : "bg-yellow-50"
        }`}
      >
        <span className="font-semibold text-gray-900">
          Verification Result
        </span>
        <span
          className={`text-sm font-medium capitalize ${
            isVerified ? "text-green-700" : "text-yellow-700"
          }`}
        >
          {overallStatus}
        </span>
      </div>

      <ul className="divide-y divide-gray-100">
        {matchResults.map((item) => {
          const matched = item.status?.toLowerCase() === "match";
          return (
            <li
              key={item.field}
              className="flex items-center gap-2 px-4 py-2.5 text-sm"
            >
              {matched ? (
                <CheckCircle2 size={16} className="text-green-600 shrink-0" />
              ) : (
                <AlertTriangle size={16} className="text-yellow-600 shrink-0" />
              )}
              <span className="text-gray-700 capitalize">
                {item.field.replace(/_/g, " ")}
              </span>
              <span className="ml-auto text-xs text-gray-400 capitalize">
                {item.status}
              </span>
            </li>
          );
        })}
      </ul>

      {disclaimer && (
        <p className="text-xs text-gray-400 px-4 py-3 border-t border-gray-100">
          {disclaimer}
        </p>
      )}
    </div>
  );
}