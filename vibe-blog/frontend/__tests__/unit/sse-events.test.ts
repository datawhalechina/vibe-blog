/**
 * 101.03 SSE 事件解析测试
 * 验证前端对各种 SSE 事件数据的解析和处理
 */
import { describe, it, expect } from 'vitest'

// 模拟 SSE 事件数据解析逻辑（从 useTaskStream 中提取的核心逻辑）
function parseResultEvent(data: any): { type: string; message: string } {
  const eventData = data.data || {}

  switch (data.type) {
    case 'search_started':
      return { type: 'info', message: `🔍 搜索: ${eventData.query || ''}` }
    case 'search_results':
      return { type: 'search', message: `🔍 ${eventData.query || '搜索结果'}` }
    case 'crawl_completed':
      return { type: 'crawl', message: `📖 已抓取 ${eventData.count || 0} 篇` }
    case 'researcher_complete':
      return { type: 'info', message: `📊 知识来源: 文档 ${eventData.document_count} 条, 网络 ${eventData.web_count} 条` }
    case 'outline_complete':
      return { type: 'success', message: `📋 大纲: ${eventData.title}` }
    default:
      return { type: 'info', message: eventData.message || '' }
  }
}

describe('SSE event parsing', () => {
  it('should parse search_started event', () => {
    const result = parseResultEvent({
      type: 'search_started',
      data: { query: 'LangGraph tutorial', engine: 'zhipu' },
    })
    expect(result.type).toBe('info')
    expect(result.message).toContain('LangGraph tutorial')
  })

  it('should parse search_results event', () => {
    const result = parseResultEvent({
      type: 'search_results',
      data: {
        query: 'LangGraph',
        results: [
          { url: 'https://example.com', title: 'Example', snippet: 'test', domain: 'example.com' },
        ],
      },
    })
    expect(result.type).toBe('search')
    expect(result.message).toContain('LangGraph')
  })

  it('should parse crawl_completed event', () => {
    const result = parseResultEvent({
      type: 'crawl_completed',
      data: { count: 3 },
    })
    expect(result.type).toBe('crawl')
    expect(result.message).toContain('3')
  })

  it('should parse researcher_complete event', () => {
    const result = parseResultEvent({
      type: 'researcher_complete',
      data: { document_count: 2, web_count: 5 },
    })
    expect(result.type).toBe('info')
    expect(result.message).toContain('文档 2 条')
    expect(result.message).toContain('网络 5 条')
  })

  it('should parse outline_complete event', () => {
    const result = parseResultEvent({
      type: 'outline_complete',
      data: {
        title: '深入理解 LangGraph',
        sections_titles: ['概述', '核心概念', '实践'],
      },
    })
    expect(result.type).toBe('success')
    expect(result.message).toContain('深入理解 LangGraph')
  })
})
