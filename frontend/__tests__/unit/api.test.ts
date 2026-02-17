import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import {
  createBlogTask,
  createMiniBlogTask,
  createStorybookTask,
  cancelTask,
  confirmOutline,
  getHistory,
  getHistoryRecord,
  deleteHistory,
  uploadDocument,
  getDocumentStatus,
  getFrontendConfig,
  getImageStyles,
  getBooks,
  regenerateBooks,
  getBook,
  getChapterContent,
  createXhsTask,
  cancelXhsTask,
  publishToXhs,
  generateExplanationVideo,
  createReviewTask,
  getReviewList,
  getReviewDetail,
} from '@/services/api'

// Mock API responses
const mockTaskResponse = { success: true, task_id: 'task-123' }
const mockHistoryResponse = {
  success: true,
  records: [
    {
      id: 'blog-1',
      topic: 'Test Blog',
      content_type: 'blog',
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
  total_pages: 1,
}
const mockHistoryRecordResponse = {
  success: true,
  record: {
    id: 'blog-1',
    topic: 'Test Blog',
    content_type: 'blog',
    created_at: '2024-01-01T00:00:00Z',
  },
}
const mockUploadResponse = {
  success: true,
  document_id: 'doc-123',
  filename: 'test.pdf',
  status: 'pending',
}
const mockDocumentStatusResponse = {
  success: true,
  status: 'ready',
  markdown_length: 1000,
}
const mockConfigResponse = {
  success: true,
  config: {
    features: {
      reviewer: true,
      xhs_tab: true,
      cover_video: true,
    },
  },
}
const mockImageStylesResponse = {
  success: true,
  styles: [
    { value: 'realistic', label: '写实风格' },
    { value: 'cartoon', label: '卡通风格' },
  ],
}
const mockBooksResponse = {
  success: true,
  books: [
    { id: 'book-1', title: 'Test Book', chapters_count: 5 },
  ],
}
const mockBookDetailResponse = {
  success: true,
  book: { id: 'book-1', title: 'Test Book' },
  chapters: [{ path: 'chapter1.md', title: 'Chapter 1' }],
}
const mockChapterContentResponse = {
  success: true,
  content: '# Chapter 1\n\nContent here',
}

// Setup MSW server
const server = setupServer(
  // Blog API
  http.post('/api/blog/generate', () => HttpResponse.json(mockTaskResponse)),
  http.post('/api/blog/generate/mini', () => HttpResponse.json(mockTaskResponse)),
  http.post('/api/generate', () => HttpResponse.json(mockTaskResponse)),
  http.post('/api/tasks/:taskId/cancel', () => HttpResponse.json({ success: true })),
  http.post('/api/tasks/:taskId/confirm-outline', () => HttpResponse.json({ success: true })),
  http.post('/api/tasks/:taskId/resume', () => HttpResponse.json({ success: true })),
  http.get('/api/history', () => HttpResponse.json(mockHistoryResponse)),
  http.get('/api/history/:id', () => HttpResponse.json(mockHistoryRecordResponse)),
  http.delete('/api/history/:id', () => HttpResponse.json({ success: true })),

  // Document API
  http.post('/api/blog/upload', () => HttpResponse.json(mockUploadResponse)),
  http.get('/api/blog/upload/:docId/status', () => HttpResponse.json(mockDocumentStatusResponse)),

  // Config API
  http.get('/api/config', () => HttpResponse.json(mockConfigResponse)),
  http.get('/api/image-styles', () => HttpResponse.json(mockImageStylesResponse)),

  // Books API
  http.get('/api/books', () => HttpResponse.json(mockBooksResponse)),
  http.post('/api/books/regenerate', () => HttpResponse.json({ success: true })),
  http.get('/api/books/:bookId', () => HttpResponse.json(mockBookDetailResponse)),
  http.get('/api/books/:bookId/chapters/:chapterPath', () => HttpResponse.json(mockChapterContentResponse)),

  // XHS API
  http.post('/api/xhs/generate', () => HttpResponse.json(mockTaskResponse)),
  http.post('/api/xhs/tasks/:taskId/cancel', () => HttpResponse.json({ success: true })),
  http.post('/api/xhs/publish', () => HttpResponse.json({ success: true, url: 'https://xiaohongshu.com/123' })),
  http.post('/api/xhs/explanation-video', () => HttpResponse.json({ success: true, video_url: 'https://example.com/video.mp4' })),

  // Reviewer API
  http.post('/api/reviewer/evaluate', () => HttpResponse.json(mockTaskResponse)),
  http.get('/api/reviewer/list', () => HttpResponse.json({ success: true, reviews: [] })),
  http.get('/api/reviewer/:reviewId', () => HttpResponse.json({ success: true, review: {} })),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('api.ts', () => {
  describe('Blog API', () => {
    it('should create blog task', async () => {
      const result = await createBlogTask({ topic: 'Test Topic' })
      expect(result.success).toBe(true)
      expect(result.task_id).toBe('task-123')
    })

    it('should create mini blog task', async () => {
      const result = await createMiniBlogTask({ topic: 'Test Topic' })
      expect(result.success).toBe(true)
      expect(result.task_id).toBe('task-123')
    })

    it('should create storybook task', async () => {
      const result = await createStorybookTask({
        content: 'Test content',
        page_count: 10,
        target_audience: 'children',
        style: 'cartoon',
        generate_images: true,
      })
      expect(result.success).toBe(true)
      expect(result.task_id).toBe('task-123')
    })

    it('should cancel task', async () => {
      const result = await cancelTask('task-123')
      expect(result.success).toBe(true)
    })

    it('should get history with pagination', async () => {
      const result = await getHistory({ page: 1, page_size: 10 })
      expect(result.success).toBe(true)
      expect(result.records).toHaveLength(1)
      expect(result.total).toBe(1)
    })

    it('should get history with content type filter', async () => {
      const result = await getHistory({ content_type: 'blog' })
      expect(result.success).toBe(true)
    })

    it('should not include content_type in query when set to "all"', async () => {
      const result = await getHistory({ content_type: 'all' })
      expect(result.success).toBe(true)
    })

    it('should get single history record', async () => {
      const result = await getHistoryRecord('blog-1')
      expect(result.success).toBe(true)
      expect(result.record?.id).toBe('blog-1')
    })

    it('should delete history record', async () => {
      const result = await deleteHistory('blog-1')
      expect(result.success).toBe(true)
    })

    it('should confirm outline with accept action', async () => {
      const result = await confirmOutline('task-123', 'accept')
      expect(result.success).toBe(true)
    })

    it('should confirm outline with edit action', async () => {
      const result = await confirmOutline('task-123', 'edit')
      expect(result.success).toBe(true)
    })

    it('should pass interactive parameter in createBlogTask', async () => {
      let capturedBody: any = null
      server.use(
        http.post('/api/blog/generate', async ({ request }) => {
          capturedBody = await request.json()
          return HttpResponse.json(mockTaskResponse)
        })
      )

      await createBlogTask({ topic: 'Test', interactive: true })
      expect(capturedBody).toBeTruthy()
      expect(capturedBody.interactive).toBe(true)
    })
  })

  describe('Document API', () => {
    it('should upload document', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      const result = await uploadDocument(file)
      expect(result.success).toBe(true)
      expect(result.document_id).toBe('doc-123')
      expect(result.filename).toBe('test.pdf')
    })

    it('should get document status', async () => {
      const result = await getDocumentStatus('doc-123')
      expect(result.success).toBe(true)
      expect(result.status).toBe('ready')
      expect(result.markdown_length).toBe(1000)
    })
  })

  describe('Config API', () => {
    it('should get frontend config', async () => {
      const result = await getFrontendConfig()
      expect(result.success).toBe(true)
      expect(result.config?.features.reviewer).toBe(true)
    })

    it('should get image styles', async () => {
      const result = await getImageStyles()
      expect(result.success).toBe(true)
      expect(result.styles).toHaveLength(2)
      expect(result.styles?.[0].value).toBe('realistic')
    })
  })

  describe('Books API', () => {
    it('should get books list', async () => {
      const result = await getBooks()
      expect(result.success).toBe(true)
      expect(result.books).toHaveLength(1)
      expect(result.books?.[0].id).toBe('book-1')
    })

    it('should regenerate books', async () => {
      const result = await regenerateBooks()
      expect(result.success).toBe(true)
    })

    it('should get book detail', async () => {
      const result = await getBook('book-1')
      expect(result.success).toBe(true)
      expect(result.book?.id).toBe('book-1')
      expect(result.chapters).toHaveLength(1)
    })

    it('should get chapter content', async () => {
      const result = await getChapterContent('book-1', 'chapter1.md')
      expect(result.success).toBe(true)
      expect(result.content).toContain('# Chapter 1')
    })

    it('should encode chapter path in URL', async () => {
      const result = await getChapterContent('book-1', 'chapter with spaces.md')
      expect(result.success).toBe(true)
    })
  })

  describe('XHS API', () => {
    it('should create XHS task', async () => {
      const result = await createXhsTask({
        topic: 'Test Topic',
        count: 5,
        style: 'cartoon',
        generate_video: false,
      })
      expect(result.success).toBe(true)
      expect(result.task_id).toBe('task-123')
    })

    it('should cancel XHS task', async () => {
      const result = await cancelXhsTask('task-123')
      expect(result.success).toBe(true)
    })

    it('should publish to XHS', async () => {
      const result = await publishToXhs({
        cookies: [],
        title: 'Test Title',
        content: 'Test Content',
        tags: ['tag1', 'tag2'],
        images: ['image1.jpg', 'image2.jpg'],
      })
      expect(result.success).toBe(true)
      expect(result.url).toBe('https://xiaohongshu.com/123')
    })

    it('should generate explanation video', async () => {
      const result = await generateExplanationVideo({
        images: ['image1.jpg', 'image2.jpg'],
        scripts: ['script1', 'script2'],
        style: 'professional',
        target_duration: 60,
        video_model: 'runway',
      })
      expect(result.success).toBe(true)
      expect(result.video_url).toBe('https://example.com/video.mp4')
    })
  })

  describe('Reviewer API', () => {
    it('should create review task', async () => {
      const result = await createReviewTask({
        git_url: 'https://github.com/user/repo',
        enable_search: true,
      })
      expect(result.success).toBe(true)
      expect(result.task_id).toBe('task-123')
    })

    it('should get review list', async () => {
      const result = await getReviewList()
      expect(result.success).toBe(true)
      expect(result.reviews).toBeDefined()
    })

    it('should get review detail', async () => {
      const result = await getReviewDetail('review-123')
      expect(result.success).toBe(true)
      expect(result.review).toBeDefined()
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors', async () => {
      server.use(
        http.post('/api/blog/generate', () => {
          return HttpResponse.json({ success: false, error: 'API Error' }, { status: 500 })
        })
      )

      const result = await createBlogTask({ topic: 'Test' })
      expect(result.success).toBe(false)
      expect(result.error).toBe('API Error')
    })

    it('should handle network errors', async () => {
      server.use(
        http.get('/api/history', () => {
          return HttpResponse.error()
        })
      )

      await expect(getHistory({})).rejects.toThrow()
    })
  })
})
