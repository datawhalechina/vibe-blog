import { vi } from 'vitest'

// Mock API responses
export const mockBlogResponse = {
  task_id: 'test-task-123',
  status: 'processing',
}

export const mockBlogDetailResponse = {
  id: 'blog-123',
  title: 'Test Blog Title',
  content: '# Test Content\n\nThis is a test blog.',
  cover_image: 'https://example.com/cover.jpg',
  cover_video: 'https://example.com/cover.mp4',
  word_count: 1500,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockHistoryResponse = {
  items: [
    {
      id: 'blog-1',
      title: 'Blog 1',
      cover_image: 'https://example.com/1.jpg',
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'blog-2',
      title: 'Blog 2',
      cover_image: 'https://example.com/2.jpg',
      created_at: '2024-01-02T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
}

export const mockConfigResponse = {
  llm_provider: 'openai',
  llm_model: 'gpt-4',
  image_provider: 'dalle',
  video_provider: 'runway',
  max_revisions: 3,
}

// Mock API functions
export const mockApi = {
  generateBlog: vi.fn().mockResolvedValue(mockBlogResponse),
  getBlogDetail: vi.fn().mockResolvedValue(mockBlogDetailResponse),
  getHistory: vi.fn().mockResolvedValue(mockHistoryResponse),
  deleteBlog: vi.fn().mockResolvedValue({ success: true }),
  getConfig: vi.fn().mockResolvedValue(mockConfigResponse),
  updateConfig: vi.fn().mockResolvedValue(mockConfigResponse),
  publishToWeChat: vi.fn().mockResolvedValue({ success: true, url: 'https://mp.weixin.qq.com/123' }),
  publishToXHS: vi.fn().mockResolvedValue({ success: true, url: 'https://xiaohongshu.com/123' }),
}
