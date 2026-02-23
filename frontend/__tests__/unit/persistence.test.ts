import { describe, it, expect, beforeEach } from 'vitest'
import {
  loadFromStorage,
  saveToStorage,
  removeFromStorage,
  clearAllStorage,
  persistState,
  mergeWithDefaults,
  getStorageStats,
} from '../../src/utils/persistence'

// The global localStorage mock from vitest.setup.ts lacks length/key().
// Provide a full-featured mock for tests that need iteration.
function installFullLocalStorageMock() {
  const store: Record<string, string> = {}
  const mock = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = String(value) },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { Object.keys(store).forEach(k => delete store[k]) },
    get length() { return Object.keys(store).length },
    key: (index: number) => Object.keys(store)[index] ?? null,
  }
  Object.defineProperty(globalThis, 'localStorage', { value: mock, writable: true, configurable: true })
}

describe('persistence utilities', () => {
  beforeEach(() => {
    installFullLocalStorageMock()
  })

  describe('loadFromStorage', () => {
    it('returns default when key missing', () => {
      expect(loadFromStorage('nope', 42)).toBe(42)
    })

    it('reads wrapped format', () => {
      localStorage.setItem('vibe_blog_test', JSON.stringify({ version: 1, data: 'hello', timestamp: 1 }))
      expect(loadFromStorage('test', '')).toBe('hello')
    })

    it('reads legacy format', () => {
      localStorage.setItem('vibe_blog_legacy', JSON.stringify({ foo: 'bar' }))
      expect(loadFromStorage('legacy', {})).toEqual({ foo: 'bar' })
    })

    it('returns default on parse error', () => {
      localStorage.setItem('vibe_blog_bad', 'not json')
      expect(loadFromStorage('bad', 'default')).toBe('default')
    })
  })

  describe('saveToStorage', () => {
    it('saves in wrapper format', () => {
      saveToStorage('key1', { a: 1 })
      const raw = JSON.parse(localStorage.getItem('vibe_blog_key1')!)
      expect(raw.version).toBe(1)
      expect(raw.data).toEqual({ a: 1 })
      expect(raw.timestamp).toBeGreaterThan(0)
    })
  })

  describe('removeFromStorage', () => {
    it('removes prefixed key', () => {
      localStorage.setItem('vibe_blog_rm', 'x')
      removeFromStorage('rm')
      expect(localStorage.getItem('vibe_blog_rm')).toBeNull()
    })
  })

  describe('clearAllStorage', () => {
    it('clears only prefixed keys', () => {
      localStorage.setItem('vibe_blog_a', '1')
      localStorage.setItem('vibe_blog_b', '2')
      localStorage.setItem('other', '3')
      clearAllStorage()
      expect(localStorage.getItem('vibe_blog_a')).toBeNull()
      expect(localStorage.getItem('vibe_blog_b')).toBeNull()
      expect(localStorage.getItem('other')).toBe('3')
    })
  })

  describe('persistState', () => {
    it('excludes specified fields', () => {
      const state = { a: 1, b: 2, c: 3 }
      const result = persistState(state, ['b'])
      expect(result).toEqual({ a: 1, c: 3 })
    })
  })

  describe('mergeWithDefaults', () => {
    it('merges persisted with defaults', () => {
      const defaults = { a: 1, b: 2, c: 3 }
      const persisted = { a: 10 }
      expect(mergeWithDefaults(persisted, defaults)).toEqual({ a: 10, b: 2, c: 3 })
    })

    it('resets excluded fields to defaults', () => {
      const defaults = { a: 1, b: 2 }
      const persisted = { a: 10, b: 20 }
      expect(mergeWithDefaults(persisted, defaults, ['b'])).toEqual({ a: 10, b: 2 })
    })

    it('handles null persisted', () => {
      const defaults = { a: 1 }
      expect(mergeWithDefaults(null, defaults)).toEqual({ a: 1 })
    })
  })

  describe('getStorageStats', () => {
    it('returns stats for prefixed keys', () => {
      saveToStorage('s1', 'hello')
      saveToStorage('s2', 'world')
      const stats = getStorageStats()
      expect(stats.items.length).toBe(2)
      expect(stats.totalSize).toBeGreaterThan(0)
    })
  })
})
