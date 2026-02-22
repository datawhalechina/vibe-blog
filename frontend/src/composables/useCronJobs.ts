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
    try {
      const res = await fetch('/api/scheduler/tasks')
      const data = await res.json()
      jobs.value = Array.isArray(data) ? data : []
    } catch {
      // silent
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Record<string, any>) {
    await fetch('/api/scheduler/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    await refresh()
  }

  async function remove(id: string) {
    await fetch(`/api/scheduler/tasks/${id}`, { method: 'DELETE' })
    await refresh()
  }

  async function toggle(job: CronJobView) {
    const action = job.enabled ? 'pause' : 'resume'
    await fetch(`/api/scheduler/tasks/${job.id}/${action}`, { method: 'POST' })
    await refresh()
  }

  async function retry(id: string) {
    await fetch(`/api/scheduler/tasks/${id}/retry`, { method: 'POST' })
    await refresh()
  }

  async function run(id: string) {
    await fetch(`/api/scheduler/tasks/${id}/run`, { method: 'POST' })
    await refresh()
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
    activeCount,
    pausedCount,
    errorCount,
    refresh,
    create,
    remove,
    toggle,
    retry,
    run,
  }
}
