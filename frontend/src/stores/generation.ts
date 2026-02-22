/**
 * Blog generation state management store.
 *
 * Tracks multi-stage generation pipeline: stage transitions,
 * per-task progress, and structured log entries.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type GenerationStage =
  | 'idle'
  | 'clarifying'
  | 'researching'
  | 'planning'
  | 'writing'
  | 'reviewing'
  | 'completed'
  | 'error'

export interface TaskState {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  detail: string
  startedAt?: number
  completedAt?: number
}

export interface LogEntry {
  id: string
  timestamp: number
  type: 'info' | 'success' | 'warning' | 'error' | 'system'
  content: string
}

let logCounter = 0

export const useGenerationStore = defineStore('generation', () => {
  const stage = ref<GenerationStage>('idle')
  const tasks = ref<Record<string, TaskState>>({})
  const activeTaskIds = ref<string[]>([])
  const logs = ref<LogEntry[]>([])
  const startTime = ref(0)
  const progress = ref({ current: 0, total: 0 })

  const isRunning = computed(() =>
    !['idle', 'completed', 'error'].includes(stage.value)
  )
  const completedTasks = computed(() =>
    Object.values(tasks.value).filter(t => t.status === 'completed').length
  )
  const elapsedMs = computed(() =>
    startTime.value > 0 ? Date.now() - startTime.value : 0
  )

  function addLog(content: string, type: LogEntry['type'] = 'info') {
    logs.value.push({
      id: `log_${++logCounter}`,
      timestamp: Date.now(),
      type,
      content,
    })
  }

  function handleStageChange(newStage: GenerationStage) {
    stage.value = newStage
    if (newStage === 'researching' || newStage === 'clarifying') {
      startTime.value = Date.now()
    }
    addLog(`Stage: ${newStage}`, 'system')
  }

  function handleTaskUpdate(taskId: string, update: Partial<TaskState>) {
    if (!tasks.value[taskId]) {
      tasks.value[taskId] = {
        id: taskId, label: '', status: 'pending',
        progress: 0, detail: '', ...update,
      }
    } else {
      Object.assign(tasks.value[taskId], update)
    }
    if (update.status === 'running' && !activeTaskIds.value.includes(taskId)) {
      activeTaskIds.value.push(taskId)
    } else if (update.status === 'completed' || update.status === 'failed') {
      activeTaskIds.value = activeTaskIds.value.filter(id => id !== taskId)
    }
  }

  function handleProgress(current: number, total: number) {
    progress.value = { current, total }
  }

  function reset() {
    stage.value = 'idle'
    tasks.value = {}
    activeTaskIds.value = []
    logs.value = []
    startTime.value = 0
    progress.value = { current: 0, total: 0 }
  }

  return {
    stage, tasks, activeTaskIds, logs, startTime, progress,
    isRunning, completedTasks, elapsedMs,
    addLog, handleStageChange, handleTaskUpdate, handleProgress, reset,
  }
})
