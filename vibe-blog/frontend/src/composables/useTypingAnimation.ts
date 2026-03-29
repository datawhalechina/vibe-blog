import { ref, watch, onUnmounted, getCurrentInstance, toValue, type Ref, type ComputedRef } from 'vue'

export interface UseTypingAnimationOptions {
  content: Ref<string> | ComputedRef<string>
  enabled?: Ref<boolean> | boolean
  speed?: number
  skipThreshold?: number
}

export interface UseTypingAnimationReturn {
  displayedContent: Ref<string>
  isAnimating: Ref<boolean>
  flush: () => void
}

export function useTypingAnimation(options: UseTypingAnimationOptions): UseTypingAnimationReturn {
  const {
    content,
    enabled = true,
    speed = 60,
    skipThreshold = 1000,
  } = options

  const displayedContent = ref('')
  const isAnimating = ref(false)
  let rafId: number | null = null
  let lastTimestamp = 0
  let charDebt = 0

  function cancelRaf() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
  }

  function animate(timestamp: number) {
    const target = content.value
    if (displayedContent.value.length >= target.length) {
      // Caught up
      displayedContent.value = target
      isAnimating.value = false
      rafId = null
      return
    }

    if (lastTimestamp === 0) {
      lastTimestamp = timestamp
    }

    const elapsed = timestamp - lastTimestamp
    lastTimestamp = timestamp

    // Calculate how many chars to add based on elapsed time
    charDebt += (elapsed / 1000) * speed
    // Always advance at least 1 character per frame
    const charsToAdd = Math.max(1, Math.floor(charDebt))
    charDebt = Math.max(0, charDebt - charsToAdd)
    const newLen = Math.min(displayedContent.value.length + charsToAdd, target.length)
    displayedContent.value = target.slice(0, newLen)

    if (displayedContent.value.length < target.length) {
      rafId = requestAnimationFrame(animate)
    } else {
      displayedContent.value = target
      isAnimating.value = false
      rafId = null
    }
  }

  function startAnimation() {
    cancelRaf()
    lastTimestamp = 0
    charDebt = 0
    isAnimating.value = true
    rafId = requestAnimationFrame(animate)
  }

  function flush() {
    cancelRaf()
    displayedContent.value = content.value
    isAnimating.value = false
  }

  watch(
    () => content.value,
    (newVal, oldVal) => {
      if (!toValue(enabled)) {
        // Disabled: show immediately
        displayedContent.value = newVal
        isAnimating.value = false
        cancelRaf()
        return
      }

      const isFirstLoad = displayedContent.value === '' && newVal.length > 0
      const isShrink = newVal.length < displayedContent.value.length
      const increment = newVal.length - displayedContent.value.length
      const isLargeJump = increment > skipThreshold

      if (isFirstLoad || isShrink || isLargeJump) {
        // Skip animation
        cancelRaf()
        displayedContent.value = newVal
        isAnimating.value = false
        return
      }

      // If already animating, just let it continue chasing the new target
      if (isAnimating.value && rafId !== null) {
        return
      }

      // Start animation
      startAnimation()
    },
    { immediate: true }
  )

  if (getCurrentInstance()) {
    onUnmounted(() => {
      cancelRaf()
    })
  }

  return {
    displayedContent,
    isAnimating,
    flush,
  }
}
