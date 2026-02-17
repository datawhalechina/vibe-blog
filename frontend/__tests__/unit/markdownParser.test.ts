/**
 * 101.09 parseMarkdownToParagraphs 测试
 */
import { describe, it, expect } from 'vitest'
import { parseMarkdownToParagraphs } from '@/composables/useExport'

describe('parseMarkdownToParagraphs', () => {
  it('should parse h1 headings', () => {
    const result = parseMarkdownToParagraphs('# Hello World')
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ type: 'h1', text: 'Hello World' })
  })

  it('should parse h2 headings', () => {
    const result = parseMarkdownToParagraphs('## Section Title')
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ type: 'h2', text: 'Section Title' })
  })

  it('should parse h3 headings', () => {
    const result = parseMarkdownToParagraphs('### Sub Section')
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ type: 'h3', text: 'Sub Section' })
  })

  it('should parse unordered list items', () => {
    const result = parseMarkdownToParagraphs('- Item one\n* Item two')
    expect(result).toHaveLength(2)
    expect(result[0]).toEqual({ type: 'list', text: '• Item one' })
    expect(result[1]).toEqual({ type: 'list', text: '• Item two' })
  })

  it('should skip empty lines and parse paragraphs', () => {
    const md = '# Title\n\nSome text\n\n- List item'
    const result = parseMarkdownToParagraphs(md)
    expect(result).toHaveLength(3)
    expect(result[0].type).toBe('h1')
    expect(result[1].type).toBe('paragraph')
    expect(result[2].type).toBe('list')
  })
})
