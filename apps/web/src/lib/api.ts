import type {
  Analytics,
  ApiKey,
  ApiKeyCreated,
  AskResponse,
  AskStreamDone,
  AuditLog,
  Chunk,
  Conversation,
  ConversationDetail,
  DocumentItem,
  Feedback,
  FeedbackRating,
  Invitation,
  InvitationCreated,
  Member,
  RetrieveResponse,
  Role,
  Tag,
  Tokens,
  UsageSummary,
  User,
  Workspace,
} from "@/lib/types";
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
  formData?: FormData;
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
  const { method = "GET", body, auth = true, formData } = opts;
  const isForm = formData !== undefined;
  const headers: Record<string, string> = {};
  if (!isForm) headers["Content-Type"] = "application/json";

  if (auth) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${PREFIX}${path}`, {
    method,
    headers,
    body: isForm ? formData : body !== undefined ? JSON.stringify(body) : undefined,
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
  logout: () =>
    request<{ detail: string }>("/auth/logout", {
      method: "POST",
      body: { refresh_token: useAuthStore.getState().refreshToken },
    }),
  oauthProviders: () =>
    request<{ providers: string[] }>("/auth/oauth/providers", { auth: false }),
  oauthAuthorize: (provider: string, redirectUri: string) =>
    request<{ authorize_url: string; state: string }>("/auth/oauth/authorize", {
      method: "POST",
      auth: false,
      body: { provider, redirect_uri: redirectUri },
    }),
  oauthCallback: (provider: string, code: string, redirectUri: string) =>
    request<Tokens>("/auth/oauth/callback", {
      method: "POST",
      auth: false,
      body: { provider, code, redirect_uri: redirectUri },
    }),
  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (name: string, description?: string) =>
    request<Workspace>("/workspaces", { method: "POST", body: { name, description } }),
  getWorkspace: (id: string) => request<Workspace>(`/workspaces/${id}`),
  updateWorkspace: (
    id: string,
    data: { name?: string; description?: string; monthly_question_limit?: number | null },
  ) => request<Workspace>(`/workspaces/${id}`, { method: "PATCH", body: data }),
  deleteWorkspace: (id: string) =>
    request<void>(`/workspaces/${id}`, { method: "DELETE" }),

  listApiKeys: (id: string) => request<ApiKey[]>(`/workspaces/${id}/api-keys`),
  createApiKey: (id: string, name: string) =>
    request<ApiKeyCreated>(`/workspaces/${id}/api-keys`, { method: "POST", body: { name } }),
  revokeApiKey: (id: string, keyId: string) =>
    request<void>(`/workspaces/${id}/api-keys/${keyId}`, { method: "DELETE" }),

  getUsage: (id: string) => request<UsageSummary>(`/workspaces/${id}/usage`),
  getAnalytics: (id: string) => request<Analytics>(`/workspaces/${id}/analytics`),

  listMembers: (id: string) => request<Member[]>(`/workspaces/${id}/members`),
  changeMemberRole: (id: string, userId: string, role: Role) =>
    request<Member>(`/workspaces/${id}/members/${userId}/role`, {
      method: "PATCH",
      body: { role },
    }),
  removeMember: (id: string, userId: string) =>
    request<void>(`/workspaces/${id}/members/${userId}`, { method: "DELETE" }),

  listInvitations: (id: string) =>
    request<Invitation[]>(`/workspaces/${id}/invitations`),
  createInvitation: (id: string, email: string, role: Role) =>
    request<InvitationCreated>(`/workspaces/${id}/invitations`, {
      method: "POST",
      body: { email, role },
    }),
  revokeInvitation: (id: string, invitationId: string) =>
    request<void>(`/workspaces/${id}/invitations/${invitationId}`, { method: "DELETE" }),
  acceptInvitation: (token: string) =>
    request<Workspace>("/invitations/accept", { method: "POST", body: { token } }),

  listAuditLogs: (id: string) =>
    request<AuditLog[]>(`/workspaces/${id}/audit-logs`),

  listTags: (id: string) => request<Tag[]>(`/workspaces/${id}/tags`),
  addDocumentTag: (workspaceId: string, documentId: string, name: string) =>
    request<Tag[]>(`/workspaces/${workspaceId}/documents/${documentId}/tags`, {
      method: "POST",
      body: { name },
    }),
  removeDocumentTag: (workspaceId: string, documentId: string, tagId: string) =>
    request<Tag[]>(`/workspaces/${workspaceId}/documents/${documentId}/tags/${tagId}`, {
      method: "DELETE",
    }),

  listDocuments: (
    workspaceId: string,
    filters?: { status_filter?: string; search?: string; tag_id?: string },
  ) => {
    const qs = new URLSearchParams();
    if (filters?.status_filter) qs.set("status_filter", filters.status_filter);
    if (filters?.search) qs.set("search", filters.search);
    if (filters?.tag_id) qs.set("tag_id", filters.tag_id);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<DocumentItem[]>(`/workspaces/${workspaceId}/documents${suffix}`);
  },
  uploadDocument: (workspaceId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentItem>(`/workspaces/${workspaceId}/documents`, {
      method: "POST",
      formData: fd,
    });
  },
  deleteDocument: (workspaceId: string, id: string) =>
    request<void>(`/workspaces/${workspaceId}/documents/${id}`, { method: "DELETE" }),
  reprocessDocument: (workspaceId: string, id: string) =>
    request<DocumentItem>(`/workspaces/${workspaceId}/documents/${id}/reprocess`, {
      method: "POST",
    }),
  getDocument: (workspaceId: string, id: string) =>
    request<DocumentItem>(`/workspaces/${workspaceId}/documents/${id}`),
  getChunks: (workspaceId: string, id: string) =>
    request<Chunk[]>(`/workspaces/${workspaceId}/documents/${id}/chunks`),

  retrieve: (
    workspaceId: string,
    payload: { question: string; document_ids?: string[]; top_k?: number; hybrid?: boolean },
  ) =>
    request<RetrieveResponse>(`/workspaces/${workspaceId}/search/retrieve`, {
      method: "POST",
      body: payload,
    }),

  listConversations: (workspaceId: string) =>
    request<Conversation[]>(`/workspaces/${workspaceId}/chat/conversations`),
  getConversation: (workspaceId: string, conversationId: string) =>
    request<ConversationDetail>(
      `/workspaces/${workspaceId}/chat/conversations/${conversationId}`,
    ),
  deleteConversation: (workspaceId: string, conversationId: string) =>
    request<void>(`/workspaces/${workspaceId}/chat/conversations/${conversationId}`, {
      method: "DELETE",
    }),
  ask: (
    workspaceId: string,
    payload: { question: string; conversation_id?: string; document_ids?: string[] },
  ) => request<AskResponse>(`/workspaces/${workspaceId}/chat/ask`, { method: "POST", body: payload }),
  askStream: async (
    workspaceId: string,
    payload: { question: string; conversation_id?: string; document_ids?: string[] },
    handlers: {
      onToken: (text: string) => void;
      onDone: (done: AskStreamDone) => void;
      onError?: (message: string) => void;
    },
  ): Promise<void> => {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${BASE}${PREFIX}/workspaces/${workspaceId}/chat/ask/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok || !res.body) {
      handlers.onError?.(res.status === 429 ? "Question limit reached." : `Request failed (${res.status})`);
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const dataLine = frame.split("\n").find((l) => l.startsWith("data: "));
        if (!dataLine) continue;
        const event = JSON.parse(dataLine.slice(6));
        if (event.type === "token") handlers.onToken(event.text);
        else if (event.type === "done") handlers.onDone(event as AskStreamDone);
        else if (event.type === "error") handlers.onError?.(event.detail);
      }
    }
  },
  submitFeedback: (
    workspaceId: string,
    messageId: string,
    rating: FeedbackRating,
    comment?: string,
  ) =>
    request<Feedback>(`/workspaces/${workspaceId}/chat/messages/${messageId}/feedback`, {
      method: "POST",
      body: { rating, comment },
    }),
};
