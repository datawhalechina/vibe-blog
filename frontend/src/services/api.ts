// 后端 API 基础配置
const API_BASE = '/api'

// 博客生成请求参数
export interface GenerateBlogRequest {
  topic: string
  article_type?: 'tutorial' | 'problem-solving' | 'comparison' | 'picture-book'
  target_audience?: 'beginner' | 'intermediate' | 'advanced'
  target_length?: 'mini' | 'short' | 'medium' | 'long' | 'custom'
  document_ids?: string[]
  image_style?: string
  generate_cover_video?: boolean
  custom_config?: {
    section_count?: number
    image_count?: number
    code_block_count?: number
    target_words?: number
  }
}

// 任务状态
export interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress?: number
  result?: {
    markdown?: string
    title?: string
    cover_url?: string
    video_url?: string
  }
  error?: string
}

// SSE 事件类型
export interface SSEEvent {
  event: 'progress' | 'stage' | 'thinking' | 'tool_call' | 'content' | 'image' | 'complete' | 'error' | 'connected' | 'heartbeat' | 'log' | 'result' | 'stream' | 'cancelled'
  data: {
    type?: string
    message?: string
    detail?: string
    progress?: number
    stage?: string
    result?: any
    error?: string
    logger?: string
    accumulated?: string
    delta?: string
    data?: any
    section_index?: number  // 章节索引（流式输出时使用）
    section_title?: string  // 章节标题
  }
}

// 图片风格
export interface ImageStyle {
  id: string
  name: string
  description?: string
}

// 段落操作请求
export interface ParagraphActionRequest {
  content: string
  section_index?: number
  action_type: 'image' | 'code' | 'polish' | 'deepen' | 'review'
}

// ========== API 函数 ==========

/**
 * 安全解析 JSON 响应
 */
async function safeJsonParse(response: Response): Promise<any> {
  const text = await response.text()
  if (!text) {
    throw new Error(`服务器返回空响应 (HTTP ${response.status})`)
  }
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`JSON 解析失败: ${text.substring(0, 100)}`)
  }
}

/**
 * 创建博客生成任务
 */
export async function createBlogTask(params: GenerateBlogRequest): Promise<{ success: boolean; task_id?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/blog/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      return { success: false, error: `HTTP ${response.status}: ${errorText || '请求失败'}` }
    }
    
    return await safeJsonParse(response)
  } catch (error) {
    const message = error instanceof Error ? error.message : '网络请求失败'
    // 检查是否是后端未启动
    if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
      return { success: false, error: '无法连接后端服务，请确保后端已启动 (python app.py)' }
    }
    return { success: false, error: message }
  }
}

/**
 * 创建 Mini 博客生成任务
 */
export async function createMiniBlogTask(params: GenerateBlogRequest): Promise<{ success: boolean; task_id?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/blog/generate/mini`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      return { success: false, error: `HTTP ${response.status}: ${errorText || '请求失败'}` }
    }
    
    return await safeJsonParse(response)
  } catch (error) {
    const message = error instanceof Error ? error.message : '网络请求失败'
    if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
      return { success: false, error: '无法连接后端服务，请确保后端已启动 (python app.py)' }
    }
    return { success: false, error: message }
  }
}

/**
 * 订阅任务 SSE 流
 */
export function subscribeTaskStream(
  taskId: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/stream`)

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      onEvent({ event: 'progress', data })  // 默认作为 progress 事件
    } catch (err) {
      console.error('Failed to parse SSE message:', err)
    }
  }

  // 监听特定事件类型（与后端 SSE 事件对应）
  const eventTypes: SSEEvent['event'][] = ['connected', 'progress', 'stage', 'thinking', 'tool_call', 'content', 'image', 'complete', 'error', 'heartbeat', 'log', 'result', 'stream', 'cancelled']
  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        onEvent({ event: type, data })
      } catch (err) {
        console.error(`Failed to parse SSE ${type} event:`, err)
      }
    })
  })

  eventSource.onerror = (e) => {
    console.error('SSE error:', e)
    if (onError) onError(new Error('SSE connection error'))
    eventSource.close()
  }

  // 监听完成事件
  eventSource.addEventListener('complete', () => {
    if (onComplete) onComplete()
    eventSource.close()
  })

  // 返回取消函数
  return () => {
    eventSource.close()
  }
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`)
  return response.json()
}

/**
 * 取消任务
 */
export async function cancelTask(taskId: string): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
    method: 'POST',
  })
  return response.json()
}

/**
 * 段落操作 - 配图
 */
export async function generateParagraphImage(content: string): Promise<{ success: boolean; image_url?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/generate-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: content,
        style: 'default',
      }),
    })
    return await safeJsonParse(response)
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : '生成图片失败' }
  }
}

/**
 * 段落操作 - 润色（调用 LLM）
 */
export async function polishParagraph(content: string): Promise<{ success: boolean; result?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/paragraph/polish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }
    return await safeJsonParse(response)
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : '润色失败' }
  }
}

/**
 * 段落操作 - 生成代码
 */
export async function generateParagraphCode(content: string): Promise<{ success: boolean; code?: string; language?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/paragraph/code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }
    return await safeJsonParse(response)
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : '生成代码失败' }
  }
}

/**
 * 段落操作 - 追问深化
 */
export async function deepenParagraph(content: string): Promise<{ success: boolean; result?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/paragraph/deepen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }
    return await safeJsonParse(response)
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : '深化内容失败' }
  }
}

/**
 * 段落操作 - 校对审查
 */
export async function reviewParagraph(content: string): Promise<{ success: boolean; issues?: string[]; suggestions?: string[]; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/paragraph/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }
    return await safeJsonParse(response)
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : '校对审查失败' }
  }
}

/**
 * 获取图片风格列表
 */
export async function getImageStyles(): Promise<{ success: boolean; styles?: ImageStyle[]; error?: string }> {
  const response = await fetch(`${API_BASE}/image-styles`)
  return response.json()
}

/**
 * 获取前端配置
 */
export async function getFrontendConfig(): Promise<{ success: boolean; config?: Record<string, any>; error?: string }> {
  const response = await fetch(`${API_BASE}/config`)
  return response.json()
}

/**
 * 获取历史记录
 */
export async function getHistory(page = 1, pageSize = 20): Promise<{ success: boolean; items?: any[]; total?: number; error?: string }> {
  const response = await fetch(`${API_BASE}/history?page=${page}&page_size=${pageSize}`)
  return response.json()
}
