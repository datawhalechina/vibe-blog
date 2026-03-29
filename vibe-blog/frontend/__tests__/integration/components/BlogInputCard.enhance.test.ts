/**
 * 101.08 Prompt 增强 — BlogInputCard 魔法棒按钮组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BlogInputCard from '@/components/home/BlogInputCard.vue'

describe('BlogInputCard enhance button', () => {
  const baseProps = {
    topic: 'LangGraph 入门',
    uploadedDocuments: [],
    isLoading: false,
    isEnhancing: false,
    showAdvancedOptions: false,
  }

  it('should render enhance button (wand icon)', () => {
    const wrapper = mount(BlogInputCard, { props: baseProps })
    expect(wrapper.find('.enhance-btn').exists()).toBe(true)
  })

  it('should emit enhanceTopic when enhance button clicked', async () => {
    const wrapper = mount(BlogInputCard, { props: baseProps })
    await wrapper.find('.enhance-btn').trigger('click')
    expect(wrapper.emitted('enhanceTopic')).toBeTruthy()
  })

  it('should disable enhance button when topic is empty', () => {
    const wrapper = mount(BlogInputCard, {
      props: { ...baseProps, topic: '' },
    })
    expect(wrapper.find('.enhance-btn').attributes('disabled')).toBeDefined()
  })

  it('should disable enhance button when isEnhancing is true', () => {
    const wrapper = mount(BlogInputCard, {
      props: { ...baseProps, isEnhancing: true },
    })
    expect(wrapper.find('.enhance-btn').attributes('disabled')).toBeDefined()
  })

  it('should show spinner when isEnhancing is true', () => {
    const wrapper = mount(BlogInputCard, {
      props: { ...baseProps, isEnhancing: true },
    })
    expect(wrapper.find('.enhance-btn').classes()).toContain('enhancing')
    expect(wrapper.find('.enhance-spinner').exists()).toBe(true)
  })

  it('should disable enhance button when isLoading is true', () => {
    const wrapper = mount(BlogInputCard, {
      props: { ...baseProps, isLoading: true },
    })
    expect(wrapper.find('.enhance-btn').attributes('disabled')).toBeDefined()
  })
})
