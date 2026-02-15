// API 服务层 - 与后端 API 交互

const API_BASE = ''

// ========== 博客相关 API ==========

export interface BlogGenerateParams {
  topic: string
  article_type?: string
  target_length?: string
  target_audience?: string
  audience_adaptation?: string
  document_ids?: string[]
  image_style?: string
  generate_cover_video?: boolean
  video_aspect_ratio?: string
  deep_thinking?: boolean
  background_investigation?: boolean
  interactive?: boolean
  custom_config?: {
    sections_count?: number
    images_count?: number
    code_blocks_count?: number
    target_word_count?: number
  }
}

export interface HistoryRecord {
  id: string
  topic: string
  content_type: string
  created_at: string
  cover_image?: string
  cover_video?: string
  sections_count?: number
  images_count?: number
  book_id?: string
  book_title?: string
  xhs_image_urls?: string
  xhs_hashtags?: string
  xhs_copy_text?: string
}

export interface HistoryResponse {
  success: boolean
  records: HistoryRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 创建博客生成任务
export async function createBlogTask(params: BlogGenerateParams): Promise<{ success: boolean; task_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/blog/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 优化主题（Prompt 增强）
export async function enhanceTopic(topic: string): Promise<{ success: boolean; enhanced_topic?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/blog/enhance-topic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic })
  })
  return response.json()
}

// 恢复中断的任务（101.113 LangGraph interrupt 方案）
export async function resumeTask(taskId: string, action: 'accept' | 'edit' = 'accept', outline?: any): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/api/tasks/${taskId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, outline })
  })
  return response.json()
}

// 确认大纲（兼容旧接口，内部调用 resumeTask）
export async function confirmOutline(taskId: string, action: 'accept' | 'edit' = 'accept', outline?: any): Promise<{ success: boolean; error?: string }> {
  return resumeTask(taskId, action, outline)
}

// 评估文章质量
export async function evaluateArticle(blogId: string): Promise<{ success: boolean; evaluation?: any; error?: string }> {
  const response = await fetch(`${API_BASE}/api/blog/${blogId}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return response.json()
}

// 创建 Mini 博客生成任务
export async function createMiniBlogTask(params: BlogGenerateParams): Promise<{ success: boolean; task_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/blog/generate/mini`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 创建科普绘本生成任务
export async function createStorybookTask(params: {
  content: string
  page_count: number
  target_audience: string
  style: string
  generate_images: boolean
}): Promise<{ success: boolean; task_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 取消任务
export async function cancelTask(taskId: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/api/tasks/${taskId}/cancel`, {
    method: 'POST'
  })
  return response.json()
}

// 创建 SSE 连接
export function createTaskStream(taskId: string): EventSource {
  return new EventSource(`${API_BASE}/api/tasks/${taskId}/stream`)
}

// 获取历史记录
export async function getHistory(params: {
  page?: number
  page_size?: number
  content_type?: string
}): Promise<HistoryResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.content_type && params.content_type !== 'all') query.set('content_type', params.content_type)
  
  const response = await fetch(`${API_BASE}/api/history?${query}`)
  return response.json()
}

// 获取单条历史记录
export async function getHistoryRecord(id: string): Promise<{ success: boolean; record?: HistoryRecord; error?: string }> {
  const response = await fetch(`${API_BASE}/api/history/${id}`)
  return response.json()
}

// 删除历史记录
export async function deleteHistory(id: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/api/history/${id}`, {
    method: 'DELETE'
  })
  return response.json()
}

// ========== 文档上传 API ==========

export interface UploadResponse {
  success: boolean
  document_id?: string
  filename?: string
  status?: string
  error?: string
}

export interface DocumentStatus {
  success: boolean
  status?: string
  markdown_length?: number
  error_message?: string
}

// 上传知识文档
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE}/api/blog/upload`, {
    method: 'POST',
    body: formData
  })
  return response.json()
}

// 获取文档解析状态
export async function getDocumentStatus(docId: string): Promise<DocumentStatus> {
  const response = await fetch(`${API_BASE}/api/blog/upload/${docId}/status`)
  return response.json()
}

// ========== 配置 API ==========

export interface FrontendConfig {
  features: {
    reviewer?: boolean
    xhs_tab?: boolean
    cover_video?: boolean
  }
  image_styles?: Array<{ value: string; label: string }>
}

// 获取前端配置
export async function getFrontendConfig(): Promise<{ success: boolean; config?: FrontendConfig }> {
  const response = await fetch(`${API_BASE}/api/config`)
  return response.json()
}

// 获取配图风格列表
export async function getImageStyles(): Promise<{ success: boolean; styles?: Array<{ value: string; label: string }> }> {
  const response = await fetch(`${API_BASE}/api/image-styles`)
  return response.json()
}

// ========== 书籍 API ==========

export interface Book {
  id: string
  title: string
  description?: string
  cover_image?: string
  chapters_count?: number
  articles_count?: number
  theme?: string
}

// 获取书籍列表
export async function getBooks(): Promise<{ success: boolean; books?: Book[] }> {
  const response = await fetch(`${API_BASE}/api/books`)
  return response.json()
}

// 扫描聚合书籍
export async function regenerateBooks(): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/api/books/regenerate`, {
    method: 'POST'
  })
  return response.json()
}

