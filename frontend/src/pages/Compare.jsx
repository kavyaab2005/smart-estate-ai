import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import ComparisonTable from "../components/ComparisonTable";
import client from "../api/client";

export default function Compare() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const ids = (searchParams.get("ids") || "").split(",").filter(Boolean);

  const [properties, setProperties] = useState([]);
  const [analysisData, setAnalysisData] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadProperties() {
      try {
        const results = await Promise.all(
          ids.map((id) => client.get(`/properties/${id}`))
        );
        const loadedProperties = results.map((res) => res.data.property);
        setProperties(loadedProperties);

        // Fetch analysis data for each property
        const analysisResults = await Promise.allSettled(
          loadedProperties.map((p) => client.get(`/properties/${p.id}/analyze`))
        );
        const analysisMap = {};
        analysisResults.forEach((result, index) => {
          if (result.status === "fulfilled" && result.value.data) {
            analysisMap[loadedProperties[index].id] = result.value.data;
          }
        });
        setAnalysisData(analysisMap);
      } catch (err) {
        console.error("Failed to load properties for comparison", err);
      } finally {
        setIsLoading(false);
      }
    }
    if (ids.length >= 2) loadProperties();
    else setIsLoading(false);
  }, [ids.join(",")]);

  if (isLoading) {
    return <div className="p-6 text-center text-gray-500">Loading comparison...</div>;
  }

  if (properties.length < 2) {
    return (
      <div className="p-6 text-center text-gray-500 border border-gray-200 rounded-xl m-6 space-y-3">
        <p>Select at least 2 properties to compare.</p>
        <button
          onClick={() => navigate("/search")}
          className="text-sm font-medium text-blue-600 hover:text-blue-700 underline"
        >
          Go to Search
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">
          Comparing {properties.length} Properties
        </h2>
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Back to Search
        </button>
      </div>
      <ComparisonTable properties={properties} analysisData={analysisData} />
    </div>
  );
}
