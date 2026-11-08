import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  CheckCircle2,
  XCircle,
  Clock,
  MinusCircle,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Info,
} from "lucide-react";
import { computeTrustScore } from "../utils/trustScore";

/**
 * TrustScoreBadge Component
 *
 * Requirements fulfilled:
 * 1. Weighted score calculation from 5 independent verification signals
 * 2. 3-tier visual bucketing (High / Partial / Unverified) with distinct colors & icons
 * 3. Compact card badge with interactive click/hover popover breakdown
 * 4. Explicit distinction between pass, fail, pending, not-applicable, and missing states
 * 5. Prevents navigation propagation to the parent listing card
 * 6. Entry point linking to the full "Verify Documents" tab (/verify-documents)
 * 7. Compliant copy avoiding legal certainty ("Checks Passed", not "100% Verified")
 */
export default function TrustScoreBadge({
  signals,
  score: manualScore,
  propertyId,
  compact = true,
  className = "",
}) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const containerRef = useRef(null);
  const popoverRef = useRef(null);

  // Compute breakdown and score
  const computed = computeTrustScore(signals || {});
  const effectiveScore = typeof manualScore === "number" ? manualScore : computed.score;
  const { tier, tierLabel, checks, disclaimer } = computed;

  // Visual tier styling
  const tierConfig = {
    high: {
      badgeClass:
        "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-200 dark:border-emerald-800",
      iconClass: "text-emerald-600",
      accentBg: "bg-emerald-500",
      Icon: ShieldCheck,
      pillText: "Checks Passed",
    },
    partial: {
      badgeClass:
        "bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-800",
      iconClass: "text-amber-600",
      accentBg: "bg-amber-500",
      Icon: ShieldAlert,
      pillText: "Partial Checks",
    },
    unverified: {
      badgeClass:
        "bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200 dark:bg-slate-800/80 dark:text-slate-300 dark:border-slate-700",
      iconClass: "text-slate-500",
      accentBg: "bg-slate-400",
      Icon: ShieldQuestion,
      pillText: "Needs Verification",
    },
  };

  const currentTier = tierConfig[tier] || tierConfig.unverified;
  const TierIcon = currentTier.Icon;

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const showPopover = isOpen || isHovered;

  const handleBadgeClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    setIsOpen((prev) => !prev);
  };

  const handleDeepDiveClick = (e) => {
    e.stopPropagation();
    e.preventDefault();
    setIsOpen(false);
    navigate(propertyId ? `/verify-documents?propertyId=${propertyId}` : "/verify-documents");
  };

  // State icon & color helper for popover items
  const renderStateIcon = (state) => {
    switch (state) {
      case "pass":
        return <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />;
      case "fail":
        return <XCircle size={16} className="text-red-500 shrink-0" />;
      case "pending":
        return <Clock size={16} className="text-amber-500 shrink-0" />;
      case "not_applicable":
        return <MinusCircle size={16} className="text-slate-400 shrink-0" />;
      case "missing":
      default:
        return <HelpCircle size={16} className="text-gray-400 shrink-0" />;
    }
  };

  return (
    <div
      ref={containerRef}
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Interactive Compact Badge */}
      <button
        type="button"
        onClick={handleBadgeClick}
        title="Click to view verification breakdown"
        aria-expanded={showPopover}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border shadow-xs transition-all cursor-pointer select-none ${currentTier.badgeClass}`}
      >
        <TierIcon size={14} className={currentTier.iconClass} />
        <span className="font-semibold tracking-tight">
          Trust {effectiveScore}
        </span>
        <span className="text-[11px] opacity-80 hidden sm:inline">
          · {currentTier.pillText}
        </span>
      </button>

      {/* Popover Breakdown Modal/Flyout */}
      {showPopover && (
        <div
          ref={popoverRef}
          onClick={(e) => e.stopPropagation()}
          className="absolute z-50 left-0 sm:left-auto sm:right-0 mt-2 w-80 max-w-[90vw] p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-xl animate-fade-in-up text-left text-gray-800 dark:text-gray-100"
          style={{ transformOrigin: "top right" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded-lg ${currentTier.badgeClass}`}>
                <TierIcon size={18} className={currentTier.iconClass} />
              </div>
              <div>
                <div className="text-xs uppercase font-bold tracking-wider text-gray-400 dark:text-gray-400">
                  Trust Score
                </div>
                <div className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                  <span>{effectiveScore}/100</span>
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                    {currentTier.pillText}
                  </span>
                </div>
              </div>
            </div>

            {/* Progress gauge bar */}
            <div className="w-16">
              <div className="h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${currentTier.accentBg}`}
                  style={{ width: `${effectiveScore}%` }}
                />
              </div>
            </div>
          </div>

          {/* Verification Checks List */}
          <div className="py-3 space-y-2.5">
            <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
              5 Independent Signal Checks
            </div>

            {checks.map((chk) => (
              <div
                key={chk.id}
                className="flex items-start gap-2.5 text-xs p-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <div className="mt-0.5">{renderStateIcon(chk.state)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900 dark:text-gray-200">
                      {chk.title}
                    </span>
                    <span
                      className={`text-[11px] font-medium capitalize ${
                        chk.state === "pass"
                          ? "text-emerald-700 dark:text-emerald-400"
                          : chk.state === "fail"
                          ? "text-red-600 dark:text-red-400"
                          : chk.state === "pending"
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-gray-500 dark:text-gray-400"
                      }`}
                    >
                      {chk.label}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-1">
                    {chk.detail}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* State Legend Tip (Explicit distinction per Requirement 4) */}
          <div className="pt-2 pb-1 px-2 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[10px] text-gray-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 size={11} className="text-emerald-600" /> Passed
            </span>
            <span className="flex items-center gap-1">
              <Clock size={11} className="text-amber-500" /> In Review
            </span>
            <span className="flex items-center gap-1">
              <MinusCircle size={11} className="text-slate-400" /> Exempt/NA
            </span>
            <span className="flex items-center gap-1">
              <XCircle size={11} className="text-red-500" /> Issue
            </span>
          </div>

          {/* Compliance Disclaimer (Requirement 7) */}
          <p className="text-[10px] leading-tight text-gray-400 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/60 p-2 rounded-md mt-2 flex gap-1.5 items-start">
            <Info size={13} className="shrink-0 mt-0.5 text-gray-400" />
            <span>{disclaimer}</span>
          </p>

          {/* Entry point into full Verify Documents page (Requirement 6) */}
          <button
            type="button"
            onClick={handleDeepDiveClick}
            className="w-full mt-3 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-colors cursor-pointer shadow-xs"
          >
            <span>Verify Documents Details</span>
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}