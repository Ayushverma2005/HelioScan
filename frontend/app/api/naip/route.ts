import { getApiBaseUrl } from "@/lib/api";
import { isNaipAcquisitionResponse } from "@/lib/naip";

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
    if (
      !isRecord(body) ||
      typeof body.min_lon !== "number" ||
      typeof body.min_lat !== "number" ||
      typeof body.max_lon !== "number" ||
      typeof body.max_lat !== "number"
    ) {
      return getErrorBody("invalid_bbox", "A valid WGS84 bounding box is required.", 422);
    }

    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/imagery/naip`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        min_lon: body.min_lon,
        min_lat: body.min_lat,
        max_lon: body.max_lon,
        max_lat: body.max_lat,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });

    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      if (isRecord(data) && isRecord(data.detail)) {
        const message = typeof data.detail.message === "string" ? data.detail.message : "NAIP imagery request failed.";
        const code = typeof data.detail.code === "string" ? data.detail.code : "unknown_error";
        return getErrorBody(code, message, response.status === 422 ? 422 : 502);
      }
      return getErrorBody("unknown_error", "Unable to complete the NAIP imagery request.", 502);
    }

    if (!isNaipAcquisitionResponse(data)) {
      return getErrorBody(
        "unexpected_response",
        "Unexpected response from the NAIP imagery service.",
        502,
      );
    }

    return Response.json(data);
  } catch {
    return getErrorBody("network_error", "Unable to connect to the HelioScan backend.", 502);
  }
}
