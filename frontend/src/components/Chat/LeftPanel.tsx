import { ExecutionLog } from './ExecutionLog'
import { ChatInput } from './ChatInput'

interface LeftPanelProps {
  onSendMessage: (message: string) => void
}

export function LeftPanel({ onSendMessage }: LeftPanelProps) {
  return (
    <div className="flex flex-col h-full bg-gray-50/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-white">
        <h2 className="font-semibold text-sm text-vibe-orange">执行日志</h2>
      </div>

      {/* Execution Log */}
      <ExecutionLog />

      {/* Chat Input */}
      <ChatInput onSend={onSendMessage} />
    </div>
  )
}
