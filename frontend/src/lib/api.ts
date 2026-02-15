import type {
  Strategy,
  StrategyDetail,
  LiveStatus,
  ChatRequest,
  ChatResponse,
  IngestRequest,
  IngestResponse,
  QueryRequest,
  QueryResponse,
  MetricsResponse,
  PlaybookResponse,
  HealthResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Chat ────────────────────────────────────────────────────────
export function sendChat(body: ChatRequest) {
  return apiFetch<ChatResponse>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Strategies ──────────────────────────────────────────────────
export function listStrategies() {
  return apiFetch<Strategy[]>("/api/v1/strategies");
}

export function getStrategy(id: string) {
  return apiFetch<StrategyDetail>(`/api/v1/strategies/${id}`);
}

export function getLiveStatus(id: string) {
  return apiFetch<LiveStatus>(`/api/v1/strategies/${id}/live`);
}

// ── RAG / Knowledge ─────────────────────────────────────────────
export function ingestKnowledge(body: IngestRequest) {
  return apiFetch<IngestResponse>("/api/v1/rag/ingest", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function queryKnowledge(body: QueryRequest) {
  return apiFetch<QueryResponse>("/api/v1/rag/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Metrics ─────────────────────────────────────────────────────
export function getMetrics() {
  return apiFetch<MetricsResponse>("/api/v1/metrics");
}

// ── Playbook ────────────────────────────────────────────────────
export function getPlaybook() {
  return apiFetch<PlaybookResponse>("/api/v1/playbook");
}

export function resetPlaybook() {
  return apiFetch<{ status: string; message: string }>("/api/v1/playbook/reset", {
    method: "POST",
  });
}

// ── Health ──────────────────────────────────────────────────────
export function healthCheck() {
  return apiFetch<HealthResponse>("/api/v1/health");
}
