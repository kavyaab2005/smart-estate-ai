import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  ShieldCheck,
  TrendingUp,
  Building2,
  MapPin,
  Clock,
} from "lucide-react";
import client from "../api/client";

function Landing() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function fetchStats() {
      try {
        const res = await client.get("/properties");
        const list = Array.isArray(res.data)
          ? res.data
          : res.data?.properties || [];

        if (!isMounted) return;

        if (list.length > 0) {
          // Compute distinct cities & neighborhood areas client-side
          const areaSet = new Set();
          list.forEach((p) => {
            if (p.city && typeof p.city === "string" && p.city.trim()) {
              areaSet.add(p.city.trim());
            }
            if (p.address && typeof p.address === "string") {
              const segments = p.address
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean);
              if (segments.length >= 2) {
                areaSet.add(segments[segments.length - 2]);
              }
            }
          });

          // Compute recently added/updated listings (within last 30 days)
          const now = Date.now();
          const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
          const recentCount = list.filter((p) => {
            const dateVal = p.updated_at || p.created_at;
            if (!dateVal) return false;
            const t = new Date(dateVal).getTime();
            return !isNaN(t) && now - t <= thirtyDaysMs;
          }).length;

          setStats({
            total:
              typeof res.data?.total === "number"
                ? res.data.total
                : list.length,
            areasCount: areaSet.size > 0 ? areaSet.size : 1,
            recentCount: recentCount > 0 ? recentCount : null,
          });
        } else {
          setStats(null);
        }
      } catch {
        // Fail silently: omit the bar if the backend is offline
        if (isMounted) {
          setStats(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchStats();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="animate-fade-in-up">
      {/* Hero Section */}
      <div className="bg-ink rounded-b-2xl md:rounded-2xl md:mx-6 md:mt-6 px-6 py-16 md:py-24 text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-44 h-44 rounded-full bg-clay/10"></div>
        <div className="relative max-w-2xl mx-auto">
          <h1 className="font-serif text-3xl md:text-4xl font-semibold text-white mb-3">
            Find your next home in Bengaluru
          </h1>
          <p className="text-line text-base md:text-lg mb-8">
            AI-matched listings, verified documents, real prices.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link
              to="/search"
              className="inline-block bg-clay hover:bg-clay-dark text-ink font-semibold px-6 py-3 rounded-lg transition-colors"
            >
              Start searching
            </Link>
            <Link
              to="/chat"
              className="inline-block bg-transparent border border-white/30 hover:border-white text-white font-semibold px-6 py-3 rounded-lg transition-colors"
            >
              Ask the AI assistant
            </Link>
          </div>
        </div>
      </div>

      {/* Live Stat Bar (directly below hero section) */}
      {(loading || stats) && (
        <div className="max-w-4xl mx-auto px-6 -mt-6 md:-mt-8 relative z-10">
          <div className="bg-white border border-line rounded-xl p-4 md:p-6 shadow-sm">
            <div
              className={`grid gap-4 md:gap-6 text-center ${
                loading
                  ? "grid-cols-2 md:grid-cols-3"
                  : stats?.recentCount
                  ? "grid-cols-2 md:grid-cols-3"
                  : "grid-cols-2"
              }`}
            >
              {/* Stat 1: Total Properties */}
              <div className="flex flex-col items-center justify-center p-2">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 rounded-md bg-clay/15 flex items-center justify-center text-clay-dark">
                    <Building2 size={16} />
                  </div>
                  {loading ? (
                    <div className="h-7 w-12 bg-line/60 rounded animate-pulse"></div>
                  ) : (
                    <span className="font-serif text-2xl md:text-3xl font-semibold text-ink">
                      {stats ? stats.total : "—"}
                    </span>
                  )}
                </div>
                <span className="text-sage text-xs md:text-sm font-medium">
                  Properties Listed
                </span>
              </div>

              {/* Stat 2: Cities & Areas */}
              <div className="flex flex-col items-center justify-center p-2 border-l border-line">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-7 h-7 rounded-md bg-ai/10 flex items-center justify-center text-ai">
                    <MapPin size={16} />
                  </div>
                  {loading ? (
                    <div className="h-7 w-12 bg-line/60 rounded animate-pulse"></div>
                  ) : (
                    <span className="font-serif text-2xl md:text-3xl font-semibold text-ink">
                      {stats ? stats.areasCount : "—"}
                    </span>
                  )}
                </div>
                <span className="text-sage text-xs md:text-sm font-medium">
                  Cities & Areas
                </span>
              </div>

              {/* Stat 3: Recently Added / Updated (optional based on availability) */}
              {(loading || stats?.recentCount) && (
                <div className="flex flex-col items-center justify-center p-2 col-span-2 md:col-span-1 border-t md:border-t-0 md:border-l border-line">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-7 h-7 rounded-md bg-success/10 flex items-center justify-center text-success">
                      <Clock size={16} />
                    </div>
                    {loading ? (
                      <div className="h-7 w-12 bg-line/60 rounded animate-pulse"></div>
                    ) : (
                      <span className="font-serif text-2xl md:text-3xl font-semibold text-ink">
                        {stats?.recentCount ?? "—"}
                      </span>
                    )}
                  </div>
                  <span className="text-sage text-xs md:text-sm font-medium">
                    Added Recently
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Feature Highlights */}
      <div className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h2 className="font-serif text-2xl font-semibold text-ink mb-2">
          Why SmartEstate AI
        </h2>
        <p className="text-sage text-sm mb-10">
          Built for how people actually search for homes
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="bg-white border border-line rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-ai/10 flex items-center justify-center mb-3">
              <Search size={18} className="text-ai" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1">
              AI-matched search
            </h3>
            <p className="text-sage text-xs">
              Describe what you want in plain language, get real matching listings back.
            </p>
          </div>

          <div className="bg-white border border-line rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center mb-3">
              <ShieldCheck size={18} className="text-success" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1">
              Verified documents
            </h3>
            <p className="text-sage text-xs">
              Every listing's paperwork is checked before it reaches you.
            </p>
          </div>

          <div className="bg-white border border-line rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-alert/10 flex items-center justify-center mb-3">
              <TrendingUp size={18} className="text-alert" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1">
              Fair price insight
            </h3>
            <p className="text-sage text-xs">
              See how a price compares to similar homes nearby before you decide.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;