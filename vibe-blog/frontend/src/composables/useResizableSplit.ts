import { ref, onUnmounted, getCurrentInstance } from 'vue'

export interface UseResizableSplitOptions {
  defaultRatio?: number
  minRatio?: number
  maxRatio?: number
  storageKey?: string
}

export interface UseResizableSplitReturn {
  splitRatio: Ref<number>
  setSplitRatio: (ratio: number) => void
  resetRatio: () => void
  handlePointerDown: (e: PointerEvent) => void
}

import type { Ref } from 'vue'

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function readFromStorage(key: string | undefined, fallback: number): number {
  if (!key) return fallback
  try {
    const stored = localStorage.getItem(key)
    if (stored === null) return fallback
    const parsed = parseFloat(stored)
    return isNaN(parsed) ? fallback : parsed
  } catch {
    return fallback
  }
}

function writeToStorage(key: string | undefined, value: number): void {
  if (!key) return
  try {
    localStorage.setItem(key, String(value))
  } catch {
    // Silently ignore storage errors
  }
}

export function useResizableSplit(options: UseResizableSplitOptions = {}): UseResizableSplitReturn {
  const {
    defaultRatio = 50,
    minRatio = 20,
    maxRatio = 80,
    storageKey,
  } = options

  const initial = clamp(readFromStorage(storageKey, defaultRatio), minRatio, maxRatio)
  const splitRatio = ref(initial)

  let rafId: number | null = null
  let containerRect: DOMRect | null = null

  function setSplitRatio(ratio: number) {
    splitRatio.value = clamp(ratio, minRatio, maxRatio)
  }

  function resetRatio() {
    splitRatio.value = defaultRatio
    writeToStorage(storageKey, defaultRatio)
  }

  function onPointerMove(e: PointerEvent) {
    if (!containerRect) return
    if (rafId !== null) return // rAF throttle

    rafId = requestAnimationFrame(() => {
      rafId = null
      if (!containerRect) return
      const x = e.clientX - containerRect.left
      const ratio = (x / containerRect.width) * 100
      setSplitRatio(ratio)
    })
  }

  function onPointerUp() {
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
    containerRect = null
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    document.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('pointerup', onPointerUp)
    writeToStorage(storageKey, splitRatio.value)
  }

  function handlePointerDown(e: PointerEvent) {
    const target = e.currentTarget as HTMLElement
    const container = target.parentElement
    if (!container) return

    containerRect = container.getBoundingClientRect()
    target.setPointerCapture(e.pointerId)

    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'

    document.addEventListener('pointermove', onPointerMove)
    document.addEventListener('pointerup', onPointerUp)
  }

  if (getCurrentInstance()) {
    onUnmounted(() => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId)
      }
      document.removeEventListener('pointermove', onPointerMove)
      document.removeEventListener('pointerup', onPointerUp)
    })
  }

  return {
    splitRatio,
    setSplitRatio,
    resetRatio,
    handlePointerDown,
  }
}
