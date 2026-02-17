/**
 * 101.04 质量评估 — QualityDialog 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import QualityDialog from '@/components/generate/QualityDialog.vue'

const mountOpts = {
  global: {
    stubs: {
      Dialog: true,
      DialogContent: true,
      DialogHeader: true,
      DialogTitle: true,
      DialogDescription: true,
      Badge: true,
      Progress: true,
      Separator: true,
      Loader2: true,
    },
  },
}

describe('QualityDialog.vue', () => {
  const mockEvaluation = {
    grade: 'A-',
    overall_score: 83,
    scores: {
      factual_accuracy: 85, completeness: 78, coherence: 92,
      relevance: 88, citation_quality: 70, writing_quality: 85,
    },
    strengths: ['代码示例丰富且可运行', '章节结构清晰有层次'],
    weaknesses: ['引用来源偏少'],
    suggestions: ['补充 3-5 个权威引用'],
    summary: '文章结构清晰，建议补充更多引用。',
    word_count: 3500, citation_count: 8, image_count: 4, code_block_count: 6,
  }

  it('should accept visible prop', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('should accept evaluation prop with grade', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation')).toEqual(mockEvaluation)
    expect(wrapper.props('evaluation').grade).toBe('A-')
  })

  it('should accept evaluation prop with overall_score', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').overall_score).toBe(83)
  })

  it('should accept evaluation prop with scores', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').scores.factual_accuracy).toBe(85)
  })

  it('should accept evaluation prop with strengths', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').strengths).toContain('代码示例丰富且可运行')
  })

  it('should accept evaluation prop with weaknesses', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').weaknesses).toContain('引用来源偏少')
  })

  it('should accept evaluation prop with suggestions', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').suggestions).toContain('补充 3-5 个权威引用')
  })

  it('should accept empty evaluation lists', () => {
    const emptyEval = { ...mockEvaluation, strengths: [], weaknesses: [], suggestions: [] }
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: emptyEval, loading: false },
    })
    expect(wrapper.props('evaluation').strengths).toEqual([])
    expect(wrapper.props('evaluation').weaknesses).toEqual([])
    expect(wrapper.props('evaluation').suggestions).toEqual([])
  })

  it('should accept evaluation prop with word_count', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('evaluation').word_count).toBe(3500)
  })

  it('should accept loading prop as true', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: null, loading: true },
    })
    expect(wrapper.props('loading')).toBe(true)
  })

  it('should accept visible prop as false', () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: false, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.props('visible')).toBe(false)
  })

  it('should emit close event', async () => {
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    await wrapper.vm.$emit('close')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should accept different grade values', () => {
    const fallbackEval = { ...mockEvaluation, grade: 'B+', overall_score: 75 }
    const wrapper = mount(QualityDialog, {
      ...mountOpts,
      props: { visible: true, evaluation: fallbackEval, loading: false },
    })
    expect(wrapper.props('evaluation').grade).toBe('B+')
    expect(wrapper.props('evaluation').overall_score).toBe(75)
  })
})
