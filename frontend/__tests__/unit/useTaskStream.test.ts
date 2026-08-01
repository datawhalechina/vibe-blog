/**
 * 101.03 useTaskStream composable 测试
 * 测试初始化、添加进度项、带数据添加、累积预览、重置
 */
import { describe, it, expect, vi } from 'vitest'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {} })),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}))

// Mock api module
vi.mock('@/services/api', () => ({
  createTaskStream: vi.fn(),
  confirmOutline: vi.fn(),
  cancelTask: vi.fn(),
}))

import { useTaskStream } from '@/composables/useTaskStream'
import * as api from '@/services/api'

class FakeEventSource {
  readyState = 1
  close = vi.fn()
  onerror: (() => void) | null = null
  listeners = new Map<string, Array<(event: MessageEvent) => void>>()

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    const listeners = this.listeners.get(type) || []
    listeners.push(listener)
    this.listeners.set(type, listeners)
  }

  emit(type: string, data: unknown = {}) {
    const event = { data: JSON.stringify(data) } as MessageEvent
    for (const listener of this.listeners.get(type) || []) listener(event)
  }
}

describe('useTaskStream', () => {
  it('should initialize with default state', () => {
    const stream = useTaskStream()
    expect(stream.isLoading.value).toBe(false)
    expect(stream.showProgress.value).toBe(false)
    expect(stream.progressItems.value).toHaveLength(0)
    expect(stream.progressText.value).toBe('')
    expect(stream.statusBadge.value).toBe('')
    expect(stream.currentTaskId.value).toBe('')
    expect(stream.previewContent.value).toBe('')
    expect(stream.outlineData.value).toBeNull()
    expect(stream.waitingForOutline.value).toBe(false)
    expect(stream.citations.value).toHaveLength(0)
    expect(stream.completedBlogId.value).toBe('')
  })

  it('should add progress item with message and type', () => {
    const stream = useTaskStream()
    stream.addProgressItem('Test message', 'info')
    expect(stream.progressItems.value).toHaveLength(1)
    expect(stream.progressItems.value[0].message).toBe('Test message')
    expect(stream.progressItems.value[0].type).toBe('info')
    expect(stream.progressItems.value[0].time).toBeTruthy()
  })

  it('should add progress item with data', () => {
    const stream = useTaskStream()
    const data = { query: 'test', results: [] }
    stream.progressItems.value.push({
      time: new Date().toLocaleTimeString(),
      message: 'Search results',
      type: 'search',
      data,
    })
    expect(stream.progressItems.value).toHaveLength(1)
    expect(stream.progressItems.value[0].data).toEqual(data)
  })

  it('should accumulate preview content', () => {
    const stream = useTaskStream()
    // Simulate setting preview content directly
    stream.previewContent.value = '## Section 1\n\nContent here'
    expect(stream.previewContent.value).toContain('Section 1')

    stream.previewContent.value += '\n\n## Section 2\n\nMore content'
    expect(stream.previewContent.value).toContain('Section 2')
  })

  it('should reset all state', () => {
    const stream = useTaskStream()
    // Set some state
    stream.isLoading.value = true
    stream.showProgress.value = true
    stream.addProgressItem('test', 'info')
    stream.progressText.value = 'loading...'
    stream.statusBadge.value = '运行中'
    stream.currentTaskId.value = 'task-123'
    stream.previewContent.value = '# Content'
    stream.outlineData.value = { title: 'Test', sections_titles: [], sections: [] }
    stream.waitingForOutline.value = true
    stream.completedBlogId.value = 'blog-1'

    // Reset
    stream.reset()

    expect(stream.isLoading.value).toBe(false)
    expect(stream.showProgress.value).toBe(false)
    expect(stream.progressItems.value).toHaveLength(0)
    expect(stream.progressText.value).toBe('')
    expect(stream.statusBadge.value).toBe('')
    expect(stream.currentTaskId.value).toBe('')
    expect(stream.previewContent.value).toBe('')
    expect(stream.outlineData.value).toBeNull()
    expect(stream.waitingForOutline.value).toBe(false)
    expect(stream.completedBlogId.value).toBe('')
  })

  it('closes the previous connection before reconnecting', () => {
    const first = new FakeEventSource()
    const second = new FakeEventSource()
    vi.mocked(api.createTaskStream)
      .mockReturnValueOnce(first as unknown as EventSource)
      .mockReturnValueOnce(second as unknown as EventSource)
    const stream = useTaskStream()

    stream.connectSSE('task-1')
    stream.connectSSE('task-2')

    expect(first.close).toHaveBeenCalledOnce()
    expect(second.close).not.toHaveBeenCalled()
  })

  it('renders and forwards nested Storybook outputs without fabricating an ID', () => {
    const source = new FakeEventSource()
    vi.mocked(api.createTaskStream).mockReturnValue(
      source as unknown as EventSource,
    )
    const onComplete = vi.fn()
    const stream = useTaskStream()

    stream.connectSSE('storybook-task', onComplete)
    source.emit('complete', {
      task_id: 'storybook-task',
      status: 'completed',
      outputs: {
        title: '缓存小镇历险记',
        pages: [
          { page_number: 1, title: '第一页', content: '页面正文' },
        ],
      },
    })

    expect(stream.previewContent.value).toContain('# 缓存小镇历险记')
    expect(stream.previewContent.value).toContain('## 第 1 页：第一页')
    expect(stream.completedBlogId.value).toBe('')
    expect(onComplete).toHaveBeenCalledWith({
      title: '缓存小镇历险记',
      pages: [
        { page_number: 1, title: '第一页', content: '页面正文' },
      ],
    })
    expect(source.close).toHaveBeenCalledOnce()
  })

  it('preserves top-level blog completion behavior', () => {
    const source = new FakeEventSource()
    vi.mocked(api.createTaskStream).mockReturnValue(
      source as unknown as EventSource,
    )
    const onComplete = vi.fn()
    const stream = useTaskStream()

    stream.connectSSE('blog-task', onComplete)
    source.emit('complete', {
      id: 'blog-1',
      markdown: '# Existing blog',
      saved_path: '/tmp/blog.md',
    })

    expect(stream.previewContent.value).toBe('# Existing blog')
    expect(stream.completedBlogId.value).toBe('blog-1')
    expect(stream.savedOutputPath.value).toBe('/tmp/blog.md')
    expect(onComplete).toHaveBeenCalledWith({
      id: 'blog-1',
      markdown: '# Existing blog',
      saved_path: '/tmp/blog.md',
    })
    expect(source.close).toHaveBeenCalledOnce()
  })
})
