export type NaipBbox = {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
};

export type NaipAcquisitionResponse = {
  acquisition_status: "acquired";
  acquisition_id: string;
  image_url: string;
  provider: string;
  service_name: string;
  source_url: string;
  attribution: string;
  request_bbox: NaipBbox;
  request_bbox_crs: string;
  requested_size: [number, number];
  requested_resolution_web_mercator_meters_per_pixel: number;
  width: number;
  height: number;
  band_count: number;
  dtype: string;
  crs: string;
  bounds: { left: number; bottom: number; right: number; top: number };
  resolution: [number, number];
  pixel_size: [number, number];
  transform: [number, number, number, number, number, number];
  format: string;
  pixel_type: string;
  band_ids: number[];
  acquired_at: string;
  response_content_type: string | null;
  response_headers: Record<string, string>;
  service_metadata: Record<string, unknown>;
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isNaipBbox(value: unknown): value is NaipBbox {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.min_lon === "number" &&
    typeof value.min_lat === "number" &&
    typeof value.max_lon === "number" &&
    typeof value.max_lat === "number" &&
    Number.isFinite(value.min_lon) &&
    Number.isFinite(value.min_lat) &&
    Number.isFinite(value.max_lon) &&
    Number.isFinite(value.max_lat)
  );
}

export function buildNaipBboxFromCenter(
  center: { lat: number; lng: number },
  radiusDegrees = 0.0025,
): NaipBbox {
  const lat = Number(center.lat);
  const lng = Number(center.lng);

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    throw new Error("The selected map extent is invalid.");
  }

  const halfSize = Math.abs(radiusDegrees);
  return {
    min_lon: Math.max(-180, lng - halfSize),
    min_lat: Math.max(-90, lat - halfSize),
    max_lon: Math.min(180, lng + halfSize),
    max_lat: Math.min(90, lat + halfSize),
  };
}

export function resolveNaipImageUrl(imageUrl: string): string {
  const match = imageUrl.match(/\/api\/imagery\/naip\/([^/]+)\/image(?:$|\?)/);
  if (!match) {
    return imageUrl;
  }

  return `/api/naip/image/${match[1]}`;
}

export function isNaipAcquisitionResponse(value: unknown): value is NaipAcquisitionResponse {
  if (!isRecord(value)) {
    return false;
  }

  const requestBBox = value.request_bbox;
  const responseHeaders = value.response_headers;
  const serviceMetadata = value.service_metadata;

  const hasBoundingBox = isNaipBbox(requestBBox);
  const hasResponseHeaders = isRecord(responseHeaders) && Object.values(responseHeaders).every((entry) => typeof entry === "string");
  const hasServiceMetadata = isRecord(serviceMetadata);
  const hasRequestedSize = Array.isArray(value.requested_size) && value.requested_size.length === 2 && value.requested_size.every((entry) => typeof entry === "number");
  const hasResolution = Array.isArray(value.resolution) && value.resolution.length === 2 && value.resolution.every((entry) => typeof entry === "number");
  const hasPixelSize = Array.isArray(value.pixel_size) && value.pixel_size.length === 2 && value.pixel_size.every((entry) => typeof entry === "number");
  const hasBandIds = Array.isArray(value.band_ids) && value.band_ids.every((entry) => typeof entry === "number");
  const hasTransform = Array.isArray(value.transform) && value.transform.length === 6 && value.transform.every((entry) => typeof entry === "number");

  return (
    value.acquisition_status === "acquired" &&
    typeof value.acquisition_id === "string" &&
    typeof value.image_url === "string" &&
    typeof value.provider === "string" &&
    typeof value.service_name === "string" &&
    typeof value.source_url === "string" &&
    typeof value.attribution === "string" &&
    typeof value.request_bbox_crs === "string" &&
    typeof value.requested_resolution_web_mercator_meters_per_pixel === "number" &&
    typeof value.width === "number" &&
    typeof value.height === "number" &&
    typeof value.band_count === "number" &&
    typeof value.dtype === "string" &&
    typeof value.crs === "string" &&
    isRecord(value.bounds) &&
    typeof value.bounds.left === "number" &&
    typeof value.bounds.bottom === "number" &&
    typeof value.bounds.right === "number" &&
    typeof value.bounds.top === "number" &&
    typeof value.format === "string" &&
    typeof value.pixel_type === "string" &&
    typeof value.acquired_at === "string" &&
    (value.response_content_type === null || typeof value.response_content_type === "string") &&
    hasBoundingBox &&
    hasResponseHeaders &&
    hasServiceMetadata &&
    hasRequestedSize &&
    hasResolution &&
    hasPixelSize &&
    hasBandIds &&
    hasTransform
  );
}

export async function requestNaipAcquisition(bbox: NaipBbox): Promise<NaipAcquisitionResponse> {
  const response = await fetch("/api/naip", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(bbox),
    cache: "no-store",
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (isRecord(data) && isRecord(data.detail)) {
      const code = typeof data.detail.code === "string" ? data.detail.code : "unknown_error";
      const message = typeof data.detail.message === "string" ? data.detail.message : "Unable to request NAIP imagery.";
      const error = new Error(message);
      (error as Error & { code?: string }).code = code;
      throw error;
    }

    throw new Error("Unable to request NAIP imagery.");
  }

  if (!isNaipAcquisitionResponse(data)) {
    throw new Error("Unexpected response from the NAIP imagery service.");
  }

  return data;
}
