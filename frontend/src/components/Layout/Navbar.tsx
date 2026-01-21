import { History, Download, Share2 } from 'lucide-react'

interface NavbarProps {
  title: string
  saveStatus?: 'saved' | 'saving' | 'unsaved'
}

export function Navbar({ title, saveStatus = 'saved' }: NavbarProps) {
  return (
    <nav className="flex items-center justify-between h-14 px-4 border-b bg-white/80 backdrop-blur-sm">
      {/* Logo & Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🍌</span>
          <span className="font-bold text-lg bg-gradient-to-r from-vibe-orange to-vibe-yellow bg-clip-text text-transparent">
            Vibe Blog
          </span>
        </div>
        <span className="text-muted-foreground">/</span>
        <span className="font-medium text-sm truncate max-w-[300px]">{title}</span>
        
        {/* Save Status */}
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          saveStatus === 'saved' ? 'bg-green-100 text-green-600' :
          saveStatus === 'saving' ? 'bg-yellow-100 text-yellow-600' :
          'bg-red-100 text-red-600'
        }`}>
          {saveStatus === 'saved' ? '已保存' :
           saveStatus === 'saving' ? '保存中...' : '未保存'}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">
          <History className="w-4 h-4" />
          <span>版本历史</span>
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">
          <Download className="w-4 h-4" />
          <span>导出</span>
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-vibe-orange text-white hover:bg-vibe-orange/90 rounded-lg transition-colors">
          <Share2 className="w-4 h-4" />
          <span>分享</span>
        </button>
      </div>
    </nav>
  )
}
