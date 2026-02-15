import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
  IngestRequest,
  IngestResponse,
  MetricsResponse,
  PlaybookResponse,
  QueryRequest,
  QueryResponse,
  Strategy,
  StrategyDetail,
  PaperTrade,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Base fetch wrapper ──────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ───────────────────────────────────────────────────────────

export function fetchHealth() {
  return apiFetch<HealthResponse>("/health");
}

// ── Chat ─────────────────────────────────────────────────────────────

export function sendChat(data: ChatRequest) {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Strategies ───────────────────────────────────────────────────────

export function fetchStrategies() {
  return apiFetch<Strategy[]>("/strategies");
}

export function fetchStrategy(id: string) {
  return apiFetch<StrategyDetail>(`/strategies/${id}`);
}

export function fetchLiveTrading(strategyId: string) {
  return apiFetch<PaperTrade>(`/strategies/${strategyId}/live`);
}

// ── RAG / Knowledge ──────────────────────────────────────────────────

export function ingestDocument(data: IngestRequest) {
  return apiFetch<IngestResponse>("/rag/ingest", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function queryKnowledge(data: QueryRequest) {
  return apiFetch<QueryResponse>("/rag/query", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Metrics ──────────────────────────────────────────────────────────

export function fetchMetrics() {
  return apiFetch<MetricsResponse>("/metrics");
}

// ── Playbook ─────────────────────────────────────────────────────────

export function fetchPlaybook() {
  return apiFetch<PlaybookResponse>("/playbook");
}

export function resetPlaybook() {
  return apiFetch<{ status: string; message: string }>("/playbook/reset", {
    method: "POST",
  });
}
