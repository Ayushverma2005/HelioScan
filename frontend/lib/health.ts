/** Shape returned by the backend GET /health endpoint. */
export type BackendHealth = {
  status: string;
};

/** Response of this app's same-origin /api/backend-health route. */
export type BackendHealthResult =
  | { ok: true; health: BackendHealth }
  | { ok: false; error: string };

export function isBackendHealth(value: unknown): value is BackendHealth {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { status?: unknown }).status === "string"
  );
}
