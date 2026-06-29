import type { Member, Tokens, User, Workspace } from "@/lib/types";
import { useAuthStore } from "@/stores/auth";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const PREFIX = "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
};

async function tryRefresh(): Promise<boolean> {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) {
    clear();
    return false;
  }
  const res = await fetch(`${BASE}${PREFIX}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    clear();
    return false;
  }
  const tokens = (await res.json()) as Tokens;
  setTokens(tokens.access_token, tokens.refresh_token);
  return true;
}

async function request<T>(path: string, opts: RequestOptions = {}, retry = true): Promise<T> {
  const { method = "GET", body, auth = true } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (auth) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${PREFIX}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // One transparent refresh-and-retry on an expired access token.
  if (res.status === 401 && auth && retry) {
    if (await tryRefresh()) return request<T>(path, opts, false);
  }

  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(res.status, data.detail || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  register: (email: string, password: string, fullName?: string) =>
    request<User>("/auth/register", {
      method: "POST",
      auth: false,
      body: { email, password, full_name: fullName },
    }),
  login: (email: string, password: string) =>
    request<Tokens>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    }),
  me: () => request<User>("/auth/me"),
  logout: () => request<{ detail: string }>("/auth/logout", { method: "POST" }),
  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (name: string, description?: string) =>
    request<Workspace>("/workspaces", { method: "POST", body: { name, description } }),
  getWorkspace: (id: string) => request<Workspace>(`/workspaces/${id}`),
  listMembers: (id: string) => request<Member[]>(`/workspaces/${id}/members`),
};
