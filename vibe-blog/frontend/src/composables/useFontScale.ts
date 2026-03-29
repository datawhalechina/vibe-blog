import { ref, computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'

const FONT_SCALE_DEFAULT = 1
const FONT_SCALE_MIN = 0.8
const FONT_SCALE_MAX = 1.5
const FONT_SCALE_STEP = 0.05
const STORAGE_KEY = 'vibe-blog-font-scale'

export interface UseFontScaleReturn {
  fontScale: Ref<number>
  formattedScale: ComputedRef<string>
  setFontScale: (scale: number) => void
  stepUp: () => void
  stepDown: () => void
  reset: () => void
  isDefault: ComputedRef<boolean>
  canStepUp: ComputedRef<boolean>
  canStepDown: ComputedRef<boolean>
}

function readScale(): number {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === null) return FONT_SCALE_DEFAULT
    const parsed = parseFloat(stored)
    return isNaN(parsed) ? FONT_SCALE_DEFAULT : parsed
  } catch {
    return FONT_SCALE_DEFAULT
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function round(value: number): number {
  return Math.round(value * 100) / 100
}

function applyScale(scale: number) {
  document.documentElement.style.setProperty('--font-scale', String(scale))
  try {
    localStorage.setItem(STORAGE_KEY, String(scale))
  } catch {
    // Silently ignore
  }
}

export function useFontScale(): UseFontScaleReturn {
  const fontScale = ref(readScale())

  // Apply initial scale
  applyScale(fontScale.value)

  const formattedScale = computed(() => `${Math.round(fontScale.value * 100)}%`)
  const isDefault = computed(() => fontScale.value === FONT_SCALE_DEFAULT)
  const canStepUp = computed(() => fontScale.value < FONT_SCALE_MAX)
  const canStepDown = computed(() => fontScale.value > FONT_SCALE_MIN)

  function setFontScale(scale: number) {
    fontScale.value = round(clamp(scale, FONT_SCALE_MIN, FONT_SCALE_MAX))
    applyScale(fontScale.value)
  }

  function stepUp() {
    if (!canStepUp.value) return
    setFontScale(fontScale.value + FONT_SCALE_STEP)
  }

  function stepDown() {
    if (!canStepDown.value) return
    setFontScale(fontScale.value - FONT_SCALE_STEP)
  }

  function reset() {
    setFontScale(FONT_SCALE_DEFAULT)
  }

  return {
    fontScale,
    formattedScale,
    setFontScale,
    stepUp,
    stepDown,
    reset,
    isDefault,
    canStepUp,
    canStepDown,
  }
}
