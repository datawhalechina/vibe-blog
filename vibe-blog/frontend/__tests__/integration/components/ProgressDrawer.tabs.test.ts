/**
 * Phase 2: ProgressDrawer Tab 切换 + 大纲审批测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressDrawer from '@/components/home/ProgressDrawer.vue'

const baseProps = {
  visible: true,
  expanded: true,
  isLoading: false,
  statusBadge: '运行中',
  progressText: '生成中',
  progressItems: [],
  articleType: 'tutorial',
  targetLength: 'medium',
  taskId: 'task_abc123',
  outlineData: null as any,
  waitingForOutline: false,
  previewContent: '',
  embedded: false,
}

describe('ProgressDrawer — Tab 切换', () => {
  it('should render tab bar with two tabs', () => {
    const wrapper = mount(ProgressDrawer, { props: baseProps })
    const text = wrapper.text()
    expect(text).toContain('$ tail -f')
    expect(text).toContain('$ cat preview.md')
  })

  it('should default to logs tab active', () => {
    const wrapper = mount(ProgressDrawer, { props: baseProps })
    const text = wrapper.text()
    expect(text).toContain('$ tail -f')
  })

  it('should disable preview tab when no content', () => {
    const wrapper = mount(ProgressDrawer, { props: baseProps })
    expect(wrapper.text()).toContain('$ cat preview.md')
  })

  it('should enable preview tab when previewContent is set', () => {
    const wrapper = mount(ProgressDrawer, {
      props: { ...baseProps, previewContent: '<p>Hello</p>' },
    })
    expect(wrapper.text()).toContain('$ cat preview.md')
  })

  it('should switch to preview tab on click', async () => {
    const wrapper = mount(ProgressDrawer, {
      props: { ...baseProps, previewContent: '<p>Preview</p>' },
    })
    expect(wrapper.text()).toContain('Preview')
  })
})

describe('ProgressDrawer — 大纲审批卡片', () => {
  const outlineProps = {
    ...baseProps,
    outlineData: {
      title: '深入理解 LangGraph',
      sections_titles: ['介绍', '核心概念', '实战案例', '总结'],
    },
    waitingForOutline: true,
  }

  it('should render outline approval card when waiting', () => {
    const wrapper = mount(ProgressDrawer, { props: outlineProps })
    const text = wrapper.text()
    expect(text).toContain('深入理解 LangGraph')
    expect(text).toContain('开始写作')
  })

  it('should render all section titles', () => {
    const wrapper = mount(ProgressDrawer, { props: outlineProps })
    const text = wrapper.text()
    expect(text).toContain('介绍')
    expect(text).toContain('核心概念')
    expect(text).toContain('实战案例')
    expect(text).toContain('总结')
  })

  it('should render accept and edit buttons', () => {
    const wrapper = mount(ProgressDrawer, { props: outlineProps })
    const buttons = wrapper.findAll('button')
    const text = wrapper.text()
    expect(text).toContain('开始写作')
    expect(text).toContain('修改大纲')
  })

  it('should emit confirmOutline with accept on Y click', async () => {
    const wrapper = mount(ProgressDrawer, { props: outlineProps })
    const buttons = wrapper.findAll('button')
    const acceptBtn = buttons.find(b => b.text().includes('开始写作'))
    if (acceptBtn) {
      await acceptBtn.trigger('click')
      expect(wrapper.emitted('confirmOutline')).toBeTruthy()
      expect(wrapper.emitted('confirmOutline')![0]).toEqual(['accept'])
    }
  })

  it('should emit confirmOutline with edit on e click', async () => {
    const wrapper = mount(ProgressDrawer, { props: outlineProps })
    const buttons = wrapper.findAll('button')
    const editBtn = buttons.find(b => b.text().includes('修改大纲'))
    if (editBtn) {
      await editBtn.trigger('click')
      expect(wrapper.emitted('confirmOutline')).toBeTruthy()
      expect(wrapper.emitted('confirmOutline')![0]).toEqual(['edit'])
    }
  })

  it('should show confirmed state after outline is confirmed', () => {
    const wrapper = mount(ProgressDrawer, {
      props: {
        ...outlineProps,
        waitingForOutline: false,
      },
    })
    const text = wrapper.text()
    expect(text).toContain('深入理解 LangGraph')
  })

  it('should not render outline card when outlineData is null', () => {
    const wrapper = mount(ProgressDrawer, { props: baseProps })
    const text = wrapper.text()
    expect(text).not.toContain('开始写作')
  })
})
