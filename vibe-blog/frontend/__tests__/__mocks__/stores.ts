import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'

// Create a testing pinia instance
export function createTestingPinia() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}

// Mock store states
export const mockBlogState = {
  currentBlog: null,
  history: [],
  isGenerating: false,
  progress: 0,
  currentStep: '',
  error: null,
}

export const mockConfigState = {
  llmProvider: 'openai',
  llmModel: 'gpt-4',
  imageProvider: 'dalle',
  videoProvider: 'runway',
  maxRevisions: 3,
}

export const mockThemeState = {
  isDark: false,
}

// Mock store actions
export const mockBlogActions = {
  generateBlog: vi.fn(),
  loadBlogDetail: vi.fn(),
  loadHistory: vi.fn(),
  deleteBlog: vi.fn(),
  clearError: vi.fn(),
}

export const mockConfigActions = {
  loadConfig: vi.fn(),
  updateConfig: vi.fn(),
}

export const mockThemeActions = {
  toggleTheme: vi.fn(),
  setTheme: vi.fn(),
}
