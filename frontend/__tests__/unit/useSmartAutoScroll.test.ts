import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'
import { useSmartAutoScroll } from '@/composables/useSmartAutoScroll'

function createMockContainer(overrides: Partial<HTMLElement> = {}) {
  return {
    scrollTop: 0,
    scrollHeight: 1000,
    clientHeight: 400,
    scrollTo: vi.fn(),
    ...overrides,
  } as unknown as HTMLElement
}

describe('useSmartAutoScroll', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns isFollowing as true initially', () => {
    const containerRef = ref<HTMLElement | null>(null)
    const source = ref(0)
    const { isFollowing } = useSmartAutoScroll({
      containerRef,
      source: () => source.value,
    })
    expect(isFollowing.value).toBe(true)
  })

  it('returns scrollToBottom function', () => {
    const containerRef = ref<HTMLElement | null>(null)
    const source = ref(0)
    const { scrollToBottom } = useSmartAutoScroll({
      containerRef,
      source: () => source.value,
    })
    expect(typeof scrollToBottom).toBe('function')
  })

  it('scrollToBottom scrolls container to bottom and sets isFollowing true', () => {
    const mockEl = createMockContainer({ scrollHeight: 2000 })
    const containerRef = ref<HTMLElement | null>(mockEl)
    const source = ref(0)
    const { scrollToBottom, isFollowing } = useSmartAutoScroll({
      containerRef,
      source: () => source.value,
    })

    isFollowing.value = false
    scrollToBottom()

    expect(mockEl.scrollTo).toHaveBeenCalledWith({ top: 2000, behavior: 'smooth' })
    expect(isFollowing.value).toBe(true)
  })

  it('scrollToBottom does nothing when container is null', () => {
    const containerRef = ref<HTMLElement | null>(null)
    const source = ref(0)
    const { scrollToBottom } = useSmartAutoScroll({
      containerRef,
      source: () => source.value,
    })

    // Should not throw
    scrollToBottom()
  })

  it('auto-scrolls when source changes and user is near bottom', async () => {
    const mockEl = createMockContainer({
      scrollTop: 500,
      scrollHeight: 1000,
      clientHeight: 400,
    })
    // distance = 1000 - 500 - 400 = 100, which is < 200 threshold
    const containerRef = ref<HTMLElement | null>(mockEl)
    const source = ref(0)

    useSmartAutoScroll({
      containerRef,
      source: () => source.value,
      threshold: 200,
    })

    source.value = 1
    await nextTick()
    await nextTick()

    expect(mockEl.scrollTo).toHaveBeenCalled()
  })

  it('does not auto-scroll when user has scrolled up beyond threshold', async () => {
    const mockEl = createMockContainer({
      scrollTop: 100,
      scrollHeight: 1000,
      clientHeight: 400,
    })
    // distance = 1000 - 100 - 400 = 500, which is > 200 threshold
    const containerRef = ref<HTMLElement | null>(mockEl)
    const source = ref(0)

    useSmartAutoScroll({
      containerRef,
      source: () => source.value,
      threshold: 200,
    })

    source.value = 1
    await nextTick()
    await nextTick()

    expect(mockEl.scrollTo).not.toHaveBeenCalled()
  })

  it('respects custom behavior option', () => {
    const mockEl = createMockContainer({ scrollHeight: 2000 })
    const containerRef = ref<HTMLElement | null>(mockEl)
    const source = ref(0)
    const { scrollToBottom } = useSmartAutoScroll({
      containerRef,
      source: () => source.value,
      behavior: 'instant',
    })

    scrollToBottom()
    expect(mockEl.scrollTo).toHaveBeenCalledWith({ top: 2000, behavior: 'instant' })
  })
})
