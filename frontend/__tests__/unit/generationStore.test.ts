import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGenerationStore } from '../../src/stores/generation'

describe('useGenerationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts in idle stage', () => {
    const store = useGenerationStore()
    expect(store.stage).toBe('idle')
    expect(store.isRunning).toBe(false)
  })

  it('handleStageChange updates stage and adds log', () => {
    const store = useGenerationStore()
    store.handleStageChange('researching')
    expect(store.stage).toBe('researching')
    expect(store.isRunning).toBe(true)
    expect(store.logs.length).toBeGreaterThan(0)
    expect(store.startTime).toBeGreaterThan(0)
  })

  it('handleTaskUpdate creates new task', () => {
    const store = useGenerationStore()
    store.handleTaskUpdate('t1', { label: 'Search', status: 'running' })
    expect(store.tasks['t1']).toBeDefined()
    expect(store.tasks['t1'].status).toBe('running')
    expect(store.activeTaskIds).toContain('t1')
  })

  it('handleTaskUpdate removes from active on completion', () => {
    const store = useGenerationStore()
    store.handleTaskUpdate('t1', { status: 'running' })
    store.handleTaskUpdate('t1', { status: 'completed' })
    expect(store.activeTaskIds).not.toContain('t1')
    expect(store.completedTasks).toBe(1)
  })

  it('handleProgress updates progress', () => {
    const store = useGenerationStore()
    store.handleProgress(3, 10)
    expect(store.progress).toEqual({ current: 3, total: 10 })
  })

  it('reset clears all state', () => {
    const store = useGenerationStore()
    store.handleStageChange('writing')
    store.handleTaskUpdate('t1', { status: 'running' })
    store.addLog('test')
    store.reset()
    expect(store.stage).toBe('idle')
    expect(Object.keys(store.tasks)).toHaveLength(0)
    expect(store.logs).toHaveLength(0)
  })

  it('addLog creates entry with correct type', () => {
    const store = useGenerationStore()
    store.addLog('hello', 'warning')
    expect(store.logs[0].type).toBe('warning')
    expect(store.logs[0].content).toBe('hello')
  })

  it('completed stage is not running', () => {
    const store = useGenerationStore()
    store.handleStageChange('completed')
    expect(store.isRunning).toBe(false)
  })
})
