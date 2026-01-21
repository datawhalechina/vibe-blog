import { useEffect, useRef, useState } from 'react'
import { useCreateBlockNote } from '@blocknote/react'
import { BlockNoteView } from '@blocknote/mantine'
import { MantineProvider } from '@mantine/core'
import { ChevronDown, Sparkles, Check, Edit3, Image, Code, MessageSquarePlus, CheckCircle, Loader2, Square, CheckSquare } from 'lucide-react'
import { markdownToBlocks } from '@/utils/markdownToBlocks'
import type { Section } from '@/stores/documentStore'

type ViewMode = 'preview' | 'code' | 'thinking'
type ParagraphAction = 'image' | 'code' | 'polish' | 'deepen' | 'review'

interface SectionEditorProps {
  section: Section
  totalSections: number
}

export function SectionEditor({ section, totalSections }: SectionEditorProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('preview')
  const [isSelected, setIsSelected] = useState(false)
  const [actionLoading, setActionLoading] = useState<ParagraphAction | null>(null)
  const prevContentRef = useRef<string>('')
  
  const editor = useCreateBlockNote({
    initialContent: [
      {
        type: "paragraph",
        content: section.content 
          ? [{ type: "text", text: "加载中...", styles: {} }]
          : [{ type: "text", text: getStatusText(section.status), styles: { italic: true } }],
      },
    ],
  })

  // 当章节内容变化时，更新编辑器
  useEffect(() => {
    if (section.content && section.content !== prevContentRef.current) {
      prevContentRef.current = section.content
      try {
        const blocks = markdownToBlocks(section.content)
        if (blocks.length > 0) {
          editor.replaceBlocks(editor.document, blocks)
        }
      } catch (error) {
        console.error(`Failed to update section ${section.index}:`, error)
      }
    } else if (!section.content && section.status !== 'complete') {
      // 显示状态占位符
      editor.replaceBlocks(editor.document, [
        {
          id: `placeholder-${section.index}`,
          type: "paragraph",
          props: { textColor: 'gray', backgroundColor: 'default', textAlignment: 'left' },
          content: [{ type: "text", text: getStatusText(section.status), styles: { italic: true } }],
          children: [],
        },
      ])
    }
  }, [section.content, section.status, editor, section.index])

  // 处理段落操作
  const handleAction = async (action: ParagraphAction) => {
    if (!section.content) return
    setActionLoading(action)
    
    try {
      // TODO: 调用后端 API
      console.log(`执行操作: ${action}`, section.content.substring(0, 100))
      
      // 模拟 API 调用
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // 根据操作类型显示提示
      const messages: Record<ParagraphAction, string> = {
        image: '🎨 配图功能开发中...',
        code: '💻 代码生成功能开发中...',
        polish: '✨ 润色功能开发中...',
        deepen: '🔍 追问深化功能开发中...',
        review: '✅ 校对审查功能开发中...',
      }
      alert(messages[action])
    } catch (error) {
      console.error(`操作失败: ${action}`, error)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div 
      className={`border-2 rounded-xl bg-white shadow-sm mb-6 overflow-hidden transition-all ${
        isSelected ? 'border-vibe-orange ring-2 ring-vibe-orange/20' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* 视图切换标签栏 */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50/50">
        <div className="flex items-center gap-3">
          {/* 选中框 */}
          <button
            onClick={() => setIsSelected(!isSelected)}
            className={`p-1 rounded transition-colors ${
              isSelected 
                ? 'text-vibe-orange' 
                : 'text-gray-400 hover:text-gray-600'
            }`}
            title={isSelected ? '取消选中' : '选中此章节'}
          >
            {isSelected ? (
              <CheckSquare className="w-5 h-5" />
            ) : (
              <Square className="w-5 h-5" />
            )}
          </button>
          
          <div className="flex items-center gap-1">
          <ViewTab 
            active={viewMode === 'preview'} 
            onClick={() => setViewMode('preview')}
          >
            Preview
          </ViewTab>
          <ViewTab 
            active={viewMode === 'code'} 
            onClick={() => setViewMode('code')}
          >
            Code
          </ViewTab>
          <ViewTab 
            active={viewMode === 'thinking'} 
            onClick={() => setViewMode('thinking')}
          >
            Thinking
          </ViewTab>
        </div>
          </div>
        
        {/* 状态标签 */}
        <StatusBadge status={section.status} />
      </div>

      {/* 选中时显示的操作工具栏 */}
      {isSelected && (
        <div className="flex items-center gap-2 px-4 py-2 bg-vibe-orange/5 border-b border-vibe-orange/20">
          <span className="text-xs text-muted-foreground mr-2">段落操作:</span>
          <ActionButton
            icon={Image}
            label="配图"
            loading={actionLoading === 'image'}
            onClick={() => handleAction('image')}
            color="purple"
          />
          <ActionButton
            icon={Code}
            label="配代码"
            loading={actionLoading === 'code'}
            onClick={() => handleAction('code')}
            color="blue"
          />
          <ActionButton
            icon={Sparkles}
            label="润色"
            loading={actionLoading === 'polish'}
            onClick={() => handleAction('polish')}
            color="orange"
          />
          <ActionButton
            icon={MessageSquarePlus}
            label="追问深化"
            loading={actionLoading === 'deepen'}
            onClick={() => handleAction('deepen')}
            color="green"
          />
          <ActionButton
            icon={CheckCircle}
            label="校对审查"
            loading={actionLoading === 'review'}
            onClick={() => handleAction('review')}
            color="teal"
          />
        </div>
      )}

      {/* 章节标题 */}
      <div className="px-6 pt-5 pb-3">
        <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
          <span className="text-vibe-orange">🍌</span>
          {section.title}
        </h2>
      </div>

      {/* 章节内容区域 */}
      <div className="px-6 pb-4 min-h-[200px]">
        {viewMode === 'preview' && (
          <MantineProvider>
            <BlockNoteView 
              editor={editor} 
              theme="light"
            />
          </MantineProvider>
        )}
        
        {viewMode === 'code' && (
          <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
            <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap">
              {section.content || '// 暂无内容'}
            </pre>
          </div>
        )}
        
        {viewMode === 'thinking' && (
          <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
            <p className="text-sm text-amber-800">
              {section.status === 'generating' 
                ? '🤔 AI 正在思考如何编写这个章节...'
                : section.status === 'complete'
                ? '✅ 章节已生成完成'
                : '⏳ 等待生成...'}
            </p>
          </div>
        )}
      </div>

      {/* 底部操作栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50/50">
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-white hover:border-vibe-teal transition-colors">
            <Check className="w-3.5 h-3.5 text-vibe-teal" />
            <span>Fact check content</span>
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-white hover:border-vibe-orange transition-colors">
            <Sparkles className="w-3.5 h-3.5 text-vibe-orange" />
            <span>AI Edit</span>
            <ChevronDown className="w-3 h-3" />
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-white transition-colors">
            <Edit3 className="w-3.5 h-3.5" />
            <span>Advanced Edit</span>
          </button>
        </div>
        
        {/* 章节序号 */}
        <span className="text-sm text-muted-foreground">
          {section.index + 1} / {totalSections}
        </span>
      </div>
    </div>
  )
}

function ViewTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
        active 
          ? 'bg-vibe-orange text-white' 
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {children}
    </button>
  )
}

interface ActionButtonProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  loading: boolean
  onClick: () => void
  color: 'purple' | 'blue' | 'orange' | 'green' | 'teal'
}

function ActionButton({ icon: Icon, label, loading, onClick, color }: ActionButtonProps) {
  const colorClasses = {
    purple: 'text-purple-600 hover:bg-purple-50 hover:border-purple-300',
    blue: 'text-blue-600 hover:bg-blue-50 hover:border-blue-300',
    orange: 'text-vibe-orange hover:bg-vibe-orange/10 hover:border-vibe-orange',
    green: 'text-green-600 hover:bg-green-50 hover:border-green-300',
    teal: 'text-vibe-teal hover:bg-vibe-teal/10 hover:border-vibe-teal',
  }

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium border border-gray-200 rounded-md transition-colors bg-white disabled:opacity-50 ${colorClasses[color]}`}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : (
        <Icon className="w-3.5 h-3.5" />
      )}
      <span>{label}</span>
    </button>
  )
}

function StatusBadge({ status }: { status: Section['status'] }) {
  switch (status) {
    case 'pending':
      return (
        <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">
          等待中
        </span>
      )
    case 'generating':
      return (
        <span className="px-2 py-0.5 text-xs rounded-full bg-vibe-orange/10 text-vibe-orange animate-pulse">
          生成中...
        </span>
      )
    case 'complete':
      return (
        <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-600">
          已完成
        </span>
      )
    default:
      return null
  }
}

function getStatusText(status: Section['status']): string {
  switch (status) {
    case 'pending':
      return '⏸️ 等待生成...'
    case 'generating':
      return '⏳ 正在生成内容...'
    case 'complete':
      return ''
    default:
      return ''
  }
}
