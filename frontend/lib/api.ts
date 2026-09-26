/**
 * Backend API configuration. The base URL comes from the environment only;
 * it must never be hardcoded in components.
 */
export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw || raw.trim() === "") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");
  }
  return raw.trim().replace(/\/+$/, "");
}
