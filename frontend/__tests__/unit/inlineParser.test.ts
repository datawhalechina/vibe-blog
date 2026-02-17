/**
 * 101.09 parseInlineMarkdown 测试
 */
import { describe, it, expect } from 'vitest'
import { parseInlineMarkdown } from '@/composables/useExport'

describe('parseInlineMarkdown', () => {
  it('should strip bold markers', () => {
    expect(parseInlineMarkdown('This is **bold** text')).toBe('This is bold text')
  })

  it('should strip italic markers', () => {
    expect(parseInlineMarkdown('This is *italic* text')).toBe('This is italic text')
  })

  it('should strip inline code markers', () => {
    expect(parseInlineMarkdown('Use `console.log` here')).toBe('Use console.log here')
  })

  it('should convert links to plain text', () => {
    expect(parseInlineMarkdown('Visit [Google](https://google.com) now')).toBe('Visit Google now')
  })
})
