/**
 * useExport — 多格式导出 composable
 * 支持 Markdown / HTML / 纯文本 / Word 导出
 */
import { ref, readonly } from 'vue'

export type ExportFormat = 'markdown' | 'html' | 'txt' | 'word'

export function useExport() {
  const isDownloading = ref(false)

  /**
   * 触发浏览器下载
   */
  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  /**
   * 生成安全文件名
   */
  function safeFilename(title: string): string {
    return title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').substring(0, 50)
  }

  /**
   * 导出 Markdown
   */
  function exportMarkdown(content: string, title: string) {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    triggerDownload(blob, `${safeFilename(title)}.md`)
  }

  /**
   * 导出 HTML（内联基础样式）
   */
  function exportHtml(content: string, title: string) {
    // 简单的 markdown → html 转换（基于正则，不依赖外部库）
    let html = content
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')

    const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.8; color: #333; }
  h1, h2, h3 { color: #1a1a1a; margin-top: 1.5em; }
  code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
  pre { background: #f4f4f4; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  img { max-width: 100%; border-radius: 8px; }
  a { color: #0066cc; }
</style>
</head>
<body>
<p>${html}</p>
</body>
</html>`

    const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' })
    triggerDownload(blob, `${safeFilename(title)}.html`)
  }

  /**
   * 导出纯文本
   */
  function exportTxt(content: string, title: string) {
    // 去除 markdown 标记
    const plain = content
      .replace(/^#{1,6}\s/gm, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/```[\s\S]*?```/g, '')
      .replace(/!\[.*?\]\(.*?\)/g, '')
      .replace(/\[([^\]]+)\]\(.*?\)/g, '$1')

    const blob = new Blob([plain], { type: 'text/plain;charset=utf-8' })
    triggerDownload(blob, `${safeFilename(title)}.txt`)
  }

  /**
   * 导出 Word（通过后端 API）
   */
  async function exportWord(content: string, title: string) {
    const response = await fetch('/api/export/word', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: content, title }),
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: '导出失败' }))
      throw new Error(err.error || '导出失败')
    }

    const blob = await response.blob()
    triggerDownload(blob, `${safeFilename(title)}.docx`)
  }

  /**
   * 统一导出入口
   */
  async function exportAs(format: ExportFormat, content: string, title: string) {
    if (!content || isDownloading.value) return
    isDownloading.value = true

    try {
      switch (format) {
        case 'markdown':
          exportMarkdown(content, title)
          break
        case 'html':
          exportHtml(content, title)
          break
        case 'txt':
          exportTxt(content, title)
          break
        case 'word':
          await exportWord(content, title)
          break
      }
    } finally {
      isDownloading.value = false
    }
  }

  return {
    isDownloading: readonly(isDownloading),
    exportAs,
    exportMarkdown,
    exportHtml,
    exportTxt,
    exportWord,
  }
}
