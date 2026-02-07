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
  text = text.replace(/\n*---\n*/g, '\n\n---\n\n')
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
