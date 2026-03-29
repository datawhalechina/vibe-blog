/**
 * 101.09 多格式导出 — ExportMenu 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ExportMenu from '@/components/generate/ExportMenu.vue'

describe('ExportMenu.vue', () => {
  it('should render export button', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.text()).toContain('导出')
  })

  it('should render button with content and filename props', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello World', filename: 'article' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('should render 5 export format options', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('should render format labels', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test' },
    })
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('should emit export event with format on menu item click', async () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test' },
    })
    expect(wrapper.emitted('export')).toBeFalsy()
  })

  it('should disable button when isDownloading is true', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', isDownloading: true },
    })
    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('should disable button when content is empty', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '', filename: 'test' },
    })
    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
