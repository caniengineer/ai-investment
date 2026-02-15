// ── Backend model types ─────────────────────────────────────────────

export interface Strategy {
  id: string;
  name: string;
  asset: string;
  strategy_type: string;
  indicator: string;
  params: Record<string, number>;
  entry_rule: string;
  exit_rule: string;
  stop_loss_pct: number;
  lookback_months: number;
  status: "created" | "backtested" | "deployed" | "paused";
  created_at: string;
}

export interface BacktestResult {
  id: string;
  strategy_id: string;
  iteration: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
  passed: boolean;
  changes_made: string;
  metrics: Record<string, number>;
  created_at: string;
}

export interface PaperTrade {
  id: string;
  strategy_id: string;
  status: "active" | "paused" | "stopped";
  entry_price: number;
  current_price: number;
  position: "flat" | "long";
  pnl: number;
  order_history: OrderEntry[];
  last_check: string;
  created_at: string;
}

export interface OrderEntry {
  action: string;
  price: number;
  timestamp: string;
}

export interface KnowledgeChunk {
  source: string;
  content: string;
  similarity: number;
}

export interface AgentLog {
  id: string;
  strategy_id: string | null;
  agent: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface PlaybookEntry {
  id: string;
  entry_id: string;
  section: string;
  content: string;
  helpful_count: number;
  harmful_count: number;
  created_at: string;
  updated_at: string;
}

export interface LLMMetric {
  provider: string;
  model: string;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  avg_latency_ms: number;
}

// ── API request / response types ────────────────────────────────────

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  strategy_id: string;
  strategy: Record<string, unknown>;
  backtest: BacktestSummary;
  deployment: DeploymentInfo;
  ace_feedback?: AceFeedback;
  summary: string;
}

export interface BacktestSummary {
  passed: boolean;
  metrics: Record<string, number>;
  iterations: BacktestIteration[];
  explanation: string;
}

export interface BacktestIteration {
  attempt: number;
  strategy_params: Record<string, number>;
  metrics: Record<string, number>;
  passed: boolean;
  explanation: string;
}

export interface DeploymentInfo {
  trade_id: string;
  strategy_id: string;
  status: string;
  backtest_passed: boolean;
  message: string;
}

export interface AceFeedback {
  reflection: Record<string, unknown>;
  curation: Record<string, unknown>;
  playbook_stats: Record<string, unknown>;
}

export interface IngestRequest {
  content: string;
  source?: string;
}

export interface IngestResponse {
  message: string;
  chunks: number;
}

export interface QueryRequest {
  query: string;
  top_k?: number;
}

export interface QueryResponse {
  query: string;
  results: KnowledgeChunk[];
}

export interface HealthResponse {
  status: string;
  service: string;
  llm_provider: string;
}

export interface MetricsResponse {
  llm_usage: LLMMetric[];
  tool_calls: { tool: string; count: number }[];
  agent_actions: { agent: string; action: string; count: number }[];
}

export interface PlaybookResponse {
  stats: Record<string, unknown>;
  rendered: string;
  entries: PlaybookEntry[];
}

export interface StrategyDetail extends Strategy {
  backtest_history: BacktestResult[];
  agent_log: AgentLog[];
}
