/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * 将 Markdown 文本转换为 BlockNote Blocks
 * 支持常见的 Markdown 语法
 */
export function markdownToBlocks(markdown: string): any[] {
  return markdownToBlocksSimple(markdown)
}

/**
 * 简化版 Markdown 解析（作为降级方案）
 */
function markdownToBlocksSimple(markdown: string): any[] {
  const lines = markdown.split('\n')
  const blocks: any[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmedLine = line.trim()

    // 跳过空行
    if (!trimmedLine) {
      i++
      continue
    }

    // 标题
    const headingMatch = trimmedLine.match(/^(#{1,3})\s+(.+)$/)
    if (headingMatch) {
      const level = headingMatch[1].length as 1 | 2 | 3
      blocks.push({
        id: generateId(),
        type: 'heading',
        props: { level, textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
        content: parseInlineContent(headingMatch[2]),
        children: [],
      })
      i++
      continue
    }

    // 代码块
    if (trimmedLine.startsWith('```')) {
      const language = trimmedLine.slice(3).trim() || 'plaintext'
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      blocks.push({
        id: generateId(),
        type: 'codeBlock',
        props: { language },
        content: [{ type: 'text', text: codeLines.join('\n'), styles: {} }],
        children: [],
      })
      i++ // 跳过结束的 ```
      continue
    }

    // 无序列表
    if (trimmedLine.match(/^[-*+]\s+/)) {
      const text = trimmedLine.replace(/^[-*+]\s+/, '')
      blocks.push({
        id: generateId(),
        type: 'bulletListItem',
        props: { textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
        content: parseInlineContent(text),
        children: [],
      })
      i++
      continue
    }

    // 有序列表
    if (trimmedLine.match(/^\d+\.\s+/)) {
      const text = trimmedLine.replace(/^\d+\.\s+/, '')
      blocks.push({
        id: generateId(),
        type: 'numberedListItem',
        props: { textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
        content: parseInlineContent(text),
        children: [],
      })
      i++
      continue
    }

    // 引用
    if (trimmedLine.startsWith('>')) {
      const text = trimmedLine.replace(/^>\s*/, '')
      blocks.push({
        id: generateId(),
        type: 'paragraph',
        props: { textColor: 'default', backgroundColor: 'gray', textAlignment: 'left' },
        content: parseInlineContent(text),
        children: [],
      })
      i++
      continue
    }

    // 图片
    const imageMatch = trimmedLine.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)
    if (imageMatch) {
      blocks.push({
        id: generateId(),
        type: 'image',
        props: {
          url: imageMatch[2],
          caption: imageMatch[1] || '',
          width: 512,
        },
        children: [],
      })
      i++
      continue
    }

    // 分隔线
    if (trimmedLine.match(/^[-*_]{3,}$/)) {
      i++
      continue
    }

    // 普通段落
    blocks.push({
      id: generateId(),
      type: 'paragraph',
      props: { textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
      content: parseInlineContent(trimmedLine),
      children: [],
    })
    i++
  }

  return blocks
}

/**
 * 解析行内内容（粗体、斜体、代码、链接等）
 */
function parseInlineContent(text: string): Array<{ type: 'text'; text: string; styles: Record<string, boolean | string> }> {
  const result: Array<{ type: 'text'; text: string; styles: Record<string, boolean | string> }> = []
  
  // 解析行内样式
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\))/g
  let lastIndex = 0
  let match
  
  while ((match = regex.exec(text)) !== null) {
    // 添加匹配前的普通文本
    if (match.index > lastIndex) {
      result.push({ type: 'text', text: text.slice(lastIndex, match.index), styles: {} })
    }
    
    if (match[2]) {
      // 粗体 **text**
      result.push({ type: 'text', text: match[2], styles: { bold: true } })
    } else if (match[3]) {
      // 斜体 *text*
      result.push({ type: 'text', text: match[3], styles: { italic: true } })
    } else if (match[4]) {
      // 行内代码 `code`
      result.push({ type: 'text', text: match[4], styles: { code: true } })
    } else if (match[5] && match[6]) {
      // 链接 [text](url)
      result.push({ type: 'link', text: match[5], href: match[6], styles: {} } as any)
    }
    
    lastIndex = match.index + match[0].length
  }
  
  // 添加剩余文本
  if (lastIndex < text.length) {
    result.push({ type: 'text', text: text.slice(lastIndex), styles: {} })
  }
  
  // 如果没有任何匹配，返回原始文本
  if (result.length === 0 && text) {
    result.push({ type: 'text', text, styles: {} })
  }
  
  return result
}

/**
 * 生成唯一 ID
 */
function generateId(): string {
  return Math.random().toString(36).substring(2, 10)
}

/**
 * 将 BlockNote Blocks 转换为 Markdown
 */
export function blocksToMarkdown(blocks: any[]): string {
  const lines: string[] = []

  for (const block of blocks) {
    const text = getBlockText(block)

    switch (block.type) {
      case 'heading':
        const level = (block.props as { level?: number })?.level || 1
        lines.push(`${'#'.repeat(level)} ${text}`)
        break

      case 'bulletListItem':
        lines.push(`- ${text}`)
        break

      case 'numberedListItem':
        lines.push(`1. ${text}`)
        break

      case 'codeBlock':
        const language = (block.props as { language?: string })?.language || ''
        lines.push(`\`\`\`${language}`)
        lines.push(text)
        lines.push('```')
        break

      case 'image':
        const url = (block.props as { url?: string })?.url || ''
        const caption = (block.props as { caption?: string })?.caption || ''
        lines.push(`![${caption}](${url})`)
        break

      case 'paragraph':
      default:
        if (text) {
          lines.push(text)
        }
        break
    }

    lines.push('') // 段落间空行
  }

  return lines.join('\n')
}

/**
 * 获取 Block 的文本内容
 */
function getBlockText(block: any): string {
  if (!block.content) return ''
  
  if (Array.isArray(block.content)) {
    return block.content
      .filter((item: any) => item.type === 'text')
      .map((item: any) => item.text)
      .join('')
  }
  
  return ''
}
