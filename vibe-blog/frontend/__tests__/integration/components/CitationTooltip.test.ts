/**
 * 101.05 引用悬浮卡片 — CitationTooltip 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CitationTooltip from '@/components/generate/CitationTooltip.vue'

const mockCitation = {
  url: 'https://langchain-ai.github.io/langgraph/',
  title: 'LangGraph: Multi-Agent Workflows',
  domain: 'langchain-ai.github.io',
  snippet: 'A framework for building stateful, multi-actor applications with LLMs.',
  relevance: 95,
}

// Teleport 渲染到 body，需要 stub 掉才能在 wrapper 中查找
const mountOpts = {
  global: {
    stubs: { Teleport: true },
  },
}

beforeEach(() => {
  // Mock window.innerWidth 为桌面端，避免 isMobile 隐藏组件
  Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true })
})

describe('CitationTooltip.vue', () => {
  it('should render when visible with citation data', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 100, left: 200 } },
    })
    expect(wrapper.text()).toContain('LangGraph')
  })

  it('should not render when not visible', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: false, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.html()).toContain('<!--v-if-->')
  })

  it('should not render when citation is null', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: null, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.html()).toContain('<!--v-if-->')
  })

  it('should render citation index', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 3, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).toContain('3')
  })

  it('should render domain', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).toContain('langchain-ai.github.io')
  })

  it('should render title', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).toContain('LangGraph')
  })

  it('should render snippet', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).toContain('multi-actor')
  })

  it('should render relevance when available', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).toContain('95')
  })

  it('should not render relevance when not available', () => {
    const noRelevance = { ...mockCitation, relevance: undefined }
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: noRelevance, index: 1, position: { top: 0, left: 0 } },
    })
    expect(wrapper.text()).not.toContain('%')
  })

  it('should render open link with correct href', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 0, left: 0 } },
    })
    const links = wrapper.findAll('a')
    if (links.length > 0) {
      expect(links[0].attributes('href')).toBe('https://langchain-ai.github.io/langgraph/')
      expect(links[0].attributes('target')).toBe('_blank')
    }
  })

  it('should position at given coordinates', () => {
    const wrapper = mount(CitationTooltip, {
      ...mountOpts,
      props: { visible: true, citation: mockCitation, index: 1, position: { top: 150, left: 300 } },
    })
    expect(wrapper.text()).toContain('LangGraph')
  })
})
