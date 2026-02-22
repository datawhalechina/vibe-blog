import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useResizableSplit } from '@/composables/useResizableSplit'

describe('useResizableSplit', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('defaults ratio to 50', () => {
    const { splitRatio } = useResizableSplit()
    expect(splitRatio.value).toBe(50)
  })

  it('uses custom defaultRatio', () => {
    const { splitRatio } = useResizableSplit({ defaultRatio: 60 })
    expect(splitRatio.value).toBe(60)
  })

  it('restores ratio from localStorage', () => {
    localStorage.setItem('test-split', '65')
    const { splitRatio } = useResizableSplit({ storageKey: 'test-split' })
    expect(splitRatio.value).toBe(65)
  })

  it('ignores invalid localStorage value and uses default', () => {
    localStorage.setItem('test-split', 'not-a-number')
    const { splitRatio } = useResizableSplit({ storageKey: 'test-split' })
    expect(splitRatio.value).toBe(50)
  })

  it('setSplitRatio updates the value', () => {
    const { splitRatio, setSplitRatio } = useResizableSplit()
    setSplitRatio(70)
    expect(splitRatio.value).toBe(70)
  })

  it('setSplitRatio clamps to min', () => {
    const { splitRatio, setSplitRatio } = useResizableSplit({ minRatio: 20 })
    setSplitRatio(10)
    expect(splitRatio.value).toBe(20)
  })

  it('setSplitRatio clamps to max', () => {
    const { splitRatio, setSplitRatio } = useResizableSplit({ maxRatio: 80 })
    setSplitRatio(90)
    expect(splitRatio.value).toBe(80)
  })

  it('resetRatio restores default', () => {
    const { splitRatio, setSplitRatio, resetRatio } = useResizableSplit({ defaultRatio: 50 })
    setSplitRatio(70)
    expect(splitRatio.value).toBe(70)
    resetRatio()
    expect(splitRatio.value).toBe(50)
  })

  it('handlePointerDown returns a function', () => {
    const { handlePointerDown } = useResizableSplit()
    expect(typeof handlePointerDown).toBe('function')
  })
})
