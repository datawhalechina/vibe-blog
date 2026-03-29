import { vi } from 'vitest'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
} as any

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any

// Mock localStorage with actual storage
const localStorageData: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => localStorageData[key] || null,
  setItem: (key: string, value: string) => {
    localStorageData[key] = value
  },
  removeItem: (key: string) => {
    delete localStorageData[key]
  },
  clear: () => {
    Object.keys(localStorageData).forEach(key => delete localStorageData[key])
  },
}
global.localStorage = localStorageMock as any

// Mock sessionStorage with actual storage
const sessionStorageData: Record<string, string> = {}
const sessionStorageMock = {
  getItem: (key: string) => sessionStorageData[key] || null,
  setItem: (key: string, value: string) => {
    sessionStorageData[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorageData[key]
  },
  clear: () => {
    Object.keys(sessionStorageData).forEach(key => delete sessionStorageData[key])
  },
}
global.sessionStorage = sessionStorageMock as any
