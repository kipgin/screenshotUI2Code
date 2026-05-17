export interface ToolCall {
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  tool_name: string;
  success: boolean;
  output: string;
  error?: string;
  data?: any;
}

export interface AgentEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'session_id' | 'file_written';
  data?: any;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
}

export interface FileNode {
  name: string;
  path: string;
  isDir: boolean;
  children?: FileNode[];
  content?: string;
}

export interface DiffInfo {
  path: string;
  oldContent: string;
  newContent: string;
  diffText: string;
  status: 'pending' | 'accepted' | 'rejected';
}

export interface GitCommit {
  hash: string;
  message: string;
  date?: string;
  author?: string;
}
