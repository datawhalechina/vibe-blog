// 执行日志类型
export type ExecutionLogItem =
  | AIThinkingLog
  | ToolCallLog
  | TodoListLog
  | PreviewLog
  | ResultLog;

export interface AIThinkingLog {
  id: string;
  type: "thinking";
  content: string;
  timestamp: Date;
}

export interface ToolCallLog {
  id: string;
  type: "tool_call";
  toolName: string;
  toolIcon: string;
  description: string;
  status: "running" | "done" | "error";
  timestamp: Date;
}

export interface TodoListLog {
  id: string;
  type: "todo_list";
  title: string;
  total: number;
  items: TodoItem[];
  timestamp: Date;
}

export interface TodoItem {
  text: string;
  status: "pending" | "in_progress" | "done";
}

export interface PreviewLog {
  id: string;
  type: "preview";
  previewType: "block" | "image";
  thumbnailUrl?: string;
  content?: string;
  timestamp: Date;
}

export interface ResultLog {
  id: string;
  type: "result";
  success: boolean;
  message: string;
  timestamp: Date;
}

// 对话消息类型
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  actions?: BlockAction[];
}

export interface BlockAction {
  type: "insert" | "modify" | "delete" | "reorder";
  targetBlockId?: string;
  description: string;
  status: "pending" | "applied" | "rejected";
}

// 文档类型
export interface BlogDocument {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  meta: DocumentMeta;
}

export interface DocumentMeta {
  topic: string;
  articleType: "tutorial" | "problem-solving" | "comparison" | "picture-book";
  length: "mini" | "short" | "medium" | "long" | "custom";
  style: string;
  tags: string[];
}

// Block 视图状态
export interface BlockViewState {
  blockId: string;
  currentView: "preview" | "code" | "thinking";
  thinkingContent?: string;
  codeContent?: string;
}

// 编辑器上下文
export interface EditorContext {
  selectedBlockId?: string;
  selectedText?: string;
  totalBlocks: number;
  currentBlockIndex: number;
}
