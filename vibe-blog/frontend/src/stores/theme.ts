import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 读取初始值
  const savedTheme = localStorage.getItem('vibe-blog-theme')
  const isDark = ref(savedTheme === 'dark')

  // 同步 dark-mode class 到 <html> 元素
  const applyTheme = (dark: boolean) => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark-mode', 'dark')
    } else {
      root.classList.remove('dark-mode', 'dark')
    }
    localStorage.setItem('vibe-blog-theme', dark ? 'dark' : 'light')
  }

  // 初始化时同步一次
  applyTheme(isDark.value)

  // 监听变化
  watch(isDark, (newValue) => {
    applyTheme(newValue)
  })

  const toggleTheme = () => {
    isDark.value = !isDark.value
  }

  const setDark = (value: boolean) => {
    isDark.value = value
  }

  return {
    isDark,
    toggleTheme,
    setDark
  }
})
