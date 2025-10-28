const DEFAULT_API_BASE = "http://localhost:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE ?? DEFAULT_API_BASE;
}
