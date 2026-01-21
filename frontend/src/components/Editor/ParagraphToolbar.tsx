import { useState } from 'react'
import { 
  Image, 
  Code, 
  Sparkles, 
  MessageSquarePlus, 
  CheckCircle,
  Loader2,
  X
} from 'lucide-react'

export type ParagraphAction = 'image' | 'code' | 'polish' | 'deepen' | 'review'

interface ParagraphToolbarProps {
  paragraphContent: string
  onAction: (action: ParagraphAction, content: string) => Promise<void>
  onClose: () => void
}

export function ParagraphToolbar({ 
  paragraphContent, 
  onAction, 
  onClose 
}: ParagraphToolbarProps) {
  const [loading, setLoading] = useState<ParagraphAction | null>(null)

  const handleAction = async (action: ParagraphAction) => {
    setLoading(action)
    try {
      await onAction(action, paragraphContent)
    } finally {
      setLoading(null)
    }
  }

  const actions = [
    { 
      id: 'image' as const, 
      icon: Image, 
      label: '配图', 
      color: 'text-purple-500 hover:bg-purple-50',
      description: '为这段内容生成配图'
    },
    { 
      id: 'code' as const, 
      icon: Code, 
      label: '配代码', 
      color: 'text-blue-500 hover:bg-blue-50',
      description: '生成示例代码'
    },
    { 
      id: 'polish' as const, 
      icon: Sparkles, 
      label: '润色', 
      color: 'text-vibe-orange hover:bg-vibe-orange/10',
      description: 'AI 优化文字表达'
    },
    { 
      id: 'deepen' as const, 
      icon: MessageSquarePlus, 
      label: '追问深化', 
      color: 'text-green-500 hover:bg-green-50',
      description: '深入探讨这个话题'
    },
    { 
      id: 'review' as const, 
      icon: CheckCircle, 
      label: '校对审查', 
      color: 'text-vibe-teal hover:bg-vibe-teal/10',
      description: '检查事实准确性'
    },
  ]

  return (
    <div className="absolute left-0 right-0 -top-12 z-10 flex items-center justify-between bg-white border rounded-lg shadow-lg px-2 py-1.5 animate-slide-in">
      <div className="flex items-center gap-1">
        {actions.map((action) => {
          const Icon = action.icon
          const isLoading = loading === action.id
          
          return (
            <button
              key={action.id}
              onClick={() => handleAction(action.id)}
              disabled={loading !== null}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${action.color} disabled:opacity-50 disabled:cursor-not-allowed`}
              title={action.description}
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Icon className="w-3.5 h-3.5" />
              )}
              <span>{action.label}</span>
            </button>
          )
        })}
      </div>
      
      <button
        onClick={onClose}
        className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
