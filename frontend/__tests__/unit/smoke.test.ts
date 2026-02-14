/**
 * Smoke Test — 验证测试基础设施可用
 * 覆盖：Vitest 运行、@vue/test-utils 挂载、MSW mock API、@ 别名解析
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

// 1. Vitest 基础
describe('Vitest smoke', () => {
  it('should run a basic assertion', () => {
    expect(1 + 1).toBe(2)
  })

  it('should support async/await', async () => {
    const result = await Promise.resolve('ok')
    expect(result).toBe('ok')
  })
})

// 2. Vue Test Utils 挂载
describe('Vue Test Utils smoke', () => {
  const TestComponent = defineComponent({
    props: { msg: { type: String, default: 'hello' } },
    setup(props) {
      return () => h('div', { class: 'test' }, props.msg)
    },
  })

  it('should mount a Vue component', () => {
    const wrapper = mount(TestComponent)
    expect(wrapper.find('.test').exists()).toBe(true)
    expect(wrapper.text()).toBe('hello')
  })

  it('should accept props', () => {
    const wrapper = mount(TestComponent, { props: { msg: 'world' } })
    expect(wrapper.text()).toBe('world')
  })
})

// 3. MSW mock API
describe('MSW smoke', () => {
  it('should mock POST /api/blog/enhance-topic', async () => {
    const response = await fetch('/api/blog/enhance-topic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: 'LangGraph 入门' }),
    })
    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.enhanced_topic).toBeTruthy()
  })

  it('should mock GET /api/blog/:id/evaluate', async () => {
    const response = await fetch('/api/blog/test-123/evaluate')
    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.evaluation.grade).toBe('A-')
    expect(data.evaluation.overall_score).toBe(83)
    expect(Object.keys(data.evaluation.scores)).toHaveLength(6)
  })

  it('should mock POST /api/blog/generate with new params', async () => {
    const response = await fetch('/api/blog/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: 'test',
        deep_thinking: true,
        background_investigation: false,
      }),
    })
    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.task_id).toBeTruthy()
  })

  it('should mock GET /api/history/:id with citations', async () => {
    const response = await fetch('/api/history/record-456')
    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.record.citations).toHaveLength(2)
    expect(data.record.citations[0].domain).toBe('langchain-ai.github.io')
  })
})

// 4. @ 别名解析
describe('Path alias smoke', () => {
  it('should resolve @/utils/helpers', async () => {
    // 动态 import 验证 @ 别名可用
    const helpers = await import('@/utils/helpers')
    expect(helpers).toBeDefined()
  })

  it('should resolve @/services/api', async () => {
    const api = await import('@/services/api')
    expect(api.createBlogTask).toBeInstanceOf(Function)
  })
})
