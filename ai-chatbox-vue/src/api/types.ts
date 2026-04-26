// TypeScript type definitions for AI Chatbox API

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  system_prompt?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  model: string;
  message_count: number;
  error?: string;
  messages?: ChatMessage[];
}

export interface SessionInfo {
  session_id: string;
  created_at: string;
  message_count: number;
}

// Graph Types
export interface GraphNode {
  id: number;
  label: string;
  group: string;
  title: string;
}

export interface GraphEdge {
  from_node: number;
  to: number;
  label: string;
  title: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  session_id: string;
}

// Review Types
export interface ReviewQuestion {
  id: number;
  question: string;
  options: string[];
  correct_answer: number;
  explanation: string;
  difficulty: string;
}

export interface ReviewRecommendation {
  id: number;
  type: string;
  title: string;
  description: string;
  estimated_time: string;
  due_date: string;
  priority: string;
  completed: boolean;
}

export interface ReviewResponse {
  session_id: string;
  summary: string;
  key_points: string[];
  questions: ReviewQuestion[];
  recommendations: ReviewRecommendation[];
  next_review_date: string;
}

// Model Types
export interface ModelInfo {
  name: string;
  display_name: string;
  provider: string;
  description: string;
  context_length: number;
  supports_vision: boolean;
  default_temperature: number;
}

export interface SwitchModelRequest {
  model_name: string;
  base_url?: string;
}

export interface SwitchModelResponse {
  success: boolean;
  previous_model: string;
  new_model: string;
  message: string;
}

// API Response Wrapper
export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
}

// Error Types
export interface ApiError {
  detail: string;
  status: number;
  timestamp: string;
}