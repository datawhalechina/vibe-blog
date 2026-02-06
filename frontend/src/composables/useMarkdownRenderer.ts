import { computed } from 'vue'
import { marked } from 'marked'

/**
 * Markdown 渲染 Composable
 *
 * 功能：
 * - 将 Markdown 内容转换为 HTML
 * - 配置 marked 选项
 */
export function useMarkdownRenderer(content: string) {
  /**
   * 渲染后的 HTML 内容
   */
  const renderedContent = computed(() => {
    if (!content) return ''
    return marked(content)
  })

  return {
    renderedContent
  }
}
