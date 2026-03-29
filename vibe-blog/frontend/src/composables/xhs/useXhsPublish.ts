import { ref, type Ref } from 'vue'
import { parseCookies } from '../../utils/helpers'
import type { XhsResult } from './useXhsGenerator'

/**
 * 小红书发布 Composable
 *
 * 职责：
 * - 发布弹窗管理
 * - Cookie 处理
 * - 发布到小红书
 * - 文案复制功能
 */

export function useXhsPublish() {
  // 弹窗状态
  const showModal = ref(false)
  const cookieInput = ref('')

  /**
   * 打开发布弹窗
   */
  const openModal = () => {
    showModal.value = true
  }

  /**
   * 关闭发布弹窗
   */
  const closeModal = () => {
    showModal.value = false
  }

  /**
   * 发布到小红书
   */
  const publish = async (
    result: XhsResult | null
  ): Promise<{ success: boolean; url?: string; error?: string }> => {
    if (!cookieInput.value.trim()) {
      return { success: false, error: '请输入 Cookie' }
    }

    const cookies = parseCookies(cookieInput.value)
    if (!cookies || cookies.length === 0) {
      return { success: false, error: 'Cookie 解析失败，请检查格式' }
    }

    if (!result?.image_urls?.length) {
      return { success: false, error: '没有可发布的图片' }
    }

    try {
      const response = await fetch('/api/xhs/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookies,
          title: result.titles?.[0] || result.topic || '',
          content: result.copywriting || '',
          tags: result.tags || [],
          images: result.image_urls || []
        })
      })

      const data = await response.json()

      if (data.success) {
        return {
          success: true,
          url: data.url
        }
      } else {
        return {
          success: false,
          error: data.message || data.error || '未知错误'
        }
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message
      }
    }
  }

  /**
   * 复制文案到剪贴板
   */
  const copyCopywriting = async (result: XhsResult | null): Promise<boolean> => {
    if (!result) {
      alert('请先生成内容')
      return false
    }

    const title = result.titles?.[0] || ''
    const copy = result.copywriting || ''
    const tags = (result.tags || []).map(t => '#' + t).join(' ')
    const fullText = `${title}\n\n${copy}\n\n${tags}`

    try {
      await navigator.clipboard.writeText(fullText)
      alert('✅ 文案已复制到剪贴板')
      return true
    } catch (e) {
      alert('复制失败，请手动复制')
      return false
    }
  }

  return {
    // 状态
    showModal,
    cookieInput,

    // 方法
    openModal,
    closeModal,
    publish,
    copyCopywriting
  }
}
