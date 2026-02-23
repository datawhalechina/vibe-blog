const STORAGE_PREFIX = 'vibe_blog_'
const STORAGE_VERSION = 1

interface StorageWrapper<T> {
  version: number
  data: T
  timestamp: number
}

export const STORAGE_KEYS = {
  THEME: 'theme',
  CONFIG: 'config',
  FONT_SCALE: 'font_scale',
  SPLIT_RATIO: 'split_ratio',
} as const

export function loadFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key)
    if (!raw) return defaultValue
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && 'version' in parsed && 'data' in parsed) {
      return parsed.data as T
    }
    return parsed as T
  } catch {
    return defaultValue
  }
}

export function saveToStorage<T>(key: string, value: T): void {
  try {
    const wrapper: StorageWrapper<T> = {
      version: STORAGE_VERSION,
      data: value,
      timestamp: Date.now(),
    }
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(wrapper))
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[persistence] Storage quota exceeded for key:', key)
    }
  }
}

export function removeFromStorage(key: string): void {
  localStorage.removeItem(STORAGE_PREFIX + key)
}

export function clearAllStorage(): void {
  const keys: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i)
    if (k?.startsWith(STORAGE_PREFIX)) keys.push(k)
  }
  keys.forEach(k => localStorage.removeItem(k))
}

export function persistState<T extends Record<string, unknown>>(
  state: T,
  exclude: (keyof T)[]
): Partial<T> {
  const result = { ...state }
  for (const key of exclude) {
    delete result[key]
  }
  return result
}

export function mergeWithDefaults<T extends Record<string, unknown>>(
  persisted: Partial<T> | null,
  defaults: T,
  exclude?: (keyof T)[]
): T {
  const merged = { ...defaults, ...persisted }
  if (exclude) {
    for (const key of exclude) {
      merged[key] = defaults[key]
    }
  }
  return merged as T
}

export function getStorageStats(): { totalSize: number; items: { key: string; size: number }[] } {
  const items: { key: string; size: number }[] = []
  let totalSize = 0
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(STORAGE_PREFIX)) {
      const val = localStorage.getItem(key) || ''
      const size = new Blob([val]).size
      items.push({ key: key.replace(STORAGE_PREFIX, ''), size })
      totalSize += size
    }
  }
  return { totalSize, items }
}
