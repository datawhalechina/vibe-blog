/**
 * 101.05 citationMatcher 测试
 */
import { describe, it, expect } from 'vitest'
import { matchCitation, scanCitationLinks } from '@/utils/citationMatcher'
import type { Citation } from '@/utils/citationMatcher'

const citations: Citation[] = [
  { url: 'https://example.com/article-1', title: 'Article 1', domain: 'example.com', snippet: 'First article' },
  { url: 'https://blog.dev/post/2', title: 'Post 2', domain: 'blog.dev', snippet: 'Second post', relevance: 0.9 },
]

describe('matchCitation', () => {
  it('should match exact URL', () => {
    const result = matchCitation('https://example.com/article-1', citations)
    expect(result).not.toBeNull()
    expect(result!.title).toBe('Article 1')
  })

  it('should match URL with decodeURIComponent normalization', () => {
    const result = matchCitation('https://example.com/article%2D1', citations)
    expect(result).not.toBeNull()
    expect(result!.title).toBe('Article 1')
  })

  it('should return null for unmatched URL', () => {
    const result = matchCitation('https://unknown.com/page', citations)
    expect(result).toBeNull()
  })

  it('should handle trailing slash normalization', () => {
    const result = matchCitation('https://example.com/article-1/', citations)
    expect(result).not.toBeNull()
    expect(result!.title).toBe('Article 1')
  })
})

describe('scanCitationLinks', () => {
  it('should return empty array for empty container', () => {
    const container = document.createElement('div')
    const result = scanCitationLinks(container, citations)
    expect(result).toHaveLength(0)
  })

  it('should match links in container', () => {
    const container = document.createElement('div')
    container.innerHTML = '<a href="https://example.com/article-1">Link</a><a href="https://other.com">Other</a>'
    const result = scanCitationLinks(container, citations)
    expect(result).toHaveLength(1)
    expect(result[0].citation.title).toBe('Article 1')
    expect(result[0].index).toBe(1)
  })
})
