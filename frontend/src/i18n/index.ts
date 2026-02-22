/**
 * 1003.08 多语言 i18n 框架
 *
 * vue-i18n 初始化 + normalizeLocale() 语言标准化
 * 参考 DeepTutor web/i18n/init.ts
 */
import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.json'
import enUS from './locales/en-US.json'

export type AppLocale = 'zh-CN' | 'en-US'

/**
 * 标准化语言代码为 BCP 47 格式
 */
export function normalizeLocale(lang: unknown): AppLocale {
  if (!lang) return 'zh-CN'
  const s = String(lang).toLowerCase().trim()
  if (s === 'en' || s === 'en-us' || s === 'en_us' || s === 'english') return 'en-US'
  if (s === 'zh' || s === 'zh-cn' || s === 'zh_cn' || s === 'chinese' || s === 'cn') return 'zh-CN'
  return 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})
