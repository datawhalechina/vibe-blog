import { effectScope, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useCitationInteractions } from '@/composables/useCitationInteractions'
import type { Citation } from '@/utils/citationMatcher'

const citation: Citation = {
  url: 'https://example.com/article',
  title: 'Article',
  domain: 'example.com',
  snippet: 'Source summary',
}

function createFixture() {
  const container = document.createElement('div')
  container.innerHTML = '<a href="https://example.com/article">source</a>'
  const reference = document.createElement('div')
  reference.id = 'ref-1'
  reference.scrollIntoView = vi.fn()
  document.body.append(container, reference)
  return {
    container,
    link: container.querySelector('a')!,
    reference,
  }
}

describe('useCitationInteractions', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('shows and hides the matched citation using the existing delays', async () => {
    vi.useFakeTimers()
    const { container, link } = createFixture()
    vi.spyOn(link, 'getBoundingClientRect').mockReturnValue({
      top: 10,
      bottom: 30,
      left: 20,
      right: 80,
      width: 60,
      height: 20,
      x: 20,
      y: 10,
      toJSON: () => ({}),
    })
    const interactions = useCitationInteractions({
      previewRef: ref(container),
      renderedHtml: ref('<a>source</a>'),
      citations: ref([citation]),
    })
    interactions.setupCitationHover()

    link.dispatchEvent(new MouseEvent('mouseenter'))
    await vi.advanceTimersByTimeAsync(199)
    expect(interactions.tooltipVisible.value).toBe(false)
    await vi.advanceTimersByTimeAsync(1)

    expect(interactions.tooltipVisible.value).toBe(true)
    expect(interactions.tooltipCitation.value).toEqual(citation)
    expect(interactions.tooltipIndex.value).toBe(1)
    expect(interactions.tooltipPosition.value).toEqual({ top: 38, left: 20 })

    link.dispatchEvent(new MouseEvent('mouseleave'))
    await vi.advanceTimersByTimeAsync(100)
    expect(interactions.tooltipVisible.value).toBe(false)
  })

  it('scrolls to the matching reference and prevents link navigation', () => {
    const { container, link, reference } = createFixture()
    const interactions = useCitationInteractions({
      previewRef: ref(container),
      renderedHtml: ref('content'),
      citations: ref([citation]),
    })
    interactions.setupCitationHover()
    const event = new MouseEvent('click', { cancelable: true })

    link.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(reference.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'start',
    })
  })

  it('replaces old listeners when citation links are rescanned', () => {
    const { container, link, reference } = createFixture()
    const interactions = useCitationInteractions({
      previewRef: ref(container),
      renderedHtml: ref('content'),
      citations: ref([citation]),
    })

    interactions.setupCitationHover()
    interactions.setupCitationHover()
    link.dispatchEvent(new MouseEvent('click', { cancelable: true }))

    expect(reference.scrollIntoView).toHaveBeenCalledOnce()
  })

  it('cancels pending hover timers when citation links are rescanned', async () => {
    vi.useFakeTimers()
    const { container, link } = createFixture()
    const interactions = useCitationInteractions({
      previewRef: ref(container),
      renderedHtml: ref('content'),
      citations: ref([citation]),
    })
    interactions.setupCitationHover()
    link.dispatchEvent(new MouseEvent('mouseenter'))

    interactions.setupCitationHover()
    await vi.advanceTimersByTimeAsync(200)

    expect(interactions.tooltipVisible.value).toBe(false)
  })

  it('rescans after rendered content changes', async () => {
    vi.useFakeTimers()
    const { container, link } = createFixture()
    const renderedHtml = ref('before')
    const interactions = useCitationInteractions({
      previewRef: ref(container),
      renderedHtml,
      citations: ref([citation]),
      showDelayMs: 0,
    })

    renderedHtml.value = 'after'
    await nextTick()
    await nextTick()
    link.dispatchEvent(new MouseEvent('mouseenter'))
    await vi.runAllTimersAsync()

    expect(interactions.tooltipVisible.value).toBe(true)
  })

  it('clears timers and DOM listeners when its scope is disposed', async () => {
    vi.useFakeTimers()
    const { container, link, reference } = createFixture()
    const scope = effectScope()
    const interactions = scope.run(() => useCitationInteractions({
      previewRef: ref(container),
      renderedHtml: ref('content'),
      citations: ref([citation]),
    }))!
    interactions.setupCitationHover()

    link.dispatchEvent(new MouseEvent('mouseenter'))
    scope.stop()
    await vi.runAllTimersAsync()
    link.dispatchEvent(new MouseEvent('click', { cancelable: true }))

    expect(interactions.tooltipVisible.value).toBe(false)
    expect(reference.scrollIntoView).not.toHaveBeenCalled()
  })

  it('does not bind listeners from a queued rescan after disposal', async () => {
    const { container, link, reference } = createFixture()
    const renderedHtml = ref('before')
    const scope = effectScope()
    scope.run(() => useCitationInteractions({
      previewRef: ref(container),
      renderedHtml,
      citations: ref([citation]),
    }))

    renderedHtml.value = 'after'
    await nextTick()
    scope.stop()
    await nextTick()
    link.dispatchEvent(new MouseEvent('click', { cancelable: true }))

    expect(reference.scrollIntoView).not.toHaveBeenCalled()
  })
})
