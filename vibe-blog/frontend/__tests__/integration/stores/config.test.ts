import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useConfigStore } from '@/stores/config'
import type { ArticleConfig } from '@/stores/config'

describe('useConfigStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  describe('initialization', () => {
    it('should initialize with default config', () => {
      const store = useConfigStore()

      expect(store.config).toEqual({
        type: 'tutorial',
        length: 'medium',
        audience: 'intermediate',
        style: 'technical',
        language: 'zh-CN',
        includeCode: true,
        includeImages: true,
        tone: 'professional'
      })
    })

    it('should load config from localStorage', () => {
      const savedConfig: Partial<ArticleConfig> = {
        type: 'guide',
        length: 'long',
        audience: 'advanced'
      }
      localStorage.setItem('vibe-blog-config', JSON.stringify(savedConfig))

      const store = useConfigStore()

      expect(store.config.type).toBe('guide')
      expect(store.config.length).toBe('long')
      expect(store.config.audience).toBe('advanced')
      // Should merge with defaults
      expect(store.config.style).toBe('technical')
    })

    it('should handle invalid localStorage data', () => {
      localStorage.setItem('vibe-blog-config', 'invalid json')

      const store = useConfigStore()

      // Should fall back to defaults
      expect(store.config.type).toBe('tutorial')
    })
  })

  describe('updateConfig', () => {
    it('should update config with partial updates', () => {
      const store = useConfigStore()

      store.updateConfig({ type: 'analysis', length: 'short' })

      expect(store.config.type).toBe('analysis')
      expect(store.config.length).toBe('short')
      // Other fields should remain unchanged
      expect(store.config.audience).toBe('intermediate')
    })

    it('should persist config to localStorage', async () => {
      const store = useConfigStore()

      store.updateConfig({ type: 'guide' })

      // Wait for watcher to run
      await new Promise(resolve => setTimeout(resolve, 0))

      const saved = JSON.parse(localStorage.getItem('vibe-blog-config') || '{}')
      expect(saved.type).toBe('guide')
    })
  })

  describe('resetConfig', () => {
    it('should reset config to defaults', () => {
      const store = useConfigStore()

      store.updateConfig({ type: 'guide', length: 'long' })
      store.resetConfig()

      expect(store.config).toEqual({
        type: 'tutorial',
        length: 'medium',
        audience: 'intermediate',
        style: 'technical',
        language: 'zh-CN',
        includeCode: true,
        includeImages: true,
        tone: 'professional'
      })
    })
  })

  describe('setters', () => {
    it('should set article type', () => {
      const store = useConfigStore()

      store.setArticleType('guide')

      expect(store.config.type).toBe('guide')
    })

    it('should set article length', () => {
      const store = useConfigStore()

      store.setArticleLength('long')

      expect(store.config.length).toBe('long')
    })

    it('should set audience', () => {
      const store = useConfigStore()

      store.setAudience('expert')

      expect(store.config.audience).toBe('expert')
    })

    it('should set style', () => {
      const store = useConfigStore()

      store.setStyle('casual')

      expect(store.config.style).toBe('casual')
    })

    it('should set language', () => {
      const store = useConfigStore()

      store.setLanguage('en-US')

      expect(store.config.language).toBe('en-US')
    })

    it('should set tone', () => {
      const store = useConfigStore()

      store.setTone('friendly')

      expect(store.config.tone).toBe('friendly')
    })
  })

  describe('toggles', () => {
    it('should toggle includeCode', () => {
      const store = useConfigStore()

      expect(store.config.includeCode).toBe(true)

      store.toggleIncludeCode()
      expect(store.config.includeCode).toBe(false)

      store.toggleIncludeCode()
      expect(store.config.includeCode).toBe(true)
    })

    it('should toggle includeImages', () => {
      const store = useConfigStore()

      expect(store.config.includeImages).toBe(true)

      store.toggleIncludeImages()
      expect(store.config.includeImages).toBe(false)

      store.toggleIncludeImages()
      expect(store.config.includeImages).toBe(true)
    })
  })

  describe('getters', () => {
    it('should get config', () => {
      const store = useConfigStore()

      const config = store.getConfig()

      expect(config).toEqual(store.config)
    })

    it('should get config for API', () => {
      const store = useConfigStore()

      store.updateConfig({
        type: 'guide',
        length: 'long',
        audience: 'advanced',
        style: 'casual',
        language: 'en-US',
        includeCode: false,
        includeImages: false,
        tone: 'friendly'
      })

      const apiConfig = store.getConfigForAPI()

      expect(apiConfig).toEqual({
        article_type: 'guide',
        article_length: 'long',
        audience_level: 'advanced',
        writing_style: 'casual',
        language: 'en-US',
        include_code: false,
        include_images: false,
        tone: 'friendly'
      })
    })
  })

  describe('persistence', () => {
    it('should persist all config changes to localStorage', async () => {
      const store = useConfigStore()

      store.setArticleType('analysis')
      await new Promise(resolve => setTimeout(resolve, 0))

      store.setArticleLength('comprehensive')
      await new Promise(resolve => setTimeout(resolve, 0))

      const saved = JSON.parse(localStorage.getItem('vibe-blog-config') || '{}')
      expect(saved.type).toBe('analysis')
      expect(saved.length).toBe('comprehensive')
    })

    it('should handle localStorage errors gracefully', async () => {
      const store = useConfigStore()

      // Mock localStorage.setItem to throw error
      const originalSetItem = localStorage.setItem
      localStorage.setItem = () => {
        throw new Error('Storage full')
      }

      // Should not throw
      expect(() => {
        store.updateConfig({ type: 'guide' })
      }).not.toThrow()

      // Restore
      localStorage.setItem = originalSetItem
    })
  })
})
