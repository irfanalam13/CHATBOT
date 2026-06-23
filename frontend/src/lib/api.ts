// Typed HTTP client with automatic refresh-token rotation on 401.
import { tokenStore } from "./storage";
import type {
  AnalyticsDashboard,
  ChatSession,
  CostByModel,
  DocumentChunk,
  DocumentItem,
  KnowledgeBase,
  Message,
  Page,
  ReviewItem,
  SearchHit,
  SearchResponse,
  Tenant,
  TenantSettings,
  Tokens,
  ToolDefinition,
  User,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    tokenStore.set((await res.json()) as Tokens);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { retry?: boolean } = {},
): Promise<T> {
  const { retry = true, ...init } = options;
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("content-type", "application/json");
  }
  const token = tokenStore.access;
  if (token) headers.set("authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401 && retry && tokenStore.refresh) {
    refreshing = refreshing ?? doRefresh();
    const ok = await refreshing;
    refreshing = null;
    if (ok) return request<T>(path, { ...options, retry: false });
    tokenStore.clear();
  }

  if (!res.ok) {
    let code = "error";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body?.error?.code ?? body?.detail?.[0]?.type ?? code;
      message = body?.error?.message ?? body?.detail?.[0]?.msg ?? message;
    } catch {
      /* non-json */
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const get = <T>(p: string) => request<T>(p);
const post = <T>(p: string, body?: unknown) =>
  request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const patch = <T>(p: string, body?: unknown) =>
  request<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined });
const del = <T>(p: string) => request<T>(p, { method: "DELETE" });

export const api = {
  // ── Auth ──
  login: (email: string, password: string, tenant_slug: string) =>
    post<Tokens>("/auth/login", { email, password, tenant_slug }),
  register: (data: {
    tenant_name: string; tenant_slug: string; admin_email: string;
    admin_password: string; admin_full_name?: string;
  }) => post<Tokens>("/auth/register", data),
  logout: (refresh_token: string) => post("/auth/logout", { refresh_token }),
  me: () => get<User>("/auth/me"),

  // ── Tenant / settings ──
  tenant: () => get<Tenant>("/tenant"),
  updateTenant: (data: Partial<Tenant>) => patch<Tenant>("/tenant", data),
  settings: () => get<TenantSettings>("/tenant/settings"),
  updateSettings: (data: Record<string, unknown>) =>
    patch<TenantSettings>("/tenant/settings", data),

  // ── Users ──
  users: (page = 1) => get<Page<User>>(`/users?page=${page}`),
  createUser: (data: Record<string, unknown>) => post<User>("/users", data),
  updateUser: (id: string, data: Record<string, unknown>) => patch<User>(`/users/${id}`, data),
  deleteUser: (id: string) => del(`/users/${id}`),

  // ── Knowledge bases ──
  knowledgeBases: () => get<Page<KnowledgeBase>>("/knowledge-bases?page_size=100"),
  createKnowledgeBase: (data: { name: string; slug: string; description?: string }) =>
    post<KnowledgeBase>("/knowledge-bases", data),
  deleteKnowledgeBase: (id: string) => del(`/knowledge-bases/${id}`),

  // ── Documents ──
  documents: (kbId?: string, page = 1) =>
    get<Page<DocumentItem>>(
      `/documents?page=${page}${kbId ? `&knowledge_base_id=${kbId}` : ""}`,
    ),
  document: (id: string) => get<DocumentItem>(`/documents/${id}`),
  documentChunks: (id: string, page = 1) =>
    get<Page<DocumentChunk>>(`/documents/${id}/chunks?page=${page}`),
  reprocessDocument: (id: string) => post(`/documents/${id}/reprocess`),
  deleteDocument: (id: string) => del(`/documents/${id}`),
  uploadDocument: (kbId: string, file: File, onProgress?: (pct: number) => void) =>
    uploadWithProgress(kbId, file, onProgress),

  // ── Search ──
  searchDocuments: (body: {
    query: string; mode?: string; top_k?: number; rerank?: boolean;
    knowledge_base_id?: string;
  }) => post<SearchResponse>("/search/documents", body),
  searchChats: (q: string) => get<{ session_id: string; title: string; snippet: string }[]>(
    `/search/chats?q=${encodeURIComponent(q)}`,
  ),
  globalSearch: (body: { query: string; mode?: string }) =>
    post<{ query: string; documents: SearchHit[]; chats: unknown[]; took_ms: number }>(
      "/search/global",
      body,
    ),

  // ── Chat ──
  sessions: (params = "") => get<Page<ChatSession>>(`/chat/sessions${params}`),
  createSession: (data: Record<string, unknown>) => post<ChatSession>("/chat/sessions", data),
  updateSession: (id: string, data: Record<string, unknown>) =>
    patch<ChatSession>(`/chat/sessions/${id}`, data),
  deleteSession: (id: string) => del(`/chat/sessions/${id}`),
  sessionMessages: (id: string) => get<Message[]>(`/chat/sessions/${id}/messages`),
  react: (messageId: string, reaction: string | null) =>
    post(`/chat/messages/${messageId}/reaction`, { reaction }),
  editMessage: (messageId: string, content: string) =>
    patch(`/chat/messages/${messageId}`, { content }),

  // ── Analytics ──
  dashboard: (days = 30) => get<AnalyticsDashboard>(`/analytics/dashboard?days=${days}`),
  costByModel: () => get<CostByModel[]>("/analytics/cost-by-model"),

  // ── Feedback ──
  submitFeedback: (data: {
    message_id: string; feedback_type: string; comment?: string; correction?: string;
  }) => post("/feedback", data),
  reviewQueue: (page = 1) => get<Page<ReviewItem>>(`/feedback/review-queue?page=${page}`),

  // ── Tools ──
  tools: () => get<Page<ToolDefinition>>("/tools?page_size=100"),
  createTool: (data: Record<string, unknown>) => post<ToolDefinition>("/tools", data),
  deleteTool: (id: string) => del(`/tools/${id}`),
};

// XHR upload to surface progress (fetch has no upload progress on most browsers).
function uploadWithProgress(
  kbId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<DocumentItem> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("knowledge_base_id", kbId);
    form.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/documents/upload`);
    const token = tokenStore.access;
    if (token) xhr.setRequestHeader("authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
      else reject(new ApiError(xhr.status, "upload_failed", xhr.responseText));
    };
    xhr.onerror = () => reject(new ApiError(0, "network", "Upload failed"));
    xhr.send(form);
  });
}
