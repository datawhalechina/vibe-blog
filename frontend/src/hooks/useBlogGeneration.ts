import { useCallback, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { useDocumentStore } from '@/stores/documentStore'
import { createBlogTask, createMiniBlogTask, subscribeTaskStream, cancelTask } from '@/services/api'
import type { GenerateBlogRequest, SSEEvent } from '@/services/api'

export function useBlogGeneration() {
  const { addExecutionLog, updateExecutionLog, setIsGenerating, clearLogs } = useChatStore()
  const { setDocument, setCoverUrl, setVideoUrl, setOutline, setSectionContent } = useDocumentStore()
  const cancelFnRef = useRef<(() => void) | null>(null)
  const taskIdRef = useRef<string | null>(null)
  // 用于追踪流式输出的日志 ID
  const streamLogIdRef = useRef<string | null>(null)

  // 处理 result 事件 - 大纲和章节更新
  const handleResultEvent = useCallback((data: SSEEvent['data']) => {
    const resultType = data.type
    const resultData = data.data
    const timestamp = new Date()

    console.log('Result Event:', resultType, resultData)

    switch (resultType) {
      case 'outline_complete':
        // 大纲完成 - 初始化编辑器中的章节
        // 后端格式: { title, sections_count, sections: ['标题1', '标题2', ...], message }
        if (resultData?.sections) {
          const sectionTitles = resultData.sections as string[]
          const outline = {
            title: resultData.title || '生成的博客',
            summary: resultData.message || '',
            sections: sectionTitles.map((title: string, i: number) => ({
              index: i,
              title: title || `章节 ${i + 1}`,
              content: '',  // 内容稍后填充
              status: 'pending' as const,
            })),
          }
          setOutline(outline)
          
          addExecutionLog({
            id: `outline-complete-${Date.now()}`,
            type: 'result',
            success: true,
            message: `📋 大纲生成完成：${sectionTitles.length} 个章节`,
            timestamp,
          })
        }
        break

      case 'section_complete':
        // 单个章节完成 - 更新对应章节的内容
        if (resultData?.section_index !== undefined) {
          const index = resultData.section_index - 1  // 后端是 1-indexed
          const content = resultData.content || ''
          
          if (content) {
            setSectionContent(index, content)
          }
          
          addExecutionLog({
            id: `section-${index}-${Date.now()}`,
            type: 'tool_call',
            toolName: `章节 ${resultData.section_index}`,
            toolIcon: '✅',
            description: `${resultData.title || ''} 撰写完成 (${resultData.content_length || 0} 字符)`,
            status: 'done',
            timestamp,
          })
        }
        break

      case 'researcher_complete':
        addExecutionLog({
          id: `researcher-${Date.now()}`,
          type: 'tool_call',
          toolName: '资料研究',
          toolIcon: '🔍',
          description: `收集了 ${resultData?.total_length || 0} 字符的背景资料`,
          status: 'done',
          timestamp,
        })
        break

      case 'coder_complete':
        addExecutionLog({
          id: `coder-${Date.now()}`,
          type: 'tool_call',
          toolName: '代码生成',
          toolIcon: '💻',
          description: `生成了 ${resultData?.code_blocks_count || 0} 个代码块`,
          status: 'done',
          timestamp,
        })
        break

      case 'artist_complete':
        addExecutionLog({
          id: `artist-${Date.now()}`,
          type: 'tool_call',
          toolName: '配图生成',
          toolIcon: '🎨',
          description: `生成了 ${resultData?.images_count || 0} 张配图`,
          status: 'done',
          timestamp,
        })
        break

      case 'reviewer_complete':
        addExecutionLog({
          id: `reviewer-${Date.now()}`,
          type: 'tool_call',
          toolName: '质量审核',
          toolIcon: resultData?.passed ? '✅' : '⚠️',
          description: `评分: ${resultData?.score || 0}`,
          status: 'done',
          timestamp,
        })
        break

      case 'assembler_complete':
        addExecutionLog({
          id: `assembler-${Date.now()}`,
          type: 'tool_call',
          toolName: '内容组装',
          toolIcon: '📦',
          description: `生成了 ${resultData?.markdown_length || 0} 字符的 Markdown`,
          status: 'done',
          timestamp,
        })
        break
    }
  }, [addExecutionLog, setOutline, setSectionContent])

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    const { event: eventType, data } = event
    const timestamp = new Date()

    console.log('SSE Event:', eventType, data) // 调试日志

    switch (eventType) {
      case 'connected':
        // 连接成功
        addExecutionLog({
          id: `connected-${Date.now()}`,
          type: 'tool_call',
          toolName: 'SSE 连接',
          toolIcon: '🔗',
          description: '已连接到服务器',
          status: 'done',
          timestamp,
        })
        break

      case 'progress':
      case 'stage':
        // 阶段进度 - 后端格式: {stage, progress, message}
        const stageName = data.stage || '处理中'
        const progressMsg = data.message || ''
        const progressPercent = data.progress || 0
        
        addExecutionLog({
          id: `stage-${Date.now()}-${Math.random()}`,
          type: 'tool_call',
          toolName: stageName,
          toolIcon: getStageIcon(stageName),
          description: `${progressMsg} (${progressPercent}%)`,
          status: progressPercent >= 100 ? 'done' : 'running',
          timestamp,
        })
        break

      case 'thinking':
        // AI 思考过程
        addExecutionLog({
          id: `thinking-${Date.now()}`,
          type: 'thinking',
          content: data.message || data.detail || '',
          timestamp,
        })
        break

      case 'tool_call':
        // 工具调用
        addExecutionLog({
          id: `tool-${Date.now()}`,
          type: 'tool_call',
          toolName: data.message || 'Tool',
          toolIcon: '🔧',
          description: data.detail || '',
          status: 'running',
          timestamp,
        })
        break

      case 'content':
        // 内容生成
        addExecutionLog({
          id: `content-${Date.now()}`,
          type: 'thinking',
          content: `📝 ${data.message || '内容生成中...'}`,
          timestamp,
        })
        break

      case 'log':
        // 后端日志 - 显示为思考过程
        if (data.message) {
          addExecutionLog({
            id: `log-${Date.now()}-${Math.random()}`,
            type: 'thinking',
            content: `${data.logger ? `[${data.logger}] ` : ''}${data.message}`,
            timestamp,
          })
        }
        break

      case 'heartbeat':
        // 心跳事件，忽略
        break

      case 'result':
        // 后端结果事件 - 处理大纲和章节更新
        handleResultEvent(data)
        break

      case 'stream':
        // 流式输出 - 更新同一条日志而不是新增
        if (data.stage === 'outline' && data.accumulated) {
          const logId = 'stream-outline'
          if (!streamLogIdRef.current || streamLogIdRef.current !== logId) {
            // 首次创建日志
            streamLogIdRef.current = logId
            addExecutionLog({
              id: logId,
              type: 'thinking',
              content: `📋 大纲生成中...\n${data.accumulated.substring(0, 500)}`,
              timestamp,
            })
          } else {
            // 更新现有日志
            updateExecutionLog(logId, {
              content: `📋 大纲生成中...\n${data.accumulated.substring(0, 500)}`,
              timestamp,
            })
          }
        } else if (data.stage === 'section' && data.section_index !== undefined) {
          // 章节内容流式输出 - 实时更新到编辑器
          const index = data.section_index - 1  // 后端是 1-indexed
          const content = data.accumulated || ''
          if (content) {
            setSectionContent(index, content)
          }
        }
        break

      case 'cancelled':
        // 任务取消
        addExecutionLog({
          id: `cancelled-${Date.now()}`,
          type: 'result',
          success: false,
          message: data.message || '任务已取消',
          timestamp,
        })
        setIsGenerating(false)
        break

      case 'image':
        // 图片生成
        addExecutionLog({
          id: `image-${Date.now()}`,
          type: 'preview',
          previewType: 'image',
          thumbnailUrl: data.detail,
          content: data.message,
          timestamp,
        })
        break

      case 'complete':
        // 完成 - 保存生成的内容
        if (data.result) {
          if (data.result.markdown) {
            setDocument({
              title: data.result.title || '生成的博客',
              markdown: data.result.markdown,
            })
          }
          if (data.result.cover_url) {
            setCoverUrl(data.result.cover_url)
          }
          if (data.result.video_url) {
            setVideoUrl(data.result.video_url)
          }
        }
        addExecutionLog({
          id: `result-${Date.now()}`,
          type: 'result',
          success: true,
          message: data.message || '博客生成完成！',
          timestamp,
        })
        setIsGenerating(false)
        break

      case 'error':
        // 错误
        addExecutionLog({
          id: `error-${Date.now()}`,
          type: 'result',
          success: false,
          message: data.error || data.message || '生成失败',
          timestamp,
        })
        setIsGenerating(false)
        break

      default:
        // 默认消息
        if (data.message) {
          addExecutionLog({
            id: `msg-${Date.now()}`,
            type: 'thinking',
            content: data.message,
            timestamp,
          })
        }
    }
  }, [addExecutionLog, updateExecutionLog, setIsGenerating, setDocument, setCoverUrl, setVideoUrl])

  const generate = useCallback(async (params: GenerateBlogRequest) => {
    // 清除之前的日志和状态
    clearLogs()
    setIsGenerating(true)
    streamLogIdRef.current = null  // 重置流式日志 ID

    // 添加初始日志
    addExecutionLog({
      id: `start-${Date.now()}`,
      type: 'thinking',
      content: `🚀 开始生成博客：${params.topic}\n\n正在分析主题并准备生成...`,
      timestamp: new Date(),
    })

    try {
      // 根据长度选择 API
      const createTask = params.target_length === 'mini' ? createMiniBlogTask : createBlogTask
      const result = await createTask(params)

      if (!result.success || !result.task_id) {
        throw new Error(result.error || '创建任务失败')
      }

      taskIdRef.current = result.task_id

      // 添加任务创建成功日志
      addExecutionLog({
        id: `task-${Date.now()}`,
        type: 'tool_call',
        toolName: '任务创建',
        toolIcon: '✅',
        description: `任务 ID: ${result.task_id}`,
        status: 'done',
        timestamp: new Date(),
      })

      // 订阅 SSE 流
      cancelFnRef.current = subscribeTaskStream(
        result.task_id,
        handleSSEEvent,
        (error) => {
          addExecutionLog({
            id: `error-${Date.now()}`,
            type: 'result',
            success: false,
            message: `连接错误: ${error.message}`,
            timestamp: new Date(),
          })
          setIsGenerating(false)
        },
        () => {
          setIsGenerating(false)
        }
      )

      return result.task_id
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      addExecutionLog({
        id: `error-${Date.now()}`,
        type: 'result',
        success: false,
        message: `创建任务失败: ${errorMessage}`,
        timestamp: new Date(),
      })
      setIsGenerating(false)
      throw error
    }
  }, [addExecutionLog, clearLogs, handleSSEEvent, setIsGenerating])

  const cancel = useCallback(async () => {
    if (cancelFnRef.current) {
      cancelFnRef.current()
      cancelFnRef.current = null
    }

    if (taskIdRef.current) {
      try {
        await cancelTask(taskIdRef.current)
        addExecutionLog({
          id: `cancel-${Date.now()}`,
          type: 'result',
          success: true,
          message: '任务已取消',
          timestamp: new Date(),
        })
      } catch (error) {
        console.error('Cancel task error:', error)
      }
      taskIdRef.current = null
    }

    setIsGenerating(false)
  }, [addExecutionLog, setIsGenerating])

  return { generate, cancel }
}

// 根据阶段获取图标
function getStageIcon(stage?: string): string {
  if (!stage) return '⚙️'
  
  const iconMap: Record<string, string> = {
    'outline': '📋',
    'research': '🔍',
    'search': '🔍',
    'writing': '✍️',
    'content': '📝',
    'image': '🖼️',
    'review': '📖',
    'optimize': '✨',
    'cover': '🎨',
    'video': '🎬',
    'complete': '✅',
  }

  for (const [key, icon] of Object.entries(iconMap)) {
    if (stage.toLowerCase().includes(key)) {
      return icon
    }
  }

  return '⚙️'
}
