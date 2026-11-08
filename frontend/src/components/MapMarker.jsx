import L from "leaflet";

/**
 * Leaflet's default marker icon references PNG paths that break under
 * Vite's bundler (a well-known gotcha — markers render broken/missing).
 * This builds a custom marker icon in code instead, so MapView.jsx
 * never touches the broken default.
 *
 * Color reflects property status, matching PropertyCard's status colors.
 */
const statusColors = {
  approved: "#16a34a", // green-600 — "available"
  sold: "#dc2626",     // red-600
  pending: "#ca8a04",  // yellow-600
};

export function createMapMarkerIcon(status, selected = false) {
  const color = selected ? "#2563eb" : (statusColors[status] || "#4b5563"); // blue-600 for selected
  const size = selected ? 36 : 28;
  const height = selected ? 49 : 38;

  const svg = `
    <svg width="${size}" height="${height}" viewBox="0 0 28 38" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 24 14 24s14-13.5 14-24c0-7.7-6.3-14-14-14z" fill="${color}"/>
      <circle cx="14" cy="14" r="6" fill="white"/>
    </svg>
  `;

  return L.divIcon({
    html: svg,
    className: "",
    iconSize: [size, height],
    iconAnchor: [size / 2, height],
    popupAnchor: [0, -height],
  });
}