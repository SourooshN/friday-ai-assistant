// API Types for Friday UI

export interface TaskRequest {
  description: string;
  context?: Record<string, any>;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatus {
  id: string;
  description: string;
  context: Record<string, any>;
  status: 'submitted' | 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  result?: any;
}

export interface SystemStatus {
  initialized: boolean;
  running: boolean;
  environment: string;
  components: {
    orchestrator?: {
      running: boolean;
      total_tasks: number;
      active_tasks: number;
    };
    plugins?: {
      loaded_plugins: number;
      enabled_plugins: string[];
      loaded_plugin_ids: string[];
    };
    memory?: {
      sqlite_connected: boolean;
      chromadb_available: boolean;
      chroma_connected: boolean;
      sqlite_path: string;
      chroma_path: string;
    };
  };
}

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  component: string;
}

export interface WebSocketMessage {
  type: 'status' | 'task_update' | 'log_entry' | 'pong';
  data: any;
}

export interface TaskUpdateMessage {
  task_id: string;
  status: string;
  timestamp: string;
}

// API Response wrappers
export interface APIResponse<T> {
  data?: T;
  error?: string;
  success: boolean;
}

export interface LogsResponse {
  logs: LogEntry[];
}

export interface TasksResponse {
  tasks: TaskStatus[];
}