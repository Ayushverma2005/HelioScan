export type GeocodingAddress = Record<string, string>;

export type GeocodingProviderMetadata = {
  provider: string;
  attribution: string;
  license: string | null;
  attribution_url: string | null;
  provider_result_id: string | null;
};

export type GeocodingResult = {
  display_name: string;
  latitude: number;
  longitude: number;
  address: GeocodingAddress | null;
  provider_metadata: GeocodingProviderMetadata;
};

export type GeocodeResponse = {
  results: GeocodingResult[];
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isAddress(value: unknown): value is GeocodingAddress {
  if (!isRecord(value)) {
    return false;
  }

  return Object.values(value).every((entry) => typeof entry === "string");
}

export function isProviderMetadata(value: unknown): value is GeocodingProviderMetadata {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.provider === "string" &&
    typeof value.attribution === "string" &&
    (value.license === null || typeof value.license === "string") &&
    (value.attribution_url === null || typeof value.attribution_url === "string") &&
    (value.provider_result_id === null || typeof value.provider_result_id === "string")
  );
}

export function isGeocodingResult(value: unknown): value is GeocodingResult {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.display_name === "string" &&
    typeof value.latitude === "number" &&
    typeof value.longitude === "number" &&
    (value.address === null || isAddress(value.address)) &&
    isProviderMetadata(value.provider_metadata)
  );
}

export function isGeocodeResponse(value: unknown): value is GeocodeResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.results) &&
    value.results.every((result) => isGeocodingResult(result))
  );
}

export async function searchGeocode(query: string, limit = 10): Promise<GeocodeResponse> {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new Error("Please enter an address to search.");
  }

  const response = await fetch("/api/geocode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: trimmed, limit }),
    cache: "no-store",
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = null;
    }

    if (isRecord(detail) && typeof detail.message === "string") {
      throw new Error(detail.message);
    }

    if (response.status === 422) {
      throw new Error("The address query is invalid.");
    }
    if (response.status === 502) {
      throw new Error("The geocoding service rejected the request.");
    }
    if (response.status === 503) {
      throw new Error("The geocoding service is temporarily unavailable.");
    }
    if (response.status === 504) {
      throw new Error("The geocoding service timed out.");
    }

    throw new Error(`Request failed with HTTP ${response.status}.`);
  }

  const data: unknown = await response.json();
  if (!isGeocodeResponse(data)) {
    throw new Error("Unexpected response from the geocoding service.");
  }

  return data;
}
