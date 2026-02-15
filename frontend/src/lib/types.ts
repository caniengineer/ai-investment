// Strategy
export interface Strategy {
  id: string;
  name: string;
  asset: string;
  strategy_type: string;
  indicator: string;
  params: Record<string, unknown>;
  entry_rule: string;
  exit_rule: string;
  stop_loss_pct: number;
  lookback_months: number;
  status: "created" | "backtested" | "deployed" | "paused";
  created_at: string;
}

// Backtest
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
  metrics: Record<string, unknown>;
  created_at: string;
}

// Paper trading
export interface PaperTrade {
  id: string;
  strategy_id: string;
  status: "active" | "paused" | "stopped";
  entry_price: number;
  current_price: number;
  position: "flat" | "long";
  pnl: number;
  order_history: OrderRecord[];
  last_check: string;
  created_at: string;
}

export interface OrderRecord {
  action: string;
  price: number;
  timestamp: string;
}

// Knowledge / RAG
export interface KnowledgeChunk {
  id: string;
  source: string;
  content: string;
  created_at: string;
}

export interface RagResult {
  source: string;
  content: string;
  similarity: number;
}

// Agent logs
export interface AgentLog {
  id: string;
  strategy_id: string | null;
  agent: "strategy_agent" | "backtest_agent" | "deploy_agent" | "orchestrator";
  action: string;
  detail: string;
  created_at: string;
}

// Playbook (ACE)
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

export interface PlaybookResponse {
  stats: {
    total_entries: number;
    sections: Record<
      string,
      { count: number; avg_helpful: number; avg_harmful: number }
    >;
  };
  rendered: string;
  entries: PlaybookEntry[];
}

// Metrics / observability
export interface LlmUsage {
  provider: string;
  model: string;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  avg_latency_ms: number;
}

export interface ToolCall {
  tool: string;
  count: number;
}

export interface AgentAction {
  agent: string;
  action: string;
  count: number;
}

export interface MetricsResponse {
  llm_usage: LlmUsage[];
  tool_calls: ToolCall[];
  agent_actions: AgentAction[];
}

// Chat
export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  strategy_id: string;
  strategy: {
    name: string;
    asset: string;
    strategy_type: string;
    indicator: string;
    params: Record<string, unknown>;
    entry_rule: string;
    exit_rule: string;
    stop_loss_pct: number;
  };
  backtest: {
    passed: boolean;
    metrics: {
      total_return: number;
      sharpe_ratio: number;
      max_drawdown: number;
      win_rate: number;
      num_trades: number;
    };
    iterations: BacktestResult[];
    explanation: string;
  };
  deployment: Record<string, unknown>;
  summary: string;
}

// Strategy detail (expanded)
export interface StrategyDetail extends Strategy {
  backtest_history: BacktestResult[];
  agent_log: AgentLog[];
}

// Live trading status
export interface LiveStatus {
  trade_id: string;
  status: string;
  position: string;
  entry_price: number;
  current_price: number;
  pnl: number;
  order_history: OrderRecord[];
  last_check: string;
  created_at: string;
}

// RAG requests
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
  results: RagResult[];
}

// Health
export interface HealthResponse {
  status: string;
  service: string;
  llm_provider: string;
}
