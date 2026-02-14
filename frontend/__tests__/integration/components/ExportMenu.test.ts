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
    expect(wrapper.find('.export-trigger').exists()).toBe(true)
  })

  it('should toggle menu on button click', async () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test' },
    })
    expect(wrapper.find('.export-menu').exists()).toBe(false)
    await wrapper.find('.export-trigger').trigger('click')
    expect(wrapper.find('.export-menu').exists()).toBe(true)
  })

  it('should render 3 export options (md, html, txt)', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', menuOpen: true },
    })
    const items = wrapper.findAll('.export-item')
    expect(items.length).toBe(3)
  })

  it('should render format labels', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', menuOpen: true },
    })
    const text = wrapper.text()
    expect(text).toContain('Markdown')
    expect(text).toContain('HTML')
    expect(text).toContain('纯文本')
  })

  it('should emit export event with format on click', async () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', menuOpen: true },
    })
    const items = wrapper.findAll('.export-item')
    await items[0].trigger('click')
    expect(wrapper.emitted('export')).toBeTruthy()
    expect(wrapper.emitted('export')![0]).toEqual(['markdown'])
  })

  it('should close menu after export click', async () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', menuOpen: true },
    })
    await wrapper.findAll('.export-item')[0].trigger('click')
    expect(wrapper.find('.export-menu').exists()).toBe(false)
  })

  it('should disable when isDownloading', () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '# Hello', filename: 'test', isDownloading: true },
    })
    expect(wrapper.find('.export-trigger').classes()).toContain('downloading')
  })

  it('should not render menu when content is empty', async () => {
    const wrapper = mount(ExportMenu, {
      props: { content: '', filename: 'test' },
    })
    await wrapper.find('.export-trigger').trigger('click')
    expect(wrapper.find('.export-menu').exists()).toBe(false)
  })
})
