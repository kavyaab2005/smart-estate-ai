import { useState, useEffect } from "react";
import { Loader2, AlertCircle, RefreshCw, Heart, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import client from "../api/client";
import PropertyCard from "../components/PropertyCard";

export default function BuyerDashboard() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Get recommendation items (property_id, match_score, reason_text)
      const recRes = await client.get("/recommendations");
      const recItems = recRes.data?.recommendations || [];

      // 2. Fetch full property details for each recommended property
      const propertyPromises = recItems.map((item) =>
        client.get(`/properties/${item.property_id}`).then((res) => ({
          ...res.data?.property,
          images: res.data?.images || [],
          match_score: item.match_score,
          reason_text: item.reason_text,
        }))
      );

      const properties = await Promise.all(propertyPromises);
      setRecommendations(properties.filter(Boolean));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, []);

  if (loading) {
    return (
      <div className="animate-fade-in-up flex flex-col items-center justify-center py-24 px-6">
        <Loader2 className="h-10 w-10 animate-spin text-ai" />
        <p className="mt-4 text-sage">Loading your recommendations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="animate-fade-in-up flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mb-4">
          <AlertCircle size={26} className="text-red-600" />
        </div>
        <h2 className="font-serif text-xl font-semibold text-ink mb-2">
          Couldn't load recommendations
        </h2>
        <p className="text-sage text-sm mb-4">{error}</p>
        <button
          onClick={loadRecommendations}
          className="text-sm font-medium px-4 py-2 bg-ai text-white rounded-lg hover:bg-ai/90 flex items-center gap-2"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  if (!recommendations.length) {
    return (
      <div className="animate-fade-in-up flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="w-14 h-14 rounded-full bg-ai/10 flex items-center justify-center mb-4">
          <Sparkles size={26} className="text-ai" />
        </div>
        <h2 className="font-serif text-xl font-semibold text-ink mb-2">
          No recommendations yet
        </h2>
        <p className="text-sage text-sm mb-4 max-w-xs">
          Save some searches or view properties to get personalized recommendations.
        </p>
        <Link
          to="/search"
          className="text-sm font-medium px-4 py-2 bg-ai text-white rounded-lg hover:bg-ai/90 flex items-center gap-2"
        >
          <Sparkles size={16} /> Explore Properties
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in-up p-6 md:p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-2xl font-semibold text-ink">Recommended for You</h2>
          <p className="text-sage text-sm mt-1">
            Based on your preferences and browsing history
          </p>
        </div>
        <button
          onClick={loadRecommendations}
          className="text-sm text-ai hover:text-ai/80 flex items-center gap-1"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {recommendations.map((property) => (
          <Link key={property.id} to={`/property/${property.id}`}>
            <PropertyCard
              property={property}
              matchScore={property.match_score}
            />
          </Link>
        ))}
      </div>

      {/* Reason preview - could be expanded into a tooltip/modal later */}
      <div className="text-xs text-sage border-t border-line pt-4">
        <p>Match scores reflect how well each property aligns with your saved searches and view history.</p>
      </div>
    </div>
  );
}