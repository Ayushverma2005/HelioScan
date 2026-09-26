import { getApiBaseUrl } from "@/lib/api";
import { isBackendHealth, type BackendHealthResult } from "@/lib/health";

const TIMEOUT_MS = 5000;

function fail(error: string, status: number): Response {
  const body: BackendHealthResult = { ok: false, error };
  return Response.json(body, { status });
}

/**
 * Server-side check of the FastAPI GET /health endpoint. Done server-side
 * because the backend does not send CORS headers, so a browser cannot call
 * it directly from the Next.js origin.
 */
export async function GET(): Promise<Response> {
  let baseUrl: string;
  try {
    baseUrl = getApiBaseUrl();
  } catch (err) {
    return fail(err instanceof Error ? err.message : "Invalid API configuration", 500);
  }

  try {
    const res = await fetch(`${baseUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) {
      return fail(`Backend responded with HTTP ${res.status}`, 502);
    }
    const data: unknown = await res.json();
    if (!isBackendHealth(data) || data.status !== "ok") {
      return fail("Unexpected response from backend /health", 502);
    }
    const body: BackendHealthResult = { ok: true, health: data };
    return Response.json(body);
  } catch {
    return fail("Unable to connect to the HelioScan backend.", 502);
  }
}
