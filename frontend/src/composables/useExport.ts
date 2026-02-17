/**
 * useExport — 多格式导出 composable
 * 支持 Markdown / HTML / 纯文本 / Word 导出
 */
import { ref, readonly } from 'vue'

export type ExportFormat = 'markdown' | 'html' | 'txt' | 'word' | 'pdf' | 'image'

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
   * 导出 PDF（动态加载 jspdf）
   */
  async function exportPdf(content: string, title: string) {
    const paragraphs = parseMarkdownToParagraphs(content)
    const { jsPDF } = await import('jspdf')
    const doc = new jsPDF({ unit: 'mm', format: 'a4' })

    // 尝试加载中文字体，失败则用默认字体
    try {
      doc.setFont('helvetica')
    } catch {
      // fallback
    }

    let y = 20
    const pageHeight = 280
    const lineHeight = 7
    const margin = 15
    const maxWidth = 180

    for (const p of paragraphs) {
      let fontSize = 11
      if (p.type === 'h1') fontSize = 18
      else if (p.type === 'h2') fontSize = 15
      else if (p.type === 'h3') fontSize = 13
      else if (p.type === 'list') fontSize = 11

      doc.setFontSize(fontSize)
      const lines = doc.splitTextToSize(p.text, maxWidth)

      for (const line of lines) {
        if (y > pageHeight) {
          doc.addPage()
          y = 20
        }
        doc.text(line, margin, y)
        y += lineHeight
      }
      y += 2 // paragraph spacing
    }

    doc.save(`${safeFilename(title)}.pdf`)
  }

  /**
   * 导出图片（动态加载 html2canvas）
   */
  async function exportImage(elementId: string, title: string) {
    const element = document.getElementById(elementId)
    if (!element) throw new Error(`Element #${elementId} not found`)

    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      windowHeight: element.scrollHeight,
    })

    canvas.toBlob((blob: Blob | null) => {
      if (blob) triggerDownload(blob, `${safeFilename(title)}.png`)
    }, 'image/png')
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
        case 'pdf':
          await exportPdf(content, title)
          break
        case 'image':
          await exportImage('preview-content', title)
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
    exportPdf,
    exportImage,
  }
}

/**
 * Markdown → 段落数组（供 PDF 导出使用）
 */
export interface MarkdownParagraph {
  type: 'h1' | 'h2' | 'h3' | 'list' | 'paragraph'
  text: string
}

export function parseMarkdownToParagraphs(markdown: string): MarkdownParagraph[] {
  const lines = markdown.split('\n')
  const result: MarkdownParagraph[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (trimmed.startsWith('### ')) {
      result.push({ type: 'h3', text: trimmed.slice(4) })
    } else if (trimmed.startsWith('## ')) {
      result.push({ type: 'h2', text: trimmed.slice(3) })
    } else if (trimmed.startsWith('# ')) {
      result.push({ type: 'h1', text: trimmed.slice(2) })
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      result.push({ type: 'list', text: `• ${trimmed.slice(2)}` })
    } else {
      result.push({ type: 'paragraph', text: parseInlineMarkdown(trimmed) })
    }
  }

  return result
}

/**
 * 解析 Markdown 内联标记为纯文本
 */
export function parseInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')       // **粗体**
    .replace(/\*(.*?)\*/g, '$1')           // *斜体*
    .replace(/`([^`]+)`/g, '$1')           // `行内代码`
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [链接](url)
}
