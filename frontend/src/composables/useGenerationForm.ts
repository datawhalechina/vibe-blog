import { computed, reactive, ref, type Ref } from 'vue'

import * as api from '@/services/api'

type GenerationService = Pick<
  typeof api,
  | 'enhanceTopic'
  | 'createStorybookTask'
  | 'createMiniBlogTask'
  | 'createBlogTask'
>

interface UseGenerationFormOptions {
  service?: GenerationService
  getReadyDocumentIds?: () => string[]
  isGenerating?: Ref<boolean>
}

export type GenerationTaskKind = 'storybook' | 'mini' | 'blog'

export function useGenerationForm(options: UseGenerationFormOptions = {}) {
  const service = options.service ?? api
  const getReadyDocumentIds = options.getReadyDocumentIds ?? (() => [])
  const isGenerating = options.isGenerating ?? ref(false)

  const topic = ref('')
  const showAdvancedOptions = ref(false)
  const articleType = ref('tutorial')
  const targetLength = ref('mini')
  const audienceAdaptation = ref('default')
  const imageStyle = ref('cartoon')
  const generateCoverVideo = ref(false)
  const videoAspectRatio = ref('16:9')
  const deepThinking = ref(false)
  const backgroundInvestigation = ref(true)
  const interactive = ref(true)
  const isEnhancing = ref(false)
  const customConfig = reactive({
    sectionsCount: 4,
    imagesCount: 4,
    codeBlocksCount: 2,
    targetWordCount: 3_500,
  })
  const taskKind = computed<GenerationTaskKind>(() => {
    if (articleType.value === 'storybook') return 'storybook'
    if (targetLength.value === 'mini') return 'mini'
    return 'blog'
  })
  const taskName = computed(() => ({
    storybook: '科普绘本',
    mini: 'Mini 博客',
    blog: '博客',
  })[taskKind.value])

  const enhanceTopic = async () => {
    if (
      !topic.value.trim()
      || isEnhancing.value
      || isGenerating.value
    ) return

    isEnhancing.value = true
    try {
      const data = await service.enhanceTopic(topic.value)
      if (data.success && data.enhanced_topic) {
        topic.value = data.enhanced_topic
      }
    } catch (error) {
      console.error('主题优化失败:', error)
    } finally {
      isEnhancing.value = false
    }
  }

  const createTask = async () => {
    const isStorybook = articleType.value === 'storybook'
    const isMini = targetLength.value === 'mini'

    if (isStorybook) {
      const response = await service.createStorybookTask({
        content: topic.value,
        page_count: targetLength.value === 'short'
          ? 5
          : targetLength.value === 'medium' ? 8 : 12,
        target_audience: '技术小白',
        style: '可爱卡通风',
        generate_images: true,
      })
      return { kind: 'storybook' as const, name: '科普绘本', response }
    }

    if (isMini) {
      const response = await service.createMiniBlogTask({
        topic: topic.value,
        article_type: articleType.value,
        audience_adaptation: audienceAdaptation.value,
        image_style: imageStyle.value,
        document_ids: getReadyDocumentIds(),
      })
      return { kind: 'mini' as const, name: 'Mini 博客', response }
    }

    const params: api.BlogGenerateParams = {
      topic: topic.value,
      article_type: articleType.value,
      target_length: targetLength.value,
      audience_adaptation: audienceAdaptation.value,
      document_ids: getReadyDocumentIds(),
      image_style: imageStyle.value,
      generate_cover_video: generateCoverVideo.value,
      video_aspect_ratio: videoAspectRatio.value,
      deep_thinking: deepThinking.value,
      background_investigation: backgroundInvestigation.value,
      interactive: interactive.value,
    }
    if (targetLength.value === 'custom') {
      params.custom_config = {
        sections_count: customConfig.sectionsCount,
        images_count: customConfig.imagesCount,
        code_blocks_count: customConfig.codeBlocksCount,
        target_word_count: customConfig.targetWordCount,
      }
    }

    const response = await service.createBlogTask(params)
    return { kind: 'blog' as const, name: '博客', response }
  }

  return {
    topic,
    showAdvancedOptions,
    articleType,
    targetLength,
    audienceAdaptation,
    imageStyle,
    generateCoverVideo,
    videoAspectRatio,
    deepThinking,
    backgroundInvestigation,
    interactive,
    customConfig,
    isEnhancing,
    taskKind,
    taskName,
    enhanceTopic,
    createTask,
  }
}
