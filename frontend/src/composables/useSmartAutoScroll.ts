import { ref, watch, nextTick, toValue, type Ref, type WatchSource } from 'vue'

interface UseSmartAutoScrollOptions {
  containerRef: Ref<HTMLElement | null>
  source: WatchSource
  enabled?: Ref<boolean> | boolean
  threshold?: number
  behavior?: ScrollBehavior
}

interface UseSmartAutoScrollReturn {
  isFollowing: Ref<boolean>
  scrollToBottom: () => void
}

export function useSmartAutoScroll({
  containerRef,
  source,
  enabled = true,
  threshold = 200,
  behavior = 'smooth',
}: UseSmartAutoScrollOptions): UseSmartAutoScrollReturn {
  const isFollowing = ref(true)

  watch(source, async () => {
    if (!toValue(enabled)) return
    await nextTick()
    const container = containerRef.value
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceToBottom = scrollHeight - scrollTop - clientHeight
    isFollowing.value = distanceToBottom < threshold

    if (isFollowing.value) {
      container.scrollTo({ top: scrollHeight, behavior })
    }
  })

  const scrollToBottom = () => {
    const container = containerRef.value
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior })
      isFollowing.value = true
    }
  }

  return { isFollowing, scrollToBottom }
}
