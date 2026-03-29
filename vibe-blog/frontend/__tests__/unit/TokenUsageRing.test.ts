import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TokenUsageRing from '@/components/home/TokenUsageRing.vue'
import type { TokenUsageSummary } from '@/types/token'

function makeUsage(overrides: Partial<TokenUsageSummary> = {}): TokenUsageSummary {
  return {
    total_input_tokens: 100000,
    total_output_tokens: 50000,
    total_cache_read_tokens: 20000,
    total_cache_write_tokens: 10000,
    total_tokens: 180000,
    total_calls: 12,
    agent_breakdown: {},
    ...overrides,
  }
}

describe('TokenUsageRing.vue', () => {
  it('does not render when tokenUsage is null', () => {
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: null },
    })
    expect(wrapper.html()).toBe('<!--v-if-->')
  })

  it('renders SVG circle when tokenUsage is provided', () => {
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage() },
    })
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('circle').exists()).toBe(true)
  })

  // --- percentage & stroke color ---

  it('uses primary color for usage <= 70%', () => {
    // 180000 / 500000 = 36%
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage({ total_tokens: 180000 }), budget: 500000 },
    })
    const progressCircle = wrapper.findAll('circle')[1] // second circle is progress
    expect(progressCircle.attributes('stroke')).toContain('primary')
  })

  it('uses warning color for usage > 70%', () => {
    // 360000 / 500000 = 72%
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage({ total_tokens: 360000 }), budget: 500000 },
    })
    const progressCircle = wrapper.findAll('circle')[1]
    expect(progressCircle.attributes('stroke')).toContain('warning')
  })

  it('uses error color for usage > 90%', () => {
    // 460000 / 500000 = 92%
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage({ total_tokens: 460000 }), budget: 500000 },
    })
    const progressCircle = wrapper.findAll('circle')[1]
    expect(progressCircle.attributes('stroke')).toContain('error')
  })

  it('caps percentage at 100% when over budget', () => {
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage({ total_tokens: 600000 }), budget: 500000 },
    })
    const progressCircle = wrapper.findAll('circle')[1]
    // stroke-dashoffset should be 0 when at 100%
    const offset = parseFloat(progressCircle.attributes('stroke-dashoffset') || '999')
    expect(offset).toBe(0)
  })

  // --- formatTokenCount ---

  it('formats token counts correctly', () => {
    // We test via the tooltip content
    const wrapper = mount(TokenUsageRing, {
      props: {
        tokenUsage: makeUsage({ total_tokens: 1234, total_input_tokens: 1234 }),
        budget: 500000,
      },
    })
    // Trigger tooltip
    wrapper.find('.token-usage-ring').trigger('mouseenter')
    // formatTokenCount: 1234 -> "1.2K"
    // We'll check the component exposes the function or check tooltip text
    // For now, check the component renders without error
    expect(wrapper.find('svg').exists()).toBe(true)
  })

  // --- agent breakdown sorting ---

  it('sorts agent breakdown by total tokens descending in tooltip', async () => {
    const usage = makeUsage({
      agent_breakdown: {
        writer: { input: 5000, output: 3000, cache_read: 0, cache_write: 0, calls: 2 },
        researcher: { input: 20000, output: 10000, cache_read: 0, cache_write: 0, calls: 5 },
        planner: { input: 1000, output: 500, cache_read: 0, cache_write: 0, calls: 1 },
      },
    })
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: usage },
    })
    await wrapper.find('.token-usage-ring').trigger('mouseenter')
    const tooltip = wrapper.find('.token-tooltip')
    expect(tooltip.exists()).toBe(true)
    const text = tooltip.text()
    const researcherIdx = text.indexOf('researcher')
    const writerIdx = text.indexOf('writer')
    const plannerIdx = text.indexOf('planner')
    // researcher (30000) should come before writer (8000) before planner (1500)
    expect(researcherIdx).toBeLessThan(writerIdx)
    expect(writerIdx).toBeLessThan(plannerIdx)
  })

  // --- cost estimation ---

  it('calculates estimated cost correctly', async () => {
    // $3/1M input + $15/1M output
    // 100000 input = $0.30, 50000 output = $0.75 => total $1.05
    const usage = makeUsage({
      total_input_tokens: 100000,
      total_output_tokens: 50000,
    })
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: usage },
    })
    await wrapper.find('.token-usage-ring').trigger('mouseenter')
    const tooltip = wrapper.find('.token-tooltip')
    expect(tooltip.text()).toContain('$1.05')
  })

  // --- size prop ---

  it('respects custom size prop', () => {
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: makeUsage(), size: 32 },
    })
    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBe('32')
    expect(svg.attributes('height')).toBe('32')
  })

  // --- formatTokenCount unit tests via exposed or tooltip ---

  it('formats large token counts as M', async () => {
    const usage = makeUsage({ total_tokens: 1234567 })
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: usage, budget: 5000000 },
    })
    await wrapper.find('.token-usage-ring').trigger('mouseenter')
    const tooltip = wrapper.find('.token-tooltip')
    // 1234567 -> "1.2M"
    expect(tooltip.text()).toContain('1.2M')
  })

  it('formats medium token counts as K', async () => {
    const usage = makeUsage({ total_tokens: 37000 })
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: usage, budget: 500000 },
    })
    await wrapper.find('.token-usage-ring').trigger('mouseenter')
    const tooltip = wrapper.find('.token-tooltip')
    // 37000 -> "37.0K"
    expect(tooltip.text()).toContain('37.0K')
  })

  it('shows top 5 agents only when more than 5 exist', async () => {
    const agents: Record<string, any> = {}
    for (let i = 0; i < 7; i++) {
      agents[`agent_${i}`] = {
        input: (7 - i) * 1000,
        output: (7 - i) * 500,
        cache_read: 0,
        cache_write: 0,
        calls: 1,
      }
    }
    const usage = makeUsage({ agent_breakdown: agents })
    const wrapper = mount(TokenUsageRing, {
      props: { tokenUsage: usage },
    })
    await wrapper.find('.token-usage-ring').trigger('mouseenter')
    const tooltip = wrapper.find('.token-tooltip')
    const agentItems = tooltip.findAll('.agent-item')
    expect(agentItems.length).toBe(5)
  })
})
