import { ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { useGenerationForm } from '@/composables/useGenerationForm'

function createService() {
  return {
    enhanceTopic: vi.fn().mockResolvedValue({
      success: true,
      enhanced_topic: 'Enhanced topic',
    }),
    createStorybookTask: vi.fn().mockResolvedValue({
      success: true,
      task_id: 'storybook-1',
    }),
    createMiniBlogTask: vi.fn().mockResolvedValue({
      success: true,
      task_id: 'mini-1',
    }),
    createBlogTask: vi.fn().mockResolvedValue({
      success: true,
      task_id: 'blog-1',
    }),
  }
}

describe('useGenerationForm', () => {
  it('creates the existing Mini request payload', async () => {
    const service = createService()
    const form = useGenerationForm({
      service,
      getReadyDocumentIds: () => ['doc-1'],
    })
    form.topic.value = 'Vue composables'

    expect(form.taskKind.value).toBe('mini')
    expect(form.taskName.value).toBe('Mini 博客')

    const task = await form.createTask()

    expect(task).toEqual({
      kind: 'mini',
      name: 'Mini 博客',
      response: { success: true, task_id: 'mini-1' },
    })
    expect(service.createMiniBlogTask).toHaveBeenCalledWith({
      topic: 'Vue composables',
      article_type: 'tutorial',
      audience_adaptation: 'default',
      image_style: 'cartoon',
      document_ids: ['doc-1'],
    })
  })

  it('creates the existing Storybook request payload', async () => {
    const service = createService()
    const form = useGenerationForm({ service })
    form.topic.value = 'How databases work'
    form.articleType.value = 'storybook'
    form.targetLength.value = 'short'

    expect(form.taskKind.value).toBe('storybook')
    expect(form.taskName.value).toBe('科普绘本')

    const task = await form.createTask()

    expect(task.kind).toBe('storybook')
    expect(task.name).toBe('科普绘本')
    expect(service.createStorybookTask).toHaveBeenCalledWith({
      content: 'How databases work',
      page_count: 5,
      target_audience: '技术小白',
      style: '可爱卡通风',
      generate_images: true,
    })
  })

  it('creates standard and custom blog payloads without changing field names', async () => {
    const service = createService()
    const form = useGenerationForm({
      service,
      getReadyDocumentIds: () => ['doc-2'],
    })
    form.topic.value = 'LangGraph routing'
    form.targetLength.value = 'custom'
    form.generateCoverVideo.value = true
    form.deepThinking.value = true
    form.customConfig.sectionsCount = 6
    form.customConfig.imagesCount = 3
    form.customConfig.codeBlocksCount = 4
    form.customConfig.targetWordCount = 5_000

    const task = await form.createTask()

    expect(task.kind).toBe('blog')
    expect(service.createBlogTask).toHaveBeenCalledWith({
      topic: 'LangGraph routing',
      article_type: 'tutorial',
      target_length: 'custom',
      audience_adaptation: 'default',
      document_ids: ['doc-2'],
      image_style: 'cartoon',
      generate_cover_video: true,
      video_aspect_ratio: '16:9',
      deep_thinking: true,
      background_investigation: true,
      interactive: true,
      custom_config: {
        sections_count: 6,
        images_count: 3,
        code_blocks_count: 4,
        target_word_count: 5_000,
      },
    })
  })

  it('guards enhancement while empty, generating, or already enhancing', async () => {
    let resolveEnhancement!: (value: {
      success: boolean
      enhanced_topic: string
    }) => void
    const service = createService()
    service.enhanceTopic.mockImplementation(
      () => new Promise((resolve) => { resolveEnhancement = resolve }),
    )
    const isGenerating = ref(false)
    const form = useGenerationForm({ service, isGenerating })

    await form.enhanceTopic()
    expect(service.enhanceTopic).not.toHaveBeenCalled()

    form.topic.value = 'Original'
    isGenerating.value = true
    await form.enhanceTopic()
    expect(service.enhanceTopic).not.toHaveBeenCalled()

    isGenerating.value = false
    const enhancement = form.enhanceTopic()
    await form.enhanceTopic()
    expect(service.enhanceTopic).toHaveBeenCalledOnce()

    resolveEnhancement({ success: true, enhanced_topic: 'Enhanced' })
    await enhancement
    expect(form.topic.value).toBe('Enhanced')
    expect(form.isEnhancing.value).toBe(false)
  })
})
