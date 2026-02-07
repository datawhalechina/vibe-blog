import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBlogStore } from '@/stores/blog'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import axios from 'axios'

// Setup MSW server
const server = setupServer(
  http.get('/api/blog/list', () => {
    return HttpResponse.json([
      { id: '1', title: 'Blog 1' },
      { id: '2', title: 'Blog 2' }
    ])
  })
)

beforeEach(() => {
  server.listen()
  setActivePinia(createPinia())
})

afterEach(() => {
  server.resetHandlers()
  server.close()
  vi.restoreAllMocks()
})

describe('useBlogStore', () => {
  describe('initialization', () => {
    it('should initialize with empty state', () => {
      const store = useBlogStore()

      expect(store.blogs).toEqual([])
      expect(store.currentBlog).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.progress.visible).toBe(false)
      expect(store.progress.items).toEqual([])
      expect(store.progress.status).toBe('idle')
    })
  })

  describe('fetchBlogs', () => {
    it('should fetch blogs from API', async () => {
      const store = useBlogStore()

      await store.fetchBlogs()

      expect(store.blogs).toHaveLength(2)
      expect(store.blogs[0].id).toBe('1')
      expect(store.blogs[1].id).toBe('2')
    })

    it('should handle fetch errors gracefully', async () => {
      server.use(
        http.get('/api/blog/list', () => {
          return HttpResponse.error()
        })
      )

      const store = useBlogStore()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      await store.fetchBlogs()

      expect(store.blogs).toEqual([])
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })
  })

  describe('generateBlog', () => {
    it('should set loading state when generating', () => {
      const store = useBlogStore()

      // Mock axios.post to return a promise that never resolves
      const mockPost = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(() => {}))

      store.generateBlog('Test Topic')

      expect(store.isLoading).toBe(true)
      expect(store.progress.visible).toBe(true)
      expect(store.progress.status).toBe('generating')

      mockPost.mockRestore()
    })

    it('should show progress drawer when generating', () => {
      const store = useBlogStore()

      const mockPost = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(() => {}))

      store.generateBlog('Test Topic')

      expect(store.progress.visible).toBe(true)

      mockPost.mockRestore()
    })

    it('should clear progress items when starting new generation', () => {
      const store = useBlogStore()

      // Add some existing progress items
      store.progress.items = [
        { type: 'info', message: 'Old message', timestamp: '10:00:00' }
      ]

      const mockPost = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(() => {}))

      store.generateBlog('Test Topic')

      // Should have cleared old items
      expect(store.progress.items).toEqual([])

      mockPost.mockRestore()
    })

    it('should handle generation errors', async () => {
      const store = useBlogStore()

      const mockPost = vi.spyOn(axios, 'post').mockRejectedValue(new Error('Network error'))

      await store.generateBlog('Test Topic')

      expect(store.progress.status).toBe('error')
      expect(store.isLoading).toBe(false)
      expect(store.progress.items.some(item => item.type === 'error')).toBe(true)

      mockPost.mockRestore()
    })
  })
})
