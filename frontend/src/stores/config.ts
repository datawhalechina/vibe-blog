import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

/**
 * Article Configuration Types
 */
export interface ArticleConfig {
  type: ArticleType
  length: ArticleLength
  audience: AudienceLevel
  style: WritingStyle
  language: string
  includeCode: boolean
  includeImages: boolean
  tone: ToneType
}

export type ArticleType = 'tutorial' | 'guide' | 'analysis' | 'opinion' | 'news' | 'review'
export type ArticleLength = 'short' | 'medium' | 'long' | 'comprehensive'
export type AudienceLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type WritingStyle = 'formal' | 'casual' | 'technical' | 'conversational'
export type ToneType = 'professional' | 'friendly' | 'authoritative' | 'educational'

/**
 * Default Configuration
 */
const DEFAULT_CONFIG: ArticleConfig = {
  type: 'tutorial',
  length: 'medium',
  audience: 'intermediate',
  style: 'technical',
  language: 'zh-CN',
  includeCode: true,
  includeImages: true,
  tone: 'professional'
}

/**
 * Config Store
 * Manages article configuration with localStorage persistence
 */
export const useConfigStore = defineStore('config', () => {
  // Load from localStorage or use defaults
  const loadConfig = (): ArticleConfig => {
    try {
      const stored = localStorage.getItem('vibe-blog-config')
      if (stored) {
        const parsed = JSON.parse(stored)
        return { ...DEFAULT_CONFIG, ...parsed }
      }
    } catch (error) {
      console.error('Failed to load config from localStorage:', error)
    }
    return { ...DEFAULT_CONFIG }
  }

  // State
  const config = ref<ArticleConfig>(loadConfig())

  // Watch for changes and persist to localStorage
  watch(
    config,
    (newConfig) => {
      try {
        localStorage.setItem('vibe-blog-config', JSON.stringify(newConfig))
      } catch (error) {
        console.error('Failed to save config to localStorage:', error)
      }
    },
    { deep: true }
  )

  // Actions
  const updateConfig = (updates: Partial<ArticleConfig>) => {
    config.value = { ...config.value, ...updates }
  }

  const resetConfig = () => {
    config.value = { ...DEFAULT_CONFIG }
  }

  const setArticleType = (type: ArticleType) => {
    config.value.type = type
  }

  const setArticleLength = (length: ArticleLength) => {
    config.value.length = length
  }

  const setAudience = (audience: AudienceLevel) => {
    config.value.audience = audience
  }

  const setStyle = (style: WritingStyle) => {
    config.value.style = style
  }

  const setLanguage = (language: string) => {
    config.value.language = language
  }

  const toggleIncludeCode = () => {
    config.value.includeCode = !config.value.includeCode
  }

  const toggleIncludeImages = () => {
    config.value.includeImages = !config.value.includeImages
  }

  const setTone = (tone: ToneType) => {
    config.value.tone = tone
  }

  // Getters
  const getConfig = () => config.value

  const getConfigForAPI = () => ({
    article_type: config.value.type,
    article_length: config.value.length,
    audience_level: config.value.audience,
    writing_style: config.value.style,
    language: config.value.language,
    include_code: config.value.includeCode,
    include_images: config.value.includeImages,
    tone: config.value.tone
  })

  return {
    // State
    config,

    // Actions
    updateConfig,
    resetConfig,
    setArticleType,
    setArticleLength,
    setAudience,
    setStyle,
    setLanguage,
    toggleIncludeCode,
    toggleIncludeImages,
    setTone,

    // Getters
    getConfig,
    getConfigForAPI
  }
})