// 获取书籍详情
export async function getBook(bookId: string): Promise<{ success: boolean; book?: Book; chapters?: any[] }> {
  const response = await fetch(`${API_BASE}/api/books/${bookId}`)
  return response.json()
}

// 获取章节内容
export async function getChapterContent(bookId: string, chapterPath: string): Promise<{ success: boolean; content?: string }> {
  const response = await fetch(`${API_BASE}/api/books/${bookId}/chapters/${encodeURIComponent(chapterPath)}`)
  return response.json()
}

// ========== 小红书 API ==========

export interface XhsGenerateParams {
  topic: string
  count: number
  style: string
  generate_video: boolean
}

// 创建小红书生成任务
export async function createXhsTask(params: XhsGenerateParams): Promise<{ success: boolean; task_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/xhs/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 创建小红书 SSE 连接
export function createXhsStream(taskId: string): EventSource {
  return new EventSource(`${API_BASE}/api/xhs/stream/${taskId}`)
}

// 取消小红书任务
export async function cancelXhsTask(taskId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/api/xhs/tasks/${taskId}/cancel`, {
    method: 'POST'
  })
  return response.json()
}

// 发布到小红书
export async function publishToXhs(params: {
  cookies: any[]
  title: string
  content: string
  tags: string[]
  images: string[]
}): Promise<{ success: boolean; url?: string; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/xhs/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 生成讲解视频
export async function generateExplanationVideo(params: {
  images: string[]
  scripts: string[]
  style: string
  target_duration: number
  video_model: string
}): Promise<{ success: boolean; video_url?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/xhs/explanation-video`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// ========== 教程评估 API ==========

export interface ReviewerParams {
  git_url: string
  enable_search?: boolean
}

// 创建评估任务
export async function createReviewTask(params: ReviewerParams): Promise<{ success: boolean; task_id?: string; error?: string }> {
  const response = await fetch(`${API_BASE}/api/reviewer/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  return response.json()
}

// 创建评估 SSE 连接
export function createReviewStream(taskId: string): EventSource {
  return new EventSource(`${API_BASE}/api/reviewer/stream/${taskId}`)
}

// 获取评估列表
export async function getReviewList(): Promise<{ success: boolean; reviews?: any[] }> {
  const response = await fetch(`${API_BASE}/api/reviewer/list`)
  return response.json()
}

// 获取评估详情
export async function getReviewDetail(reviewId: string): Promise<{ success: boolean; review?: any }> {
  const response = await fetch(`${API_BASE}/api/reviewer/${reviewId}`)
  return response.json()
}
