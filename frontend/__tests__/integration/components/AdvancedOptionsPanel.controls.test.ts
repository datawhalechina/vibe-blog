/**
 * 101.06 输入框交互增强 — 深度思考/背景调查开关测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AdvancedOptionsPanel from '@/components/home/AdvancedOptionsPanel.vue'

const baseProps = {
  articleType: 'tutorial',
  targetLength: 'mini',
  audienceAdaptation: 'default',
  imageStyle: 'cartoon',
  generateCoverVideo: false,
  videoAspectRatio: '16:9',
  deepThinking: false,
  backgroundInvestigation: true,
  interactive: false,
  customConfig: {
    sectionsCount: 4,
    imagesCount: 4,
    codeBlocksCount: 2,
    targetWordCount: 3500,
  },
  imageStyles: [{ id: 'cartoon', name: '默认风格', icon: '🎨' }],
  appConfig: { features: {} },
}

describe('AdvancedOptionsPanel — deep thinking & background investigation', () => {
  it('should render background investigation checkbox (checked by default)', () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    // backgroundInvestigation is the first new checkbox
    const bgCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('背景调查')
    })
    expect(bgCheckbox).toBeTruthy()
    expect((bgCheckbox!.element as HTMLInputElement).checked).toBe(true)
  })

  it('should render deep thinking checkbox (unchecked by default)', () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const dtCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('深度思考')
    })
    expect(dtCheckbox).toBeTruthy()
    expect((dtCheckbox!.element as HTMLInputElement).checked).toBe(false)
  })

  it('should emit update:deepThinking when deep thinking checkbox toggled', async () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const dtCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('深度思考')
    })
    await dtCheckbox!.setValue(true)
    expect(wrapper.emitted('update:deepThinking')).toBeTruthy()
    expect(wrapper.emitted('update:deepThinking')![0]).toEqual([true])
  })

  it('should emit update:backgroundInvestigation when background investigation checkbox toggled', async () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const bgCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('背景调查')
    })
    await bgCheckbox!.setValue(false)
    expect(wrapper.emitted('update:backgroundInvestigation')).toBeTruthy()
    expect(wrapper.emitted('update:backgroundInvestigation')![0]).toEqual([false])
  })

  it('should show tooltip hints for both controls', () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const text = wrapper.text()
    expect(text).toContain('深度思考')
    expect(text).toContain('背景调查')
  })

  it('should reflect deepThinking=true from props', () => {
    const wrapper = mount(AdvancedOptionsPanel, {
      props: { ...baseProps, deepThinking: true },
    })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const dtCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('深度思考')
    })
    expect((dtCheckbox!.element as HTMLInputElement).checked).toBe(true)
  })
})

describe('AdvancedOptionsPanel — interactive mode', () => {
  it('should render interactive checkbox (unchecked by default)', () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const interactiveCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('交互式生成')
    })
    expect(interactiveCheckbox).toBeTruthy()
    expect((interactiveCheckbox!.element as HTMLInputElement).checked).toBe(false)
  })

  it('should emit update:interactive when interactive checkbox toggled', async () => {
    const wrapper = mount(AdvancedOptionsPanel, { props: baseProps })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const interactiveCheckbox = checkboxes.find((cb) => {
      const label = cb.element.closest('label')
      return label?.textContent?.includes('交互式生成')
    })
    await interactiveCheckbox!.setValue(true)
    expect(wrapper.emitted('update:interactive')).toBeTruthy()
    expect(wrapper.emitted('update:interactive')![0]).toEqual([true])
  })
})

describe('AdvancedOptionsPanel — isLoading disabled', () => {
  it('should disable all checkboxes and selects when isLoading is true', () => {
    const wrapper = mount(AdvancedOptionsPanel, {
      props: { ...baseProps, isLoading: true },
    })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    checkboxes.forEach((cb) => {
      expect((cb.element as HTMLInputElement).disabled).toBe(true)
    })
    const selects = wrapper.findAll('select')
    selects.forEach((sel) => {
      expect((sel.element as HTMLSelectElement).disabled).toBe(true)
    })
  })

  it('should not disable controls when isLoading is false', () => {
    const wrapper = mount(AdvancedOptionsPanel, {
      props: { ...baseProps, isLoading: false },
    })
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    checkboxes.forEach((cb) => {
      expect((cb.element as HTMLInputElement).disabled).toBe(false)
    })
    const selects = wrapper.findAll('select')
    selects.forEach((sel) => {
      expect((sel.element as HTMLSelectElement).disabled).toBe(false)
    })
  })
})
