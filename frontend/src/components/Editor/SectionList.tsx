import { useDocumentStore } from '@/stores/documentStore'
import { SectionEditor } from './SectionEditor'
import { FileText, Plus } from 'lucide-react'

export function SectionList() {
  const { outline } = useDocumentStore()

  if (!outline) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8">
        <FileText className="w-16 h-16 mb-4 opacity-30" />
        <p className="text-lg font-medium mb-2">还没有内容</p>
        <p className="text-sm text-center">
          在左侧输入博客主题，AI 将自动生成大纲和章节内容
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      {/* 文章标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">
          {outline.title}
        </h1>
        {outline.summary && (
          <p className="text-muted-foreground text-sm">{outline.summary}</p>
        )}
        <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
          <span>{outline.sections.length} 个章节</span>
          <span>•</span>
          <span>
            {outline.sections.filter(s => s.status === 'complete').length} 已完成
          </span>
        </div>
      </div>

      {/* 章节列表 - 每个章节是独立的 BlockNote */}
      <div className="space-y-4">
        {outline.sections.map((section) => (
          <SectionEditor 
            key={section.index} 
            section={section}
            totalSections={outline.sections.length}
          />
        ))}
      </div>

      {/* 添加章节按钮 */}
      <button className="w-full mt-4 py-3 border-2 border-dashed border-gray-200 rounded-lg text-muted-foreground hover:border-vibe-orange hover:text-vibe-orange transition-colors flex items-center justify-center gap-2">
        <Plus className="w-4 h-4" />
        <span>添加新章节</span>
      </button>
    </div>
  )
}
