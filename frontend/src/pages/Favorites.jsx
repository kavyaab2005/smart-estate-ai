import { useState, useEffect } from "react";
import PropertyCard from "../components/PropertyCard";
import client from "../api/client";

export default function Favorites() {
  const [properties, setProperties] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadFavorites() {
      try {
        const res = await client.get("/favorites");
        setProperties(res.data.properties);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }
    loadFavorites();
  }, []);

  async function handleRemove(propertyId, favoriteId) {
    try {
      await client.delete(`/favorites/${favoriteId}`);
      setProperties((prev) => prev.filter((p) => p.id !== propertyId));
    } catch (err) {
      console.error("Failed to remove favorite", err);
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-500">
        Loading your saved properties...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-600">
        Couldn't load your favorites. Please try again.
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 animate-fade-in-up">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Properties</h1>

      {properties.length === 0 ? (
        <div className="text-center text-gray-500 py-12 border border-gray-200 rounded-xl">
          You haven't saved any properties yet. Browse listings and tap the
          heart icon to save one here.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {properties.map((property) => (
            <div key={property.id} className="space-y-2">
              <PropertyCard property={property} />
              <button
                onClick={() => handleRemove(property.id, property.favorite_id)}
                className="w-full text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Remove from Favorites
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}