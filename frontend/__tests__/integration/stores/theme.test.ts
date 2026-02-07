import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '@/stores/theme'

describe('useThemeStore', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())

    // Clear localStorage
    localStorage.clear()

    // Reset document classes
    document.documentElement.classList.remove('dark-mode', 'dark')
  })

  describe('initialization', () => {
    it('should initialize with light theme by default', () => {
      const store = useThemeStore()
      expect(store.isDark).toBe(false)
    })

    it('should load saved theme from localStorage', () => {
      localStorage.setItem('vibe-blog-theme', 'dark')

      const store = useThemeStore()
      expect(store.isDark).toBe(true)
    })

    it('should apply theme classes to document on initialization', () => {
      localStorage.setItem('vibe-blog-theme', 'dark')

      useThemeStore()

      expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  describe('toggleTheme', () => {
    it('should toggle from light to dark', () => {
      const store = useThemeStore()

      store.toggleTheme()

      expect(store.isDark).toBe(true)
    })

    it('should toggle from dark to light', () => {
      localStorage.setItem('vibe-blog-theme', 'dark')
      const store = useThemeStore()

      store.toggleTheme()

      expect(store.isDark).toBe(false)
    })

    it('should update document classes when toggling', async () => {
      const store = useThemeStore()

      store.toggleTheme()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('should persist theme to localStorage when toggling', async () => {
      const store = useThemeStore()

      store.toggleTheme()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(localStorage.getItem('vibe-blog-theme')).toBe('dark')
    })
  })

  describe('setDark', () => {
    it('should set dark theme', () => {
      const store = useThemeStore()

      store.setDark(true)

      expect(store.isDark).toBe(true)
    })

    it('should set light theme', () => {
      localStorage.setItem('vibe-blog-theme', 'dark')
      const store = useThemeStore()

      store.setDark(false)

      expect(store.isDark).toBe(false)
    })

    it('should update document classes when setting theme', async () => {
      const store = useThemeStore()

      store.setDark(true)
      // Wait for watcher to run
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(true)

      store.setDark(false)
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(document.documentElement.classList.contains('dark-mode')).toBe(false)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    it('should persist theme to localStorage when setting', async () => {
      const store = useThemeStore()

      store.setDark(true)
      await new Promise(resolve => setTimeout(resolve, 10))
      expect(localStorage.getItem('vibe-blog-theme')).toBe('dark')

      store.setDark(false)
      await new Promise(resolve => setTimeout(resolve, 10))
      expect(localStorage.getItem('vibe-blog-theme')).toBe('light')
    })
  })

  describe('reactivity', () => {
    it('should react to isDark changes', async () => {
      const store = useThemeStore()

      // Directly modify isDark
      store.isDark = true

      // Wait for watchers to run
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
      expect(localStorage.getItem('vibe-blog-theme')).toBe('dark')
    })
  })
})
