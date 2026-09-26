import { getApiBaseUrl } from "@/lib/api";
import { isGeocodeResponse, type GeocodeResponse } from "@/lib/geocode";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getErrorBody(code: string, message: string, status: number): Response {
  return Response.json(
    {
      detail: { code, message },
    },
    { status },
  );
}

export async function POST(request: Request): Promise<Response> {
  try {
    const body = (await request.json()) as unknown;
    if (!isRecord(body) || typeof body.query !== "string") {
      return getErrorBody("invalid_query", "Please enter an address to search.", 422);
    }

    const query = body.query.trim();
    const limit =
      typeof body.limit === "number" && Number.isFinite(body.limit)
        ? Math.min(40, Math.max(1, Math.round(body.limit)))
        : 10;

    if (!query) {
      return getErrorBody("invalid_query", "Please enter an address to search.", 422);
    }

    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/geocode`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, limit }),
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });

    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      if (isRecord(data) && typeof data.detail === "object" && data.detail && isRecord(data.detail)) {
        const message = typeof data.detail.message === "string" ? data.detail.message : "Geocoding failed.";
        const code = typeof data.detail.code === "string" ? data.detail.code : "unknown_error";
        return getErrorBody(code, message, response.status === 422 ? 422 : 502);
      }
      return getErrorBody("unknown_error", "Unable to complete the geocoding request.", 502);
    }

    if (!isGeocodeResponse(data)) {
      return getErrorBody(
        "unexpected_response",
        "Unexpected response from the geocoding service.",
        502,
      );
    }

    return Response.json(data satisfies GeocodeResponse);
  } catch {
    return getErrorBody(
      "network_error",
      "Unable to connect to the HelioScan backend.",
      502,
    );
  }
}
