import { ref, watch, type Ref } from 'vue'
import { loadFromStorage, saveToStorage } from '../utils/persistence'

export function usePersistentRef<T>(
  key: string,
  defaultValue: T,
  debounceMs = 500
): Ref<T> {
  const stored = loadFromStorage<T>(key, defaultValue)
  const data = ref(stored) as Ref<T>

  let timer: ReturnType<typeof setTimeout> | null = null

  watch(data, (newVal) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      saveToStorage(key, newVal)
    }, debounceMs)
  }, { deep: true })

  return data
}
