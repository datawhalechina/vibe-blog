import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic, Loader2 } from 'lucide-react'
import { useChatStore } from '@/stores/chatStore'
import { cn } from '@/utils/cn'

interface ChatInputProps {
  onSend: (message: string) => void
}

export function ChatInput({ onSend }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { isGenerating } = useChatStore()

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`
    }
  }, [input])

  const handleSend = () => {
    if (!input.trim() || isGenerating) return
    onSend(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="p-4 border-t bg-white">
      {/* Tab Switcher */}
      <div className="flex gap-2 mb-3">
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-vibe-orange/10 text-vibe-orange border border-vibe-orange/30 rounded-lg">
          <span>🤖</span>
          <span>AI Blog</span>
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted rounded-lg">
          <span>👥</span>
          <span>Team Chat</span>
        </button>
      </div>

      {/* Input Area */}
      <div className="relative">
        <div className="relative bg-muted/50 rounded-xl border focus-within:border-vibe-orange/50 focus-within:ring-2 focus-within:ring-vibe-orange/20 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的博客需求..."
            disabled={isGenerating}
            className={cn(
              "w-full px-4 py-3 bg-transparent resize-none outline-none text-sm",
              "placeholder:text-muted-foreground/50",
              "min-h-[80px] max-h-[150px]"
            )}
            rows={3}
          />
          
          {/* Actions */}
          <div className="flex items-center justify-between px-3 py-2 border-t border-border/50">
            <div className="flex items-center gap-1">
              <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">
                <Paperclip className="w-4 h-4" />
              </button>
              <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">
                <Mic className="w-4 h-4" />
              </button>
            </div>
            
            <button
              onClick={handleSend}
              disabled={!input.trim() || isGenerating}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                input.trim() && !isGenerating
                  ? "bg-vibe-orange text-white hover:bg-vibe-orange/90"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>生成中...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>发送</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
