import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useBlogDetail } from '@/composables/useBlogDetail'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

const mockHistoryRecord = {
  success: true,
  record: {
    id: 'blog-123',
    topic: 'Test Blog Topic',
    content_type: 'blog',
    article_type: 'medium',
    markdown_content: '# Test Title\n\nThis is test content with ![image](test.jpg) and ```code```',
    outline: JSON.stringify({
      title: 'Test Title',
      summary: 'Test summary',
      keywords: ['test', 'blog'],
      sections: [{ title: 'Section 1' }, { title: 'Section 2' }],
    }),
    sections_count: 2,
    images_count: 1,
    code_blocks_count: 1,
    cover_video: 'https://example.com/video.mp4',
    created_at: '2024-01-01T00:00:00Z',
  },
}

const server = setupServer(
  http.get('/api/history/:id', () => HttpResponse.json(mockHistoryRecord))
)

beforeEach(() => {
  server.listen()
  vi.useFakeTimers()
  mockPush.mockClear()
})

afterEach(() => {
  server.resetHandlers()
  server.close()
  vi.useRealTimers()
})

describe('useBlogDetail', () => {
  describe('showToast', () => {
    it('should show toast with message', () => {
      const { toast, showToast } = useBlogDetail()

      showToast('Test message', 'success')

      expect(toast.value.show).toBe(true)
      expect(toast.value.message).toBe('Test message')
      expect(toast.value.type).toBe('success')
    })

    it('should hide toast after 3 seconds', () => {
      const { toast, showToast } = useBlogDetail()

      showToast('Test message')
      expect(toast.value.show).toBe(true)

      vi.advanceTimersByTime(3000)
      expect(toast.value.show).toBe(false)
    })

    it('should default to info type', () => {
      const { toast, showToast } = useBlogDetail()

      showToast('Test message')
      expect(toast.value.type).toBe('info')
    })
  })

  describe('formatDate', () => {
    it('should format date correctly', () => {
      const { formatDate } = useBlogDetail()

      const result = formatDate('2024-01-01T00:00:00Z')
      expect(result).toContain('2024')
      expect(result).toContain('1')
    })

    it('should return N/A for undefined date', () => {
      const { formatDate } = useBlogDetail()

      expect(formatDate(undefined)).toBe('N/A')
      expect(formatDate('')).toBe('N/A')
    })
  })

  describe('formatWordCount', () => {
    it('should format small counts', () => {
      const { formatWordCount } = useBlogDetail()

      expect(formatWordCount(500)).toBe('500 字')
      expect(formatWordCount(999)).toBe('999 字')
    })

    it('should format thousands', () => {
      const { formatWordCount } = useBlogDetail()

      expect(formatWordCount(1000)).toBe('1.0 千字')
      expect(formatWordCount(5500)).toBe('5.5 千字')
    })

    it('should format ten thousands', () => {
      const { formatWordCount } = useBlogDetail()

      expect(formatWordCount(10000)).toBe('1.0 万字')
      expect(formatWordCount(25000)).toBe('2.5 万字')
    })
  })

  describe('toggleFavorite', () => {
    it('should toggle favorite state', () => {
      const { isFavorite, toggleFavorite } = useBlogDetail()

      expect(isFavorite.value).toBe(false)
      toggleFavorite()
      expect(isFavorite.value).toBe(true)
      toggleFavorite()
      expect(isFavorite.value).toBe(false)
    })

    it('should show toast when favoriting', () => {
      const { toast, toggleFavorite } = useBlogDetail()

      toggleFavorite()
      expect(toast.value.message).toBe('已添加到收藏')
      expect(toast.value.type).toBe('success')
    })

    it('should show toast when unfavoriting', () => {
      const { toast, toggleFavorite } = useBlogDetail()

      toggleFavorite() // favorite
      toggleFavorite() // unfavorite
      expect(toast.value.message).toBe('已取消收藏')
      expect(toast.value.type).toBe('success')
    })
  })

  describe('loadBlog', () => {
    it('should load blog successfully', async () => {
      const { blog, isLoading, loadBlog } = useBlogDetail()

      await loadBlog('blog-123')

      expect(isLoading.value).toBe(false)
      expect(blog.value).not.toBeNull()
      expect(blog.value?.id).toBe('blog-123')
      expect(blog.value?.title).toBe('Test Title')
      expect(blog.value?.description).toBe('Test summary')
      expect(blog.value?.tags).toEqual(['test', 'blog'])
    })

    it('should extract title from markdown if not in outline', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({
            success: true,
            record: {
              ...mockHistoryRecord.record,
              outline: '{}',
              markdown_content: '# Markdown Title\n\nContent',
            },
          })
        })
      )

      const { blog, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(blog.value?.title).toBe('Markdown Title')
    })

    it('should use topic as fallback title', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({
            success: true,
            record: {
              ...mockHistoryRecord.record,
              outline: '{}',
              markdown_content: 'Content without title',
              topic: 'Fallback Topic',
            },
          })
        })
      )

      const { blog, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(blog.value?.title).toBe('Fallback Topic')
    })

    it('should truncate long topic titles', async () => {
      const longTopic = 'A'.repeat(60)
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({
            success: true,
            record: {
              ...mockHistoryRecord.record,
              outline: '{}',
              markdown_content: '',
              topic: longTopic,
            },
          })
        })
      )

      const { blog, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(blog.value?.title).toHaveLength(53) // 50 + '...'
      expect(blog.value?.title).toContain('...')
    })

    it('should count images from markdown', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({
            success: true,
            record: {
              ...mockHistoryRecord.record,
              markdown_content: '![img1](a.jpg) ![img2](b.jpg) ![img3](c.jpg)',
            },
          })
        })
      )

      const { blog, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(blog.value?.imagesCount).toBe(3)
    })

    it('should count code blocks from markdown', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({
            success: true,
            record: {
              ...mockHistoryRecord.record,
              markdown_content: '```js\ncode1\n```\n\n```py\ncode2\n```',
            },
          })
        })
      )

      const { blog, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(blog.value?.codeBlocksCount).toBe(2)
    })

    it('should map article types correctly', async () => {
      const testCases = [
        { type: 'mini', expected: 'Mini' },
        { type: 'short', expected: '短文' },
        { type: 'medium', expected: '中等' },
        { type: 'long', expected: '长文' },
        { type: 'custom', expected: '自定义' },
        { type: 'unknown', expected: 'unknown' },
      ]

      for (const { type, expected } of testCases) {
        server.use(
          http.get('/api/history/:id', () => {
            return HttpResponse.json({
              success: true,
              record: {
                ...mockHistoryRecord.record,
                article_type: type,
              },
            })
          })
        )

        const { blog, loadBlog } = useBlogDetail()
        await loadBlog('blog-123')

        expect(blog.value?.articleType).toBe(expected)
      }
    })

    it('should handle API error', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.json({ success: false, error: 'Not found' })
        })
      )

      const { toast, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(toast.value.message).toContain('加载失败')
      expect(toast.value.type).toBe('error')
      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('should handle network error', async () => {
      server.use(
        http.get('/api/history/:id', () => {
          return HttpResponse.error()
        })
      )

      const { toast, loadBlog } = useBlogDetail()
      await loadBlog('blog-123')

      expect(toast.value.message).toContain('加载失败')
      expect(toast.value.type).toBe('error')
      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('should set loading state correctly', async () => {
      const { isLoading, loadBlog } = useBlogDetail()

      expect(isLoading.value).toBe(true)

      const loadPromise = loadBlog('blog-123')
      expect(isLoading.value).toBe(true)

      await loadPromise
      expect(isLoading.value).toBe(false)
    })
  })
})
