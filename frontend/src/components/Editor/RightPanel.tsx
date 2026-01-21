import { SectionList } from './SectionList'
import { BlogEditor } from './BlogEditor'
import { useDocumentStore } from '@/stores/documentStore'
import { Download, Share2 } from 'lucide-react'

export function RightPanel() {
  const { outline, title } = useDocumentStore()

  return (
    <div className="flex flex-col h-full bg-gray-50/30">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-white">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-foreground">
            {outline ? outline.title : title || '新建博客'}
          </span>
          {outline && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-vibe-orange/10 text-vibe-orange">
              {outline.sections.filter(s => s.status === 'complete').length}/{outline.sections.length} 章节
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted rounded-lg transition-colors">
            <Download className="w-4 h-4" />
            导出
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-vibe-orange text-white hover:bg-vibe-orange/90 rounded-lg transition-colors">
            <Share2 className="w-4 h-4" />
            分享
          </button>
        </div>
      </div>

      {/* Content - 根据是否有大纲显示不同内容 */}
      <div className="flex-1 overflow-hidden">
        {outline ? (
          <SectionList />
        ) : (
          <BlogEditor />
        )}
      </div>

      {/* Footer - 全局操作 */}
      {outline && (
        <div className="flex items-center justify-between px-4 py-3 border-t bg-white">
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-muted transition-colors">
              <span className="w-2 h-2 rounded-full bg-vibe-teal"></span>
              全文事实核查
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-muted transition-colors">
              ✨ AI 润色全文
            </button>
          </div>
          
          <span className="text-sm text-muted-foreground">
            共 {outline.sections.length} 个章节
          </span>
        </div>
      )}
    </div>
  )
}
