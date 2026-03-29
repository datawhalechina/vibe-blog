// 工具函数

// 格式化文件大小
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

// 格式化字数
export function formatWordCount(count: number): string {
  if (count >= 10000) {
    return `约 ${(count / 10000).toFixed(1)} 万字`
  } else if (count >= 1000) {
    return `约 ${(count / 1000).toFixed(1)} 千字`
  }
  return `${count} 字`
}

// 获取状态文本
export function getStatusText(status: string): string {
  const texts: Record<string, string> = {
    'uploading': '上传中...',
    'pending': '等待解析...',
    'parsing': '解析中...',
    'ready': '已就绪',
    'error': '解析失败',
    'timeout': '超时'
  }
  return texts[status] || status
}

// 获取状态图标
export function getStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    'uploading': '⏳',
    'pending': '🔄',
    'parsing': '⚙️',
    'ready': '✅',
    'error': '❌',
    'timeout': '⚠️'
  }
  return icons[status] || '📄'
}

// 判断是否需要转圈动画
export function isSpinningStatus(status: string): boolean {
  return ['uploading', 'pending', 'parsing'].includes(status)
}

// 获取阶段图标
export function getStageIcon(stage: string): string {
  const icons: Record<string, string> = {
    'start': '🚀',
    'researcher': '🔍',
    'planner': '📋',
    'writer': '✍️',
    'questioner': '❓',
    'deepen_content': '📚',
    'coder': '💻',
    'artist': '🎨',
    'reviewer': '✅',
    'revision': '🔄',
    'assembler': '📦',
    'generator': '⚙️',
    'search_service': '🌐',
    'blog_service': '🖼️'
  }
  return icons[stage] || '⚙️'
}

// 解析 Cookie 字符串
export function parseCookies(cookieText: string): Array<{ name: string; value: string; domain: string; path: string }> {
  // 尝试 JSON 格式
  try {
    const parsed = JSON.parse(cookieText)
    if (Array.isArray(parsed)) return parsed
  } catch (e) {
    // 忽略
  }
  
  // 解析浏览器原始 Cookie 字符串格式: "name1=value1; name2=value2"
  const cookies: Array<{ name: string; value: string; domain: string; path: string }> = []
  const pairs = cookieText.split(';')
  for (const pair of pairs) {
    const trimmed = pair.trim()
    if (!trimmed) continue
    const eqIndex = trimmed.indexOf('=')
    if (eqIndex > 0) {
      cookies.push({
        name: trimmed.substring(0, eqIndex).trim(),
        value: trimmed.substring(eqIndex + 1).trim(),
        domain: '.xiaohongshu.com',
        path: '/'
      })
    }
  }
  return cookies
}

// 转义 HTML
export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// 格式化时间
export function formatTime(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

// 下载文件
export function downloadFile(url: string, filename: string): void {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// 复制到剪贴板
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (e) {
    console.error('复制失败:', e)
    return false
  }
}
