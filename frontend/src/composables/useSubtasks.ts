/**
 * useSubtasks — 子任务状态管理 composable（1002.13）
 *
 * 监听 SSE subtask_* 事件，维护子任务实时状态。
 * 借鉴 DeerFlow SubtaskContext 的设计，适配 Vue 3 Composition API。
 */
import { ref, computed } from 'vue'

export interface Subtask {
  id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'timed_out'
  subagent_type: string
  description: string
  latestMessage?: string
  result?: string
  error?: string
  startedAt?: string
  completedAt?: string
}

export function useSubtasks() {
  const tasks = ref<Record<string, Subtask>>({})

  const activeCount = computed(() =>
    Object.values(tasks.value).filter(t => t.status === 'in_progress').length
  )

  const completedCount = computed(() =>
    Object.values(tasks.value).filter(t => t.status === 'completed').length
  )

  const updateSubtask = (partial: Partial<Subtask> & { id: string }) => {
    const existing = tasks.value[partial.id]
    tasks.value = {
      ...tasks.value,
      [partial.id]: { ...existing, ...partial } as Subtask,
    }
  }

  /**
   * 处理 SSE result 事件中的 subtask_* 类型
   */
  const handleSSEEvent = (data: any) => {
    if (!data?.type?.startsWith('subtask_')) return false

    const taskId = data.task_id || data.data?.task_id
    if (!taskId) return false

    switch (data.type) {
      case 'subtask_started':
        updateSubtask({
          id: taskId,
          status: 'in_progress',
          subagent_type: data.subagent || data.data?.subagent || '',
          description: data.description || data.data?.description || '',
          startedAt: new Date().toISOString(),
        })
        return true

      case 'subtask_running':
        updateSubtask({
          id: taskId,
          latestMessage: data.message || data.data?.message || '',
        })
        return true

      case 'subtask_completed':
        updateSubtask({
          id: taskId,
          status: data.status === 'failed' ? 'failed'
            : data.status === 'timed_out' ? 'timed_out'
            : 'completed',
          result: data.result || data.data?.result,
          error: data.error || data.data?.error,
          completedAt: new Date().toISOString(),
        })
        return true

      case 'subtask_failed':
        updateSubtask({
          id: taskId,
          status: 'failed',
          error: data.error || data.data?.error || '执行失败',
          completedAt: new Date().toISOString(),
        })
        return true

      case 'subtask_timed_out':
        updateSubtask({
          id: taskId,
          status: 'timed_out',
          error: data.error || data.data?.error || '执行超时',
          completedAt: new Date().toISOString(),
        })
        return true

      default:
        return false
    }
  }

  const reset = () => {
    tasks.value = {}
  }

  return {
    tasks,
    activeCount,
    completedCount,
    updateSubtask,
    handleSSEEvent,
    reset,
  }
}
