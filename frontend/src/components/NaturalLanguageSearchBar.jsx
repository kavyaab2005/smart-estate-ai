import { useState } from "react";
import { Search } from "lucide-react";

/**
 * Free-text search bar. Parses simple patterns out of natural language
 * (city names, "Nbhk"/"N bedroom", "under X crore/lakh") and filters
 * the properties list client-side. This mimics the parsing step Part 4's
 * real NL-search endpoint will eventually do server-side — the parsing
 * function below is the one piece to swap out later.
 *
 * Props:
 *  - properties: full array of properties to search over
 *  - onResults: called with the filtered array whenever a search runs
 */
export default function NaturalLanguageSearchBar({ properties, onResults }) {
  const [query, setQuery] = useState("");

  function parseAndSearch(text) {
    const q = text.toLowerCase().trim();

    if (!q) {
      onResults(properties);
      return;
    }

    let results = properties;

    // BHK: "3bhk", "3 bhk", "3 bedroom"
    const bhkMatch = q.match(/(\d)\s*(bhk|bedroom)/);
    if (bhkMatch) {
      const bhk = Number(bhkMatch[1]);
      results = results.filter((p) => p.bhk === bhk);
    }

    // Price ceiling: "under 1 crore", "under 50 lakh(s)"
    const croreMatch = q.match(/under\s+([\d.]+)\s*crore/);
    const lakhMatch = q.match(/under\s+([\d.]+)\s*lakh/);
    if (croreMatch) {
      const maxPrice = parseFloat(croreMatch[1]) * 10000000;
      results = results.filter((p) => p.price <= maxPrice);
    } else if (lakhMatch) {
      const maxPrice = parseFloat(lakhMatch[1]) * 100000;
      results = results.filter((p) => p.price <= maxPrice);
    }

    // City: match against any city present in the dataset
    const knownCities = [...new Set(properties.map((p) => p.city.toLowerCase()))];
    const matchedCity = knownCities.find((c) => q.includes(c));
    if (matchedCity) {
      results = results.filter((p) => p.city.toLowerCase() === matchedCity);
    }

    // Locality/address fallback: if nothing structured matched at all,
    // fall back to a plain substring search across title + address.
    const nothingMatched = !bhkMatch && !croreMatch && !lakhMatch && !matchedCity;
    if (nothingMatched) {
      results = properties.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.address.toLowerCase().includes(q)
      );
    }

    onResults(results);
  }

  function handleSubmit(e) {
    e.preventDefault();
    parseAndSearch(query);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full gap-2">
      <div className="relative flex-1">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <label htmlFor="nl-search-input" className="sr-only">
          Search properties
        </label>
        <input
          id="nl-search-input"
          name="search"
          type="text"
          autoComplete="off"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Try '3BHK under 1 crore in Koramangala'"
          className="w-full border border-gray-300 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <button
        type="submit"
        className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
      >
        Search
      </button>
    </form>
  );
}