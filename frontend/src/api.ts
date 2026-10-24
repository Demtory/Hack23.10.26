import type {
  CustomerDetail,
  CustomerPage,
  Level,
  ModelSettings,
  Snapshot,
  Summary,
  User,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // keep status text
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface CustomerQuery {
  sort: string;
  order: string;
  level?: Level | "";
  q?: string;
  page: number;
  pageSize: number;
}

export const api = {
  me: () => request<User>("/api/v1/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" }),
  customers: (query: CustomerQuery) => {
    const params = new URLSearchParams({
      sort: query.sort,
      order: query.order,
      page: String(query.page),
      pageSize: String(query.pageSize),
    });
    if (query.level) params.set("level", query.level);
    if (query.q?.trim()) params.set("q", query.q.trim());
    return request<CustomerPage>(`/api/v1/customers?${params.toString()}`);
  },
  customer: (id: number) => request<CustomerDetail>(`/api/v1/customers/${id}`),
  summary: () => request<Summary>("/api/v1/analytics/summary"),
  settings: () => request<ModelSettings>("/api/v1/model/settings"),
  updateSettings: (payload: Partial<ModelSettings>) =>
    request<{ settings: ModelSettings; summary: Summary }>("/api/v1/model/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  source: () => request<Snapshot>("/api/v1/source/snapshot"),
  replaceSource: (snapshot: Snapshot) =>
    request<{ counts: Record<string, number>; summary: Summary }>("/api/v1/source/snapshot", {
      method: "PUT",
      body: JSON.stringify(snapshot),
    }),
};
