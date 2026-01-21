import { useChatStore } from '@/stores/chatStore'
import { cn } from '@/utils/cn'
import { CheckCircle, Circle, Loader2, AlertCircle, Brain } from 'lucide-react'
import type { ExecutionLogItem, TodoItem } from '@/types'

function formatTime(date: Date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function TodoItemComponent({ item }: { item: TodoItem }) {
  return (
    <div className="flex items-start gap-2 text-sm py-1">
      {item.status === 'done' ? (
        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
      ) : item.status === 'in_progress' ? (
        <Loader2 className="w-4 h-4 text-vibe-orange animate-spin mt-0.5 flex-shrink-0" />
      ) : (
        <Circle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
      )}
      <span className={cn(
        item.status === 'done' && 'text-muted-foreground line-through',
        item.status === 'in_progress' && 'text-foreground font-medium'
      )}>
        {item.text}
      </span>
    </div>
  )
}

function LogItem({ log }: { log: ExecutionLogItem }) {
  switch (log.type) {
    case 'thinking':
      return (
        <div className="animate-slide-in bg-white rounded-lg border p-3 shadow-sm">
          <p className="text-sm text-foreground whitespace-pre-wrap">{log.content}</p>
          <span className="text-xs text-muted-foreground mt-2 block">
            {formatTime(log.timestamp)}
          </span>
        </div>
      )

    case 'tool_call':
      return (
        <div className="animate-slide-in flex items-center gap-2 py-2 px-3 bg-muted/50 rounded-lg">
          <span className="text-base">{log.toolIcon}</span>
          <span className="text-sm font-medium text-muted-foreground">Using Tool</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-sm">{log.toolName}</span>
          {log.status === 'running' && (
            <Loader2 className="w-3 h-3 animate-spin text-vibe-orange ml-auto" />
          )}
          {log.status === 'done' && (
            <CheckCircle className="w-3 h-3 text-green-500 ml-auto" />
          )}
          {log.status === 'error' && (
            <AlertCircle className="w-3 h-3 text-red-500 ml-auto" />
          )}
        </div>
      )

    case 'todo_list':
      return (
        <div className="animate-slide-in bg-muted/30 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">
              Total: {log.total} Todos
            </span>
          </div>
          <div className="space-y-0.5">
            {log.items.map((item, idx) => (
              <TodoItemComponent key={idx} item={item} />
            ))}
          </div>
        </div>
      )

    case 'preview':
      return (
        <div className="animate-slide-in bg-white rounded-lg border p-3 shadow-sm">
          {log.thumbnailUrl && (
            <img 
              src={log.thumbnailUrl} 
              alt="Preview" 
              className="w-full rounded-md border"
            />
          )}
          {log.content && (
            <p className="text-sm text-muted-foreground mt-2">{log.content}</p>
          )}
        </div>
      )

    case 'result':
      return (
        <div className={cn(
          "animate-slide-in rounded-lg p-3 border-l-4",
          log.success 
            ? "bg-green-50 border-l-green-500" 
            : "bg-red-50 border-l-red-500"
        )}>
          <div className="flex items-start gap-2">
            {log.success ? (
              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-500 mt-0.5" />
            )}
            <p className="text-sm">{log.message}</p>
          </div>
        </div>
      )

    default:
      return null
  }
}

export function ExecutionLog() {
  const { executionLogs } = useChatStore()

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {executionLogs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
          <Brain className="w-12 h-12 mb-3 opacity-30" />
          <p className="text-sm">开始对话，AI 将在这里展示执行过程</p>
        </div>
      ) : (
        executionLogs.map((log) => (
          <LogItem key={log.id} log={log} />
        ))
      )}
    </div>
  )
}
