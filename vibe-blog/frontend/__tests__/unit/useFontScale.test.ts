import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFontScale } from '@/composables/useFontScale'

describe('useFontScale', () => {
  beforeEach(() => {
    localStorage.clear()
    // Reset CSS custom property
    document.documentElement.style.removeProperty('--font-scale')
    vi.restoreAllMocks()
  })

  it('defaults scale to 1', () => {
    const { fontScale } = useFontScale()
    expect(fontScale.value).toBe(1)
  })

  it('restores scale from localStorage', () => {
    localStorage.setItem('vibe-blog-font-scale', '1.2')
    const { fontScale } = useFontScale()
    expect(fontScale.value).toBe(1.2)
  })

  it('stepUp increases by 0.05', () => {
    const { fontScale, stepUp } = useFontScale()
    stepUp()
    expect(fontScale.value).toBeCloseTo(1.05)
  })

  it('stepDown decreases by 0.05', () => {
    const { fontScale, stepDown } = useFontScale()
    stepDown()
    expect(fontScale.value).toBeCloseTo(0.95)
  })

  it('does not exceed max (1.5)', () => {
    const { fontScale, setFontScale, stepUp } = useFontScale()
    setFontScale(1.5)
    stepUp()
    expect(fontScale.value).toBe(1.5)
  })

  it('does not go below min (0.8)', () => {
    const { fontScale, setFontScale, stepDown } = useFontScale()
    setFontScale(0.8)
    stepDown()
    expect(fontScale.value).toBe(0.8)
  })

  it('reset restores to default 1', () => {
    const { fontScale, setFontScale, reset } = useFontScale()
    setFontScale(1.3)
    expect(fontScale.value).toBe(1.3)
    reset()
    expect(fontScale.value).toBe(1)
  })

  it('formattedScale shows percentage', () => {
    const { formattedScale } = useFontScale()
    expect(formattedScale.value).toBe('100%')
  })

  it('formattedScale updates after stepUp', () => {
    const { formattedScale, stepUp } = useFontScale()
    stepUp()
    expect(formattedScale.value).toBe('105%')
  })

  it('canStepUp is false at max', () => {
    const { canStepUp, setFontScale } = useFontScale()
    setFontScale(1.5)
    expect(canStepUp.value).toBe(false)
  })

  it('canStepDown is false at min', () => {
    const { canStepDown, setFontScale } = useFontScale()
    setFontScale(0.8)
    expect(canStepDown.value).toBe(false)
  })

  it('isDefault is true at scale 1', () => {
    const { isDefault } = useFontScale()
    expect(isDefault.value).toBe(true)
  })

  it('isDefault is false when scale is not 1', () => {
    const { isDefault, stepUp } = useFontScale()
    stepUp()
    expect(isDefault.value).toBe(false)
  })

  it('sets CSS custom property on document', () => {
    const { setFontScale } = useFontScale()
    setFontScale(1.2)
    expect(document.documentElement.style.getPropertyValue('--font-scale')).toBe('1.2')
  })

  it('persists to localStorage', () => {
    const { setFontScale } = useFontScale()
    setFontScale(1.15)
    expect(localStorage.getItem('vibe-blog-font-scale')).toBe('1.15')
  })
})
