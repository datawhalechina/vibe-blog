import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref, nextTick } from 'vue'

// Mock rAF/cAF before importing the composable
let rafCallbacks: Array<{ id: number; cb: FrameRequestCallback }> = []
let rafIdCounter = 0

vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
  const id = ++rafIdCounter
  rafCallbacks.push({ id, cb })
  return id
})

vi.stubGlobal('cancelAnimationFrame', (id: number) => {
  rafCallbacks = rafCallbacks.filter((r) => r.id !== id)
})

function flushRaf(times = 1) {
  for (let i = 0; i < times; i++) {
    const pending = [...rafCallbacks]
    rafCallbacks = []
    pending.forEach((r) => r.cb(performance.now()))
  }
}

function flushAllRaf(maxIterations = 200) {
  let iterations = 0
  while (rafCallbacks.length > 0 && iterations < maxIterations) {
    flushRaf()
    iterations++
  }
}

import { useTypingAnimation } from '@/composables/useTypingAnimation'

describe('useTypingAnimation', () => {
  beforeEach(() => {
    rafCallbacks = []
    rafIdCounter = 0
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows initial content immediately without animation (first load)', async () => {
    const content = ref('Hello World')
    const { displayedContent, isAnimating } = useTypingAnimation({ content })

    await nextTick()
    // First load: displayedContent was empty, content has value -> skip animation
    expect(displayedContent.value).toBe('Hello World')
    expect(isAnimating.value).toBe(false)
  })

  it('animates when content grows by small increments', async () => {
    const content = ref('Hi')
    const { displayedContent, isAnimating } = useTypingAnimation({ content, speed: 60 })

    await nextTick()
    // First load -> immediate
    expect(displayedContent.value).toBe('Hi')

    content.value = 'Hi there'
    await nextTick()

    // Should be animating, not yet fully caught up
    expect(isAnimating.value).toBe(true)
    expect(displayedContent.value.length).toBeLessThan('Hi there'.length)

    // Flush enough rAF frames to finish
    flushAllRaf()
    expect(displayedContent.value).toBe('Hi there')
    expect(isAnimating.value).toBe(false)
  })

  it('skips animation when increment exceeds skipThreshold', async () => {
    const content = ref('A')
    const { displayedContent } = useTypingAnimation({
      content,
      skipThreshold: 10,
    })

    await nextTick()
    expect(displayedContent.value).toBe('A')

    // Set content to something much longer than threshold
    content.value = 'A' + 'B'.repeat(50)
    await nextTick()

    // Should skip animation and show immediately
    expect(displayedContent.value).toBe(content.value)
  })

  it('skips animation when content becomes shorter', async () => {
    const content = ref('Hello World')
    const { displayedContent } = useTypingAnimation({ content })

    await nextTick()
    expect(displayedContent.value).toBe('Hello World')

    content.value = 'Hi'
    await nextTick()

    // Content got shorter -> skip animation
    expect(displayedContent.value).toBe('Hi')
  })

  it('flush() immediately shows latest content', async () => {
    const content = ref('Start')
    const { displayedContent, flush } = useTypingAnimation({ content, speed: 10 })

    await nextTick()
    expect(displayedContent.value).toBe('Start')

    content.value = 'Start and more text'
    await nextTick()

    // Don't flush rAF, call flush() instead
    flush()
    expect(displayedContent.value).toBe('Start and more text')
  })

  it('directly displays content when enabled is false', async () => {
    const content = ref('Hello')
    const enabled = ref(false)
    const { displayedContent, isAnimating } = useTypingAnimation({
      content,
      enabled,
    })

    await nextTick()
    expect(displayedContent.value).toBe('Hello')

    content.value = 'Hello World'
    await nextTick()

    // Should show immediately, no animation
    expect(displayedContent.value).toBe('Hello World')
    expect(isAnimating.value).toBe(false)
  })

  it('cleans up rAF on unmount', async () => {
    const cancelCalls: number[] = []
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      cancelCalls.push(id)
      rafCallbacks = rafCallbacks.filter((r) => r.id !== id)
    })

    const { createApp, defineComponent, ref: vRef, nextTick: vNextTick } = await import('vue')

    const contentRef = vRef('Hi')
    const app = createApp(
      defineComponent({
        setup() {
          useTypingAnimation({ content: contentRef })
          return {}
        },
        template: '<div></div>',
      })
    )
    const el = document.createElement('div')
    app.mount(el)

    // Trigger an animation so there's a pending rAF
    contentRef.value = 'Hi there'
    await vNextTick()

    // There should be a pending rAF now
    expect(rafCallbacks.length).toBeGreaterThan(0)

    app.unmount()
    // cancelAnimationFrame should have been called during cleanup
    expect(cancelCalls.length).toBeGreaterThan(0)
  })

  it('continues chasing when content changes during animation', async () => {
    const content = ref('AB')
    const { displayedContent } = useTypingAnimation({ content, speed: 60 })

    await nextTick()
    expect(displayedContent.value).toBe('AB')

    content.value = 'ABCD'
    await nextTick()

    // Flush one frame (partial)
    flushRaf()

    // Now content changes again while still animating
    content.value = 'ABCDEF'
    await nextTick()

    // Flush all remaining frames
    flushAllRaf()
    expect(displayedContent.value).toBe('ABCDEF')
  })
})
