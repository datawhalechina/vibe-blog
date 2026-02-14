/**
 * useTaskStream — SSE 任务流 composable
 * 从 Home.vue 提取的通用 SSE 事件处理逻辑
 */
import { ref, onUnmounted } from 'vue'
import * as api from '@/services/api'
import type { Citation } from '@/utils/citationMatcher'

export interface ProgressItem {
  time: string
  message: string
  type: string
  data?: any
  detail?: string
}

export interface OutlineData {
  title: string
  sections_titles: string[]
  sections: any[]
}

export function useTaskStream() {
  // 状态
  const isLoading = ref(false)
  const showProgress = ref(false)
  const progressItems = ref<ProgressItem[]>([])
  const progressText = ref('')
  const statusBadge = ref('')
  const currentTaskId = ref('')
  const previewContent = ref('')
  const outlineData = ref<OutlineData | null>(null)
  const waitingForOutline = ref(false)
  const citations = ref<Citation[]>([])
  const completedBlogId = ref('')

  let eventSource: EventSource | null = null
  let accumulatedPreview = ''
  let previewTimer: ReturnType<typeof setTimeout> | null = null

  // 节流更新预览
  const throttledUpdatePreview = (content: string) => {
    if (previewTimer) return
    previewTimer = setTimeout(() => {
      previewContent.value = content
      previewTimer = null
    }, 100)
  }

  // 添加进度项
  const addProgressItem = (message: string, type = 'info', detail?: string) => {
    progressItems.value.push({
      time: new Date().toLocaleTimeString(),
      message,
      type,
      ...(detail ? { detail } : {}),
    })
  }

  // 更新流式项
  const updateStreamItem = (content: string) => {
    const existing = progressItems.value.find((item) => item.type === 'stream')
    if (existing) {
      existing.message = content
    } else {
      addProgressItem(content, 'stream')
    }
  }

  const getStageIcon = (stage: string) => {
    const icons: Record<string, string> = {
      start: '🚀', research: '🔍', plan: '📋', write: '✍️',
      code: '💻', review: '✅', image: '🎨', assemble: '📦',
      complete: '🎉', error: '❌',
    }
    return icons[stage] || '○'
  }

  // 连接 SSE
  const connectSSE = (taskId: string, onComplete?: (data: any) => void) => {
    accumulatedPreview = ''
    previewContent.value = ''
    citations.value = []
    completedBlogId.value = ''
    const es = api.createTaskStream(taskId)
    eventSource = es

    es.addEventListener('connected', () => {
      addProgressItem('🔗 已连接到服务器')
      statusBadge.value = '运行中'
    })

    es.addEventListener('progress', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      const icon = getStageIcon(d.stage)
      addProgressItem(`${icon} ${d.message}`, d.stage === 'error' ? 'error' : 'info')
      progressText.value = d.message
    })

    es.addEventListener('log', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      let icon = '📝'
      const loggerIcons: Record<string, string> = {
        generator: '⚙️', researcher: '🔍', planner: '📋', writer: '✍️',
        questioner: '❓', coder: '💻', artist: '🎨', reviewer: '✅',
        assembler: '📦', search_service: '🌐', blog_service: '🖼️',
      }
      icon = loggerIcons[d.logger] || icon
      const isSuccess = d.message?.includes('完成') || d.message?.includes('成功')
      addProgressItem(`${icon} ${d.message}`, isSuccess ? 'success' : 'info')
      progressText.value = d.message
    })

    es.addEventListener('stream', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      if (d.stage === 'outline') updateStreamItem(d.accumulated)
    })

    es.addEventListener('outline_ready', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      outlineData.value = {
        title: d.title || '',
        sections_titles: d.sections_titles || [],
        sections: d.sections || [],
      }
      waitingForOutline.value = true
      addProgressItem('📋 大纲已生成，等待确认...', 'info')
      progressText.value = '等待大纲确认'
    })

    es.addEventListener('writing_chunk', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      if (d.accumulated) {
        accumulatedPreview = d.accumulated
        throttledUpdatePreview(accumulatedPreview)
      } else if (d.delta) {
        accumulatedPreview += d.delta
        throttledUpdatePreview(accumulatedPreview)
      }
    })

    es.addEventListener('result', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      const data = d.data || {}

      switch (d.type) {
        case 'search_started':
          addProgressItem(`🔍 搜索: ${data.query || ''}`, 'info')
          break
        case 'search_results':
          progressItems.value.push({
            time: new Date().toLocaleTimeString(),
            message: `🔍 ${data.query || '搜索结果'}`,
            type: 'search',
            data,
          })
          break
        case 'crawl_completed':
          progressItems.value.push({
            time: new Date().toLocaleTimeString(),
            message: `📖 已抓取 ${data.count || 0} 篇`,
            type: 'crawl',
            data,
          })
          break
        case 'search_completed':
          addProgressItem(`✅ ${data.message || '搜索完成'}`, 'success')
          break
        case 'researcher_complete':
          if (data.document_count > 0 || data.web_count > 0) {
            addProgressItem(`📊 知识来源: 文档 ${data.document_count} 条, 网络 ${data.web_count} 条`, 'info')
          }
          if (data.key_concepts?.length > 0) {
            addProgressItem(`💡 核心概念: ${data.key_concepts.join(', ')}`, 'success')
          }
          break
        case 'outline_complete':
          if (data.sections_titles?.length > 0) {
            const titles = data.sections_titles.map((t: string, i: number) => `${i + 1}. ${t}`).join('\n')
            addProgressItem(`📋 大纲: ${data.title}`, 'success', titles)
          }
          break
        case 'section_complete':
          addProgressItem(`✍️ 章节 ${data.section_index} 完成: ${data.title} (${data.content_length} 字)`, 'success')
          break
        case 'check_knowledge_complete':
          if (data.gaps_count > 0) {
            addProgressItem(`🔎 知识空白: ${data.gaps_count} 个 (搜索 ${data.search_count}/${data.max_search_count})`, 'info', data.gaps?.join('\n'))
          }
          break
        case 'refine_search_complete':
          addProgressItem(`🌐 第 ${data.round} 轮搜索: 获取 ${data.results_count} 条结果`, 'info')
          break
        case 'enhance_knowledge_complete':
          addProgressItem(`📚 内容增强完成: 累积知识 ${data.knowledge_length} 字`, 'success')
          break
        case 'questioner_complete':
          addProgressItem(data.needs_deepen ? '❓ 内容需要深化' : '✅ 内容深度检查通过', data.needs_deepen ? 'info' : 'success')
          break
        case 'coder_complete':
          addProgressItem(`💻 代码示例: ${data.code_blocks_count} 个代码块`, 'success')
          break
        case 'artist_complete':
          addProgressItem(`🎨 配图描述: ${data.images_count} 张`, 'success')
          break
        case 'reviewer_complete':
          addProgressItem(`✅ 质量审核: ${data.score} 分 ${data.passed ? '通过' : '需修订'}`, data.passed ? 'success' : 'warning')
          break
        case 'assembler_complete':
          addProgressItem(`📦 文档组装完成: ${data.markdown_length} 字`, 'success')
          break
        default:
          if (data.message) {
            addProgressItem(`📌 ${data.message}`, 'info')
          }
      }
    })

    es.addEventListener('complete', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      addProgressItem('🎉 生成完成！', 'success')
      statusBadge.value = '已完成'
      progressText.value = '生成完成'
      isLoading.value = false

      // 保存 citations
      if (d.citations) {
        citations.value = d.citations
      }

      // 更新最终预览
      if (d.markdown) {
        previewContent.value = d.markdown
      }

      completedBlogId.value = d.id || d.book_id || ''

      es.close()
      eventSource = null

      onComplete?.(d)
    })

    es.addEventListener('error', (e: MessageEvent) => {
      if (e.data) {
        const d = JSON.parse(e.data)
        addProgressItem(`❌ 错误: ${d.message}`, 'error')
      }
      statusBadge.value = '错误'
      isLoading.value = false
    })

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        addProgressItem('🔌 连接已关闭')
        isLoading.value = false
      }
    }
  }

  // 确认大纲
  const confirmOutline = async (action: string) => {
    if (!currentTaskId.value) return
    waitingForOutline.value = false
    try {
      const data = await api.confirmOutline(currentTaskId.value, action as 'accept' | 'edit')
      if (data.success) {
        addProgressItem(action === 'accept' ? '✓ 大纲已确认，开始写作' : '✓ 大纲已修改，重新规划', 'success')
        progressText.value = '写作中...'
      }
    } catch (error: any) {
      addProgressItem(`✗ 大纲确认失败: ${error.message}`, 'error')
    }
  }

  // 停止生成
  const stopGeneration = async () => {
    if (currentTaskId.value) {
      try {
        const data = await api.cancelTask(currentTaskId.value)
        if (data.success) {
          addProgressItem('⏹️ 任务已取消', 'error')
        } else {
          addProgressItem(`⚠️ 取消失败: ${data.error}`, 'error')
        }
      } catch {
        addProgressItem('⚠️ 取消请求失败', 'error')
      }
    }
    eventSource?.close()
    eventSource = null
    statusBadge.value = '已停止'
    isLoading.value = false
  }

  // 关闭进度
  const closeProgress = () => {
    showProgress.value = false
    eventSource?.close()
    eventSource = null
  }

  // 重置状态
  const reset = () => {
    isLoading.value = false
    showProgress.value = false
    progressItems.value = []
    progressText.value = ''
    statusBadge.value = ''
    currentTaskId.value = ''
    previewContent.value = ''
    outlineData.value = null
    waitingForOutline.value = false
    citations.value = []
    completedBlogId.value = ''
    accumulatedPreview = ''
  }

  onUnmounted(() => {
    eventSource?.close()
    eventSource = null
    if (previewTimer) {
      clearTimeout(previewTimer)
      previewTimer = null
    }
  })

  return {
    // 状态
    isLoading,
    showProgress,
    progressItems,
    progressText,
    statusBadge,
    currentTaskId,
    previewContent,
    outlineData,
    waitingForOutline,
    citations,
    completedBlogId,
    // 方法
    connectSSE,
    confirmOutline,
    stopGeneration,
    closeProgress,
    addProgressItem,
    reset,
  }
}
