// Typed mirror of the backend API contracts (app/schemas/*).

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type Role = "super_admin" | "tenant_admin" | "manager" | "employee" | "viewer";

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string | null;
  role: Role;
  custom_permissions: string[];
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: string;
  description: string | null;
  created_at: string;
}

export interface TenantSettings {
  llm_provider: string | null;
  llm_model: string | null;
  embedding_provider: string | null;
  embedding_model: string | null;
  system_prompt: string | null;
  chunk_strategy: string | null;
  chunk_size: number | null;
  chunk_overlap: number | null;
  retrieval_top_k: number | null;
  enable_reranking: boolean;
  enable_tools: boolean;
  has_anthropic_key: boolean;
  has_openai_key: boolean;
  has_google_key: boolean;
}

export interface KnowledgeBase {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  document_count: number;
  created_at: string;
}

export type DocumentStatus =
  | "uploaded" | "validating" | "scanning" | "extracting" | "chunking"
  | "embedding" | "indexing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  tenant_id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string | null;
  content_type: string | null;
  size_bytes: number;
  status: DocumentStatus;
  version: number;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  token_count: number | null;
}

export interface ChatSession {
  id: string;
  tenant_id: string;
  user_id: string;
  knowledge_base_id: string | null;
  title: string;
  category: string | null;
  status: "active" | "archived" | "deleted";
  pinned: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  document_id: string | null;
  chunk_id: string | null;
  document_name: string | null;
  chunk_reference: string | null;
  page_number: number | null;
  confidence: number | null;
  source_link: string | null;
  snippet: string | null;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  reaction: string | null;
  is_edited: boolean;
  model: string | null;
  provider: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number | null;
  citations: Citation[];
  created_at: string;
}

export interface SearchHit {
  chunk_id: string | null;
  document_id: string | null;
  document_name: string | null;
  content: string;
  score: number;
  page_number: number | null;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  mode: string;
  hits: SearchHit[];
  took_ms: number;
}

export interface AnalyticsDashboard {
  window_days: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  questions_asked: number;
  failed_searches: number;
  active_users: number;
}

export interface CostByModel {
  model: string;
  tokens: number;
  cost_usd: number;
  calls: number;
}

export interface ToolDefinition {
  id: string;
  name: string;
  category: string;
  description: string;
  input_schema: Record<string, unknown>;
  handler_type: string;
  is_active: boolean;
  created_at: string;
}

export interface ReviewItem {
  id: string;
  message_id: string | null;
  reason: string;
  status: string;
  assigned_to: string | null;
  resolution: string | null;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ── Streaming chat events (SSE / WS) ──────────────────────────
export type ChatStreamEvent =
  | { type: "session"; session_id: string; title: string }
  | { type: "citations"; citations: StreamCitation[] }
  | { type: "token"; text: string }
  | { type: "tool_call"; name: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; name: string }
  | { type: "warning"; message: string }
  | { type: "error"; message: string }
  | {
      type: "done";
      message_id: string;
      usage: { prompt_tokens: number; completion_tokens: number; cost_usd: number };
      latency_ms: number;
    };

export interface StreamCitation {
  index: number;
  document_name: string | null;
  page_number: number | null;
  confidence: number;
  source_link: string | null;
  snippet: string;
}
