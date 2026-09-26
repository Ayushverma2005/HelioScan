"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { searchGeocode, type GeocodingResult } from "@/lib/geocode";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default function GeocodeSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodingResult[]>([]);
  const [selected, setSelected] = useState<GeocodingResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = query.trim();
    if (!trimmed) {
      setError("Please enter an address to search.");
      setResults([]);
      setSelected(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    setSelected(null);

    try {
      const response = await searchGeocode(trimmed);
      setResults(response.results);
      if (response.results.length === 0) {
        setError("No locations found.");
      }
    } catch (err) {
      setResults([]);
      setSelected(null);
      setError(err instanceof Error ? err.message : "An unexpected geocoding error occurred.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="space-y-4 border border-gray-400 p-4">
      <h2 className="text-lg font-semibold">Geocoding Search</h2>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="address-search">
          Address
        </label>
        <input
          id="address-search"
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="IIT Delhi"
          className="flex-1 border border-gray-400 px-3 py-2"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="border border-gray-400 bg-white px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </form>

      {isLoading && <p>Loading geocoding results...</p>}

      {error && <p className="text-red-700">{error}</p>}

      {!isLoading && results.length > 0 && (
        <div className="space-y-2">
          <p className="font-medium">Results</p>
          <ul className="space-y-2">
            {results.map((result, index) => (
              <li key={`${result.display_name}-${index}`}>
                <button
                  type="button"
                  onClick={() => setSelected(result)}
                  className="w-full border border-gray-400 bg-white p-3 text-left"
                >
                  <div className="font-medium">{result.display_name}</div>
                  {result.address && (
                    <div className="text-sm text-gray-700">
                      {Object.values(result.address).filter(Boolean).join(", ")}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <MapView selected={selected} />

      {selected && (
        <div className="space-y-2 border border-gray-300 bg-gray-50 p-3">
          <p className="font-medium">Selected location:</p>
          <p>{selected.display_name}</p>
          <p>Latitude: {selected.latitude}</p>
          <p>Longitude: {selected.longitude}</p>
        </div>
      )}

      <p className="text-sm text-gray-700">
        © OpenStreetMap contributors. See the{" "}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          OpenStreetMap copyright and license information
        </a>
        .
      </p>
    </section>
  );
}
