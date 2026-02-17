/**
 * 101.04 质量评估 — QualityDialog 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import QualityDialog from '@/components/generate/QualityDialog.vue'

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

  it('should render grade badge with correct grade', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.text()).toContain('A-')
  })

  it('should render overall score', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.text()).toContain('83')
  })

  it('should render all 6 score dimensions', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    const text = wrapper.text()
    expect(text).toContain('事实准确')
    expect(text).toContain('内容完整')
    expect(text).toContain('逻辑连贯')
    expect(text).toContain('主题相关')
    expect(text).toContain('引用质量')
    expect(text).toContain('写作质量')
  })

  it('should render progress bars with correct values', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    const text = wrapper.text()
    expect(text).toContain('85%')
  })

  it('should render strengths list', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    const text = wrapper.text()
    expect(text).toContain('代码示例丰富且可运行')
    expect(text).toContain('章节结构清晰有层次')
  })

  it('should render weaknesses list', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.text()).toContain('引用来源偏少')
  })

  it('should render suggestions list', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.text()).toContain('补充 3-5 个权威引用')
  })

  it('should not render empty lists', () => {
    const emptyEval = { ...mockEvaluation, strengths: [], weaknesses: [], suggestions: [] }
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: emptyEval, loading: false },
    })
    const text = wrapper.text()
    expect(text).not.toContain('优点')
    expect(text).not.toContain('不足')
    expect(text).not.toContain('建议')
  })

  it('should render summary and statistics', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.text()).toContain('文章结构清晰')
    expect(wrapper.text()).toContain('3500')
  })

  it('should show loading state', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: null, loading: true },
    })
    expect(wrapper.text()).toContain('evaluate')
  })

  it('should not render when not visible', () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: false, evaluation: mockEvaluation, loading: false },
    })
    expect(wrapper.html()).toBe('')
  })

  it('should emit close when close button clicked', async () => {
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: mockEvaluation, loading: false },
    })
    await wrapper.find('.dialog-close-btn').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should apply correct color for different grades', () => {
    const grades = [
      { grade: 'A+', expectedClass: 'grade-excellent' },
      { grade: 'B', expectedClass: 'grade-good' },
      { grade: 'C', expectedClass: 'grade-average' },
      { grade: 'F', expectedClass: 'grade-poor' },
    ]
    grades.forEach(({ grade, expectedClass }) => {
      const wrapper = mount(QualityDialog, {
        props: { visible: true, evaluation: { ...mockEvaluation, grade }, loading: false },
      })
      expect(wrapper.find('.grade-badge').classes()).toContain(expectedClass)
    })
  })

  it('should handle LLM fallback evaluation', () => {
    const fallbackEval = {
      grade: 'N/A', overall_score: 0,
      scores: {
        factual_accuracy: 0, completeness: 0, coherence: 0,
        relevance: 0, citation_quality: 0, writing_quality: 0,
      },
      strengths: [], weaknesses: [], suggestions: [],
      summary: 'LLM 评估不可用，仅提供基础统计',
      word_count: 3500, citation_count: 8, image_count: 4, code_block_count: 6,
    }
    const wrapper = mount(QualityDialog, {
      props: { visible: true, evaluation: fallbackEval, loading: false },
    })
    expect(wrapper.find('.grade-badge').text()).toContain('N/A')
    expect(wrapper.text()).toContain('LLM 评估不可用')
  })
})
