import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import { createMapMarkerIcon } from "../components/MapMarker";
import PropertyCard from "../components/PropertyCard";
import client from "../api/client";
import { Navigation, MapPin, Target, RefreshCw, ExternalLink, ArrowUpDown } from "lucide-react";

const haversineDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

const getGoogleMapsUrl = (origin, destination) => {
  const originStr = origin ? `${origin.lat},${origin.lng}` : "";
  return `https://www.google.com/maps/dir/?api=1&origin=${originStr}&destination=${destination.lat},${destination.lng}&travelmode=driving`;
};

function FlyToSelected({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.flyTo(position, 15);
    }
  }, [map, position]);
  return null;
}

export default function MapView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedId = searchParams.get("selected");
  const selectedMarkerRef = useRef(null);

  const [properties, setProperties] = useState([]);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [sortByDistance, setSortByDistance] = useState(false);
  const [showUserMarker, setShowUserMarker] = useState(true);

  const loadProperties = useCallback(async () => {
    try {
      const res = await client.get("/properties");
      const withCoords = res.data.properties.filter(
        (p) =>
          p.latitude != null &&
          p.longitude != null &&
          p.status !== "rejected"
      );
      setProperties(withCoords);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  useEffect(() => {
    if (!selectedId || properties.length === 0) return;
    const found = properties.find((p) => String(p.id) === String(selectedId));
    if (found && found.latitude != null && found.longitude != null) {
      setSelectedProperty(found);
    }
  }, [selectedId, properties]);

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported by your browser");
      return;
    }

    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const loc = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        setUserLocation(loc);
        setLocationError(null);
      },
      (err) => {
        let message = "Unable to retrieve your location";
        if (err.code === err.PERMISSION_DENIED) {
          message = "Location permission denied. Please enable location access in your browser settings to see distances.";
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          message = "Location information is unavailable";
        } else if (err.code === err.TIMEOUT) {
          message = "Location request timed out";
        }
        setLocationError(message);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  useEffect(() => {
    getCurrentLocation();
  }, []);

  useEffect(() => {
    if (selectedProperty && selectedMarkerRef.current) {
      selectedMarkerRef.current.openPopup();
    }
  }, [selectedProperty]);

  const propertiesWithDistance = properties.map((p) => {
    if (userLocation && p.latitude && p.longitude) {
      const distance = haversineDistance(
        userLocation.lat,
        userLocation.lng,
        p.latitude,
        p.longitude
      );
      return { ...p, distance };
    }
    return { ...p, distance: null };
  });

  const sortedProperties = sortByDistance && userLocation
    ? [...propertiesWithDistance].sort((a, b) => {
        if (a.distance === null) return 1;
        if (b.distance === null) return -1;
        return a.distance - b.distance;
      })
    : propertiesWithDistance;

  const avgLat = properties.reduce((sum, p) => sum + (p.latitude || 0), 0) / properties.length || 0;
  const avgLng = properties.reduce((sum, p) => sum + (p.longitude || 0), 0) / properties.length || 0;

  const mapCenter = userLocation ? [userLocation.lat, userLocation.lng] : [avgLat, avgLng];
  const initialZoom = userLocation ? 13 : 12;

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading map...</div>;
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-600">
        Couldn't load the map. Please try again.
      </div>
    );
  }

  if (properties.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        No properties with location data yet.
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Map View</h1>
        <div className="flex items-center gap-3 flex-wrap">
          {userLocation && (
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={sortByDistance}
                onChange={(e) => setSortByDistance(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="flex items-center gap-1">
                <ArrowUpDown size={14} />
                Sort by distance
              </span>
            </label>
          )}
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={showUserMarker}
              onChange={(e) => setShowUserMarker(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Show my location</span>
          </label>
          <button
            onClick={getCurrentLocation}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} />
            Refresh location
          </button>
        </div>
      </div>

      {locationError && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-3 text-amber-800">
          <MapPin size={20} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{locationError}</p>
            <p className="text-sm text-amber-700 mt-1">
              Distances from your location cannot be shown. Properties will still appear on the map.
            </p>
          </div>
        </div>
      )}

      <div className="h-[500px] w-full rounded-xl overflow-hidden border border-gray-200 relative">
        <MapContainer
          center={mapCenter}
          zoom={initialZoom}
          scrollWheelZoom={true}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {showUserMarker && userLocation && (
            <Marker position={[userLocation.lat, userLocation.lng]} icon={createMapMarkerIcon("user")}>
              <Popup>
                <div className="space-y-1 text-center">
                  <p className="font-semibold text-emerald-600">Your Location</p>
                  <p className="text-sm text-gray-600">
                    Lat: {userLocation.lat.toFixed(6)}, Lng: {userLocation.lng.toFixed(6)}
                  </p>
                </div>
              </Popup>
            </Marker>
          )}
          {sortedProperties.map((property) => (
            <Marker
              key={property.id}
              position={[property.latitude, property.longitude]}
              icon={createMapMarkerIcon(property.status, selectedProperty?.id === property.id)}
              ref={selectedProperty?.id === property.id ? selectedMarkerRef : null}
            >
              <Popup>
                <div className="space-y-2 min-w-[200px]">
                  <p className="font-semibold">{property.title}</p>
                  <p className="text-sm text-gray-600">
                    ₹{(property.price / 100000).toFixed(0)} L · {property.bhk} BHK
                  </p>
                  {property.distance !== null && (
                    <p className="text-sm text-emerald-600 font-medium flex items-center gap-1">
                      <Navigation size={14} />
                      {property.distance.toFixed(1)} km away
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      onClick={() => setSelectedProperty(property)}
                      className="flex-1 text-sm text-blue-600 font-medium underline hover:text-blue-700"
                    >
                      View Details
                    </button>
                    {userLocation && property.latitude && property.longitude && (
                                            <a
                        href={getGoogleMapsUrl(userLocation, { lat: property.latitude, lng: property.longitude })}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-1 px-2 py-1 text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
                        style={{ color: "#ffffff" }}
                      >
                        <ExternalLink size={12} />
                        Directions
                      </a>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
          {userLocation && selectedProperty && (
            <Polyline
              positions={[
                [userLocation.lat, userLocation.lng],
                [selectedProperty.latitude, selectedProperty.longitude],
              ]}
              color="#059669"
              weight={3}
              dashArray="10, 10"
              opacity={0.7}
            />
          )}
          {selectedProperty && selectedProperty.latitude != null && selectedProperty.longitude != null && (
            <FlyToSelected position={[selectedProperty.latitude, selectedProperty.longitude]} />
          )}
        </MapContainer>
      </div>

      {selectedProperty && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">
            Selected Property
          </h3>
          <div className="max-w-sm">
            <PropertyCard
              property={selectedProperty}
              onClick={() => navigate(`/property/${selectedProperty.id}`)}
              userLocation={userLocation}
            />
          </div>
        </div>
      )}
    </div>
  );
}