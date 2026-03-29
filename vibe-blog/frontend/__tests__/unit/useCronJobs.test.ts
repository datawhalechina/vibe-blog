/**
 * useCronJobs composable tests
 * Tests: initial state, refresh, computed counts, toggle, cleanup
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'

// We need to control fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock vue lifecycle hooks to capture callbacks
const mountedCallbacks: Function[] = []
const unmountedCallbacks: Function[] = []

vi.mock('vue', async () => {
  const actual = await vi.importActual<typeof import('vue')>('vue')
  return {
    ...actual,
    onMounted: (cb: Function) => { mountedCallbacks.push(cb); cb() },
    onUnmounted: (cb: Function) => { unmountedCallbacks.push(cb) },
  }
})

import { useCronJobs } from '@/composables/useCronJobs'
import type { CronJobView } from '@/composables/useCronJobs'

function makeMockJobs(overrides: Partial<CronJobView>[] = []): CronJobView[] {
  const defaults: CronJobView[] = [
    {
      id: '1', name: 'Job A', enabled: true,
      schedule: { kind: 'cron', expr: '0 9 * * *', human_readable: 'Every day at 9am' },
      last_status: 'ok', consecutive_errors: 0,
      generation: { topic: 'Vue 3' }, tags: [],
    },
    {
      id: '2', name: 'Job B', enabled: false,
      schedule: { kind: 'cron', expr: '0 12 * * *' },
      last_status: 'ok', consecutive_errors: 0,
      generation: { topic: 'React' }, tags: [],
    },
    {
      id: '3', name: 'Job C', enabled: true,
      schedule: { kind: 'cron', expr: '0 18 * * *' },
      last_status: 'error', last_error: 'timeout', consecutive_errors: 3,
      generation: { topic: 'Rust' }, tags: [],
    },
  ]
  return overrides.length ? overrides.map((o, i) => ({ ...defaults[i % defaults.length], ...o })) : defaults
}

describe('useCronJobs', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mountedCallbacks.length = 0
    unmountedCallbacks.length = 0
    mockFetch.mockReset()
    // Default: fetch returns empty array
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })

  afterEach(() => {
    // Run unmounted callbacks to clean up intervals
    unmountedCallbacks.forEach(cb => cb())
    vi.useRealTimers()
  })

  it('should initialize with loading=true and empty jobs', () => {
    // Make fetch hang so loading stays true during sync check
    mockFetch.mockReturnValue(new Promise(() => {}))
    const { jobs, loading } = useCronJobs(5000)
    // Before the first fetch resolves, loading should be true
    expect(loading.value).toBe(true)
    expect(jobs.value).toEqual([])
  })

  it('should set loading=false after refresh completes', async () => {
    const mockJobs = makeMockJobs()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    const { loading, jobs, refresh } = useCronJobs(5000)
    await refresh()
    expect(loading.value).toBe(false)
    expect(jobs.value).toHaveLength(3)
  })

  it('should compute activeCount, pausedCount, errorCount correctly', async () => {
    const mockJobs = makeMockJobs()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    const { activeCount, pausedCount, errorCount, refresh } = useCronJobs(5000)
    await refresh()
    // Job A: enabled=true, status=ok -> active
    // Job B: enabled=false -> paused
    // Job C: enabled=true, status=error -> error
    expect(activeCount.value).toBe(1)
    expect(pausedCount.value).toBe(1)
    expect(errorCount.value).toBe(1)
  })

  it('should call pause API when toggling an enabled job', async () => {
    const mockJobs = makeMockJobs()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    const { refresh, toggle } = useCronJobs(5000)
    await refresh()
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    await toggle(mockJobs[0]) // enabled=true -> should call pause
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scheduler/tasks/1/pause',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('should call resume API when toggling a disabled job', async () => {
    const mockJobs = makeMockJobs()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    const { refresh, toggle } = useCronJobs(5000)
    await refresh()
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockJobs),
    })
    await toggle(mockJobs[1]) // enabled=false -> should call resume
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scheduler/tasks/2/resume',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('should clean up interval on unmount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    useCronJobs(5000)
    // Trigger unmount
    unmountedCallbacks.forEach(cb => cb())
    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })

  it('should call remove API with DELETE method', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeMockJobs()),
    })
    const { refresh, remove } = useCronJobs(5000)
    await refresh()
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
    await remove('1')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scheduler/tasks/1',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('should call run API with POST method', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeMockJobs()),
    })
    const { refresh, run } = useCronJobs(5000)
    await refresh()
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeMockJobs()),
    })
    await run('1')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scheduler/tasks/1/run',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('should call retry API with POST method', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeMockJobs()),
    })
    const { refresh, retry } = useCronJobs(5000)
    await refresh()
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeMockJobs()),
    })
    await retry('3')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/scheduler/tasks/3/retry',
      expect.objectContaining({ method: 'POST' })
    )
  })
})
