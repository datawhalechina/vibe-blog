import { ref, type Ref } from 'vue'

/**
 * 小红书生成器 Composable
 *
 * 职责：
 * - 处理生成请求
 * - 管理 SSE 连接
 * - 任务状态管理
 * - 取消生成功能
 */

export interface XhsGenerateOptions {
  topic: string
  count: number
  style: string
  generate_video: boolean
}

export interface XhsResult {
  id?: string
  topic?: string
  image_urls?: string[]
  video_url?: string
  titles?: string[]
  copywriting?: string
  tags?: string[]
  pages?: Array<{ content?: string; page_type?: string }>
}

export interface SSEEventHandlers {
  onProgress?: (data: any) => void
  onSearch?: (data: any) => void
  onOutline?: (data: any) => void
  onContent?: (data: any) => void
  onStoryboard?: (data: any) => void
  onImageProgress?: (data: any) => void
  onImage?: (data: any) => void
  onVideo?: (data: any) => void
  onComplete?: (data: any) => void
  onError?: (message: string) => void
  onCancelled?: () => void
}

export function useXhsGenerator() {
  // 状态
  const isLoading = ref(false)
  const currentTaskId = ref<string | null>(null)
  const errorMsg = ref('')
  const currentResult = ref<XhsResult | null>(null)

  // SSE 连接
  let eventSource: EventSource | null = null
  let startTime: number | null = null

  /**
   * 开始生成小红书内容
   */
  const generate = async (
    options: XhsGenerateOptions,
    handlers: SSEEventHandlers
  ): Promise<{ success: boolean; task_id?: string; error?: string }> => {
    if (isLoading.value) {
      return { success: false, error: '正在生成中，请稍候' }
    }

    errorMsg.value = ''
    isLoading.value = true
    startTime = Date.now()

    try {
      const response = await fetch('/api/xhs/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: options.topic,
          count: options.count,
          style: options.style,
          generate_video: options.generate_video
        })
      })

      const result = await response.json()

      if (!result.success) {
        throw new Error(result.error || '任务创建失败')
      }

      currentTaskId.value = result.task_id
      connectSSE(result.task_id, handlers)

      return { success: true, task_id: result.task_id }
    } catch (error: any) {
      errorMsg.value = '❌ ' + error.message
      isLoading.value = false
      return { success: false, error: error.message }
    }
  }

  /**
   * 连接 SSE 流
   */
  const connectSSE = (taskId: string, handlers: SSEEventHandlers) => {
    if (eventSource) {
      eventSource.close()
    }

    eventSource = new EventSource(`/api/xhs/stream/${taskId}`)

    // 进度事件
    eventSource.addEventListener('progress', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onProgress?.(data)
    })

    // 搜索事件
    eventSource.addEventListener('search', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onSearch?.(data)
    })

    // 大纲事件
    eventSource.addEventListener('outline', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onOutline?.(data)
    })

    // 文案事件
    eventSource.addEventListener('content', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onContent?.(data)

      // 更新结果
      currentResult.value = {
        ...currentResult.value,
        titles: data.titles,
        copywriting: data.copywriting,
        tags: data.tags
      }
    })

    // 分镜事件
    eventSource.addEventListener('storyboard', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onStoryboard?.(data)
    })

    // 图片进度事件
    eventSource.addEventListener('image_progress', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onImageProgress?.(data)
    })

    // 图片完成事件
    eventSource.addEventListener('image', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onImage?.(data)
    })

    // 视频事件
    eventSource.addEventListener('video', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      handlers.onVideo?.(data)

      if (currentResult.value) {
        currentResult.value.video_url = data.url
      }
    })

    // 完成事件
    eventSource.addEventListener('complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      eventSource?.close()
      eventSource = null
      isLoading.value = false

      currentResult.value = {
        ...currentResult.value,
        ...data,
        image_urls: data.image_urls
      }

      handlers.onComplete?.(data)
    })

    // 错误事件
    eventSource.addEventListener('error', (e: MessageEvent) => {
      if (e.data) {
        const data = JSON.parse(e.data)
        eventSource?.close()
        eventSource = null
        isLoading.value = false
        errorMsg.value = '❌ ' + data.message
        handlers.onError?.(data.message)
      }
    })

    // 取消事件
    eventSource.addEventListener('cancelled', () => {
      eventSource?.close()
      eventSource = null
      isLoading.value = false
      handlers.onCancelled?.()
    })

    // 连接错误
    eventSource.onerror = () => {
      if (eventSource?.readyState === EventSource.CLOSED) {
        console.log('SSE 连接已关闭')
      }
    }
  }

  /**
   * 取消生成
   */
  const cancel = async (): Promise<boolean> => {
    if (!currentTaskId.value) return false

    try {
      await fetch(`/api/xhs/tasks/${currentTaskId.value}/cancel`, {
        method: 'POST'
      })

      eventSource?.close()
      eventSource = null
      isLoading.value = false

      return true
    } catch (e) {
      console.error('取消请求失败:', e)
      return false
    }
  }

  /**
   * 清理资源
   */
  const cleanup = () => {
    eventSource?.close()
    eventSource = null
    isLoading.value = false
    currentTaskId.value = null
  }

  /**
   * 获取生成耗时
   */
  const getElapsedTime = (): number => {
    if (!startTime) return 0
    return Math.ceil((Date.now() - startTime) / 1000)
  }

  return {
    // 状态（只读）
    isLoading: readonly(isLoading) as Readonly<Ref<boolean>>,
    currentTaskId: readonly(currentTaskId) as Readonly<Ref<string | null>>,
    errorMsg: readonly(errorMsg) as Readonly<Ref<string>>,
    currentResult: readonly(currentResult) as Readonly<Ref<XhsResult | null>>,

    // 方法
    generate,
    cancel,
    cleanup,
    getElapsedTime
  }
}

function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>
}
