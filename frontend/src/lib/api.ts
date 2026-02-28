/** Base URL for all API calls. Empty string = same origin (works in both dev proxy and prod). */
const BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// ── Typed API helpers ────────────────────────────────────────────────────────

export interface SettingsData {
  data: Record<string, string>;
}

export const settingsApi = {
  get: () => api.get<SettingsData>("/api/settings"),
  patch: (updates: Record<string, string>) => api.patch<SettingsData>("/api/settings", { updates }),
};
