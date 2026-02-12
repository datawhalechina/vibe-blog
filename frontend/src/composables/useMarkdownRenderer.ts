import { computed } from 'vue'
import { marked } from 'marked'

/**
 * Markdown 渲染 Composable
 *
 * 功能：
 * - 将 Markdown 内容转换为 HTML
 * - 配置 marked 选项
 */
/**
 * 修复 Markdown 分隔线格式：确保 --- 前后都有空行
 * 防止 Setext 标题误判（文本紧挨 --- 会被渲染为加粗标题）和 ---## 连写
 */
function fixMarkdownSeparators(text: string): string {
  const lines = text.split('\n')
  const result: string[] = []
  let inCodeBlock = false

  for (const line of lines) {
    const stripped = line.trim()
    if (stripped.startsWith('```')) {
      inCodeBlock = !inCodeBlock
      result.push(line)
      continue
    }
    if (!inCodeBlock) {
      if (stripped === '---') {
        // 独立的 --- 行
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('')
        }
        result.push('---')
        result.push('')
      } else if (stripped.startsWith('---') && stripped.length > 3 && stripped[3] !== '-') {
        // ---## 连写：拆分 --- 和后续内容
        const rest = stripped.slice(3).trimStart()
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('')
        }
        result.push('---')
        result.push('')
        result.push(rest)
      } else {
        result.push(line)
      }
    } else {
      result.push(line)
    }
  }

  text = result.join('\n')
  text = text.replace(/\n{3,}/g, '\n\n')
  return text
}

export function useMarkdownRenderer(content: string) {
  /**
   * 渲染后的 HTML 内容
   */
  const renderedContent = computed(() => {
    if (!content) return ''
    const fixed = fixMarkdownSeparators(content)
    return marked(fixed)
  })

  return {
    renderedContent
  }
}
