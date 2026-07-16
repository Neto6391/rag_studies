export type BackendId = "agentic" | "simple";

export interface BackendOption {
  id: BackendId;
  label: string;
  baseUrl: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: number;
  session_id: string;
  role: ChatRole;
  content: string;
  hallucinated: boolean | null;
  created_at: string;
  sources?: SearchResult[] | null;
}

export interface SearchResult {
  id: string;
  title: string;
  source: string;
  score: number;
  rerank_score?: number;
  text: string;
}

export interface ChatResponse {
  message_id: number;
  response: string;
  results: SearchResult[];
}

export interface ChatSession {
  session_id: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  preview: string;
}

export interface CorpusBreakdownItem {
  name: string;
  count: number;
}

export interface DashboardStats {
  corpus_total: number;
  predominant_corpus: string;
  corpus_breakdown: CorpusBreakdownItem[];
  total_messages: number;
  total_sessions: number;
  hallucination_count: number;
}
