import { ref, computed, onMounted, onUnmounted } from 'vue'

export interface CronJobView {
  id: string
  name: string
  description?: string
  enabled: boolean
  schedule: {
    kind: string
    expr?: string
    human_readable?: string
  }
  next_run_at?: string
  last_run_at?: string
  last_status?: string
  last_error?: string
  consecutive_errors: number
  generation: { topic: string; [key: string]: any }
  tags: string[]
}

export function useCronJobs(pollInterval = 5000) {
  const jobs = ref<CronJobView[]>([])
  const loading = ref(true)
  const error = ref('')
  const feedback = ref('')

  const activeCount = computed(() =>
    jobs.value.filter(j => j.enabled && j.last_status !== 'error').length
  )
  const pausedCount = computed(() =>
    jobs.value.filter(j => !j.enabled).length
  )
  const errorCount = computed(() =>
    jobs.value.filter(j => j.last_status === 'error').length
  )

  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    error.value = ''
    try {
      const res = await fetch('/api/scheduler/tasks')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      jobs.value = Array.isArray(data) ? data : []
      return true
    } catch {
      error.value = '加载定时任务失败，请重试'
      return false
    } finally {
      loading.value = false
    }
  }

  async function runAction(
    url: string,
    options: RequestInit,
    successMessage: string,
    errorMessage: string,
  ) {
    error.value = ''
    feedback.value = ''
    try {
      const res = await fetch(url, options)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const refreshed = await refresh()
      if (!refreshed) {
        error.value = successMessage + '，但列表刷新失败，请重试'
        return true
      }
      feedback.value = successMessage
      return true
    } catch {
      error.value = errorMessage
      return false
    }
  }

  function create(payload: Record<string, any>) {
    return runAction(
      '/api/scheduler/tasks',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      '定时任务已创建',
      '创建定时任务失败，请重试',
    )
  }

  function remove(id: string) {
    return runAction(
      `/api/scheduler/tasks/${id}`,
      { method: 'DELETE' },
      '定时任务已删除',
      '删除定时任务失败，请重试',
    )
  }

  function toggle(job: CronJobView) {
    const action = job.enabled ? 'pause' : 'resume'
    return runAction(
      `/api/scheduler/tasks/${job.id}/${action}`,
      { method: 'POST' },
      job.enabled ? '定时任务已暂停' : '定时任务已恢复',
      '更新定时任务失败，请重试',
    )
  }

  function retry(id: string) {
    return runAction(
      `/api/scheduler/tasks/${id}/retry`,
      { method: 'POST' },
      '重试请求已提交',
      '重试定时任务失败，请重试',
    )
  }

  function run(id: string) {
    return runAction(
      `/api/scheduler/tasks/${id}/run`,
      { method: 'POST' },
      '执行请求已提交',
      '执行定时任务失败，请重试',
    )
  }

  function clearFeedback() {
    feedback.value = ''
  }

  function startPolling() {
    timer = setInterval(refresh, pollInterval)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function handleVisibility() {
    if (document.hidden) {
      stopPolling()
    } else {
      refresh()
      startPolling()
    }
  }

  onMounted(() => {
    refresh()
    startPolling()
    document.addEventListener('visibilitychange', handleVisibility)
  })

  onUnmounted(() => {
    stopPolling()
    document.removeEventListener('visibilitychange', handleVisibility)
  })

  return {
    jobs,
    loading,
    error,
    feedback,
    activeCount,
    pausedCount,
    errorCount,
    refresh,
    create,
    remove,
    toggle,
    retry,
    run,
    clearFeedback,
  }
}
