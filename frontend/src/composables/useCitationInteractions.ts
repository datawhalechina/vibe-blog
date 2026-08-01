import {
  getCurrentScope,
  nextTick,
  onScopeDispose,
  ref,
  watch,
  type Ref,
} from 'vue'

import { scanCitationLinks, type Citation } from '@/utils/citationMatcher'

interface UseCitationInteractionsOptions {
  previewRef: Ref<HTMLElement | null>
  renderedHtml: Ref<string>
  citations: Ref<Citation[]>
  showDelayMs?: number
  hideDelayMs?: number
}

export function useCitationInteractions(options: UseCitationInteractionsOptions) {
  const showDelayMs = options.showDelayMs ?? 200
  const hideDelayMs = options.hideDelayMs ?? 100
  const tooltipVisible = ref(false)
  const tooltipCitation = ref<Citation | null>(null)
  const tooltipIndex = ref(0)
  const tooltipPosition = ref({ top: 0, left: 0 })
  let hoverShowTimer: ReturnType<typeof setTimeout> | null = null
  let hoverHideTimer: ReturnType<typeof setTimeout> | null = null
  let listenerCleanups: Array<() => void> = []
  let disposed = false

  const clearShowTimer = () => {
    if (hoverShowTimer) clearTimeout(hoverShowTimer)
    hoverShowTimer = null
  }

  const clearHideTimer = () => {
    if (hoverHideTimer) clearTimeout(hoverHideTimer)
    hoverHideTimer = null
  }

  const clearListeners = () => {
    listenerCleanups.forEach((cleanup) => cleanup())
    listenerCleanups = []
  }

  const showTooltip = (citation: Citation, index: number, rect: DOMRect) => {
    clearHideTimer()
    clearShowTimer()
    hoverShowTimer = setTimeout(() => {
      tooltipVisible.value = true
      tooltipCitation.value = citation
      tooltipIndex.value = index
      tooltipPosition.value = { top: rect.bottom + 8, left: rect.left }
      hoverShowTimer = null
    }, showDelayMs)
  }

  const hideTooltip = () => {
    clearShowTimer()
    clearHideTimer()
    hoverHideTimer = setTimeout(() => {
      tooltipVisible.value = false
      hoverHideTimer = null
    }, hideDelayMs)
  }

  const setupCitationHover = () => {
    if (disposed) return
    clearListeners()
    clearShowTimer()
    clearHideTimer()
    tooltipVisible.value = false
    const preview = options.previewRef.value
    if (!preview || !options.citations.value.length) return

    const matches = scanCitationLinks(preview, options.citations.value)
    matches.forEach(({ element, citation, index }) => {
      const handleMouseEnter = () => {
        showTooltip(citation, index, element.getBoundingClientRect())
      }
      const handleMouseLeave = () => hideTooltip()
      const handleClick = (event: Event) => {
        const reference = document.getElementById(`ref-${index}`)
        if (!reference) return
        event.preventDefault()
        reference.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }

      element.addEventListener('mouseenter', handleMouseEnter)
      element.addEventListener('mouseleave', handleMouseLeave)
      element.addEventListener('click', handleClick)
      listenerCleanups.push(() => {
        element.removeEventListener('mouseenter', handleMouseEnter)
        element.removeEventListener('mouseleave', handleMouseLeave)
        element.removeEventListener('click', handleClick)
      })
    })
  }

  const stopWatching = watch(
    [options.renderedHtml, options.citations],
    () => { void nextTick(setupCitationHover) },
  )

  const dispose = () => {
    disposed = true
    stopWatching()
    clearListeners()
    clearShowTimer()
    clearHideTimer()
    tooltipVisible.value = false
    tooltipCitation.value = null
  }

  if (getCurrentScope()) onScopeDispose(dispose)

  return {
    tooltipVisible,
    tooltipCitation,
    tooltipIndex,
    tooltipPosition,
    setupCitationHover,
    dispose,
  }
}
