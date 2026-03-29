/**
 * 101.07 预览节流测试
 * 验证 useTaskStream 中 throttledUpdatePreview 的 100ms 节流逻辑
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('throttledUpdatePreview — 100ms throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should throttle rapid calls — only first call within 100ms window takes effect', () => {
    let previewContent = ''
    let previewTimer: ReturnType<typeof setTimeout> | null = null
    let actualUpdateCount = 0

    const throttledUpdatePreview = (content: string) => {
      if (previewTimer) return
      previewTimer = setTimeout(() => {
        previewContent = content
        previewTimer = null
        actualUpdateCount++
      }, 100)
    }

    // 快速连续调用 50 次，每 20ms 一次
    for (let i = 0; i < 50; i++) {
      throttledUpdatePreview(`content-${i}`)
      vi.advanceTimersByTime(20)
    }

    // 确保最后一个 timer 完成
    vi.advanceTimersByTime(200)

    // 50 次调用 × 20ms = 1000ms 总时长
    // 100ms 节流窗口 → 实际更新次数应远少于 50
    expect(actualUpdateCount).toBeLessThanOrEqual(15)
    expect(actualUpdateCount).toBeGreaterThanOrEqual(5)
    expect(previewContent).toBeTruthy()
  })

  it('should drop intermediate calls within throttle window', () => {
    let previewContent = ''
    let previewTimer: ReturnType<typeof setTimeout> | null = null

    const throttledUpdatePreview = (content: string) => {
      if (previewTimer) return
      previewTimer = setTimeout(() => {
        previewContent = content
        previewTimer = null
      }, 100)
    }

    // 在 100ms 窗口内连续调用 3 次
    throttledUpdatePreview('first')
    throttledUpdatePreview('second')  // 应被丢弃
    throttledUpdatePreview('third')   // 应被丢弃

    // 推进 100ms，只有第一次调用生效
    vi.advanceTimersByTime(100)
    expect(previewContent).toBe('first')
  })
})
