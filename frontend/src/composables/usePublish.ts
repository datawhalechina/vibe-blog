import { ref, readonly } from 'vue'

/**
 * 发布状态接口
 */
export interface PublishStatus {
  show: boolean
  success: boolean
  message: string
  url: string
}

/**
 * Cookie 接口
 */
export interface Cookie {
  name: string
  value: string
  domain: string
}

/**
 * 发布功能 Composable
 *
 * 功能：
 * - 发布到各平台（CSDN、知乎、掘金）
 * - Cookie 解析
 * - 发布状态管理
 */
export function usePublish() {
  const showPublishModal = ref(false)
  const publishPlatform = ref('csdn')
  const publishCookie = ref('')
  const isPublishing = ref(false)
  const publishStatus = ref<PublishStatus>({
    show: false,
    success: false,
    message: '',
    url: ''
  })
  const showCookieHelp = ref(false)

  /**
   * 打开发布弹窗
   */
  const openPublishModal = (
    content: string,
    onError: (message: string) => void
  ) => {
    if (!content) {
      onError('没有可发布的内容')
      return
    }
    showPublishModal.value = true
    publishStatus.value = { show: false, success: false, message: '', url: '' }
  }

  /**
   * 关闭发布弹窗
   */
  const closePublishModal = () => {
    showPublishModal.value = false
    publishCookie.value = ''
    showCookieHelp.value = false
  }

  /**
   * 解析 Cookie 字符串
   */
  const parseCookieString = (cookieStr: string, platform: string): Cookie[] => {
    const domainMap: Record<string, string> = {
      'csdn': '.csdn.net',
      'zhihu': '.zhihu.com',
      'juejin': '.juejin.cn'
    }
    const domain = domainMap[platform] || '.csdn.net'

    const cookies: Cookie[] = []
    const pairs = cookieStr.split(';')
    for (const pair of pairs) {
      const trimmed = pair.trim()
      if (!trimmed) continue

      const eqIndex = trimmed.indexOf('=')
      if (eqIndex === -1) continue

      const name = trimmed.substring(0, eqIndex).trim()
      const value = trimmed.substring(eqIndex + 1).trim()

      if (name) {
        cookies.push({ name, value, domain })
      }
    }
    return cookies
  }

  /**
   * 执行发布
   */
  const doPublish = async (
    title: string,
    content: string,
    onError: (message: string) => void
  ) => {
    if (!publishCookie.value.trim()) {
      onError('请输入 Cookie')
      return
    }

    if (isPublishing.value) return
    isPublishing.value = true

    // 解析 Cookie
    let cookies: Cookie[] | any
    try {
      cookies = JSON.parse(publishCookie.value)
      if (!Array.isArray(cookies)) {
        throw new Error('not array')
      }
    } catch (e) {
      cookies = parseCookieString(publishCookie.value, publishPlatform.value)
      if (cookies.length === 0) {
        onError('Cookie 格式错误，请检查输入')
        isPublishing.value = false
        return
      }
    }

    publishStatus.value = {
      show: true,
      success: false,
      message: '⏳ 正在发布，请稍候...（约 30-60 秒）',
      url: ''
    }

    try {
      const response = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: publishPlatform.value,
          cookies,
          title,
          content
        })
      })

      const data = await response.json()

      if (data.success) {
        publishStatus.value = {
          show: true,
          success: true,
          message: '✅ 发布成功！',
          url: data.url || ''
        }
      } else {
        publishStatus.value = {
          show: true,
          success: false,
          message: '❌ ' + (data.error || '发布失败'),
          url: ''
        }
      }
    } catch (error: any) {
      publishStatus.value = {
        show: true,
        success: false,
        message: '❌ 发布失败: ' + error.message,
        url: ''
      }
    } finally {
      isPublishing.value = false
    }
  }

  return {
    // 状态（只读）
    showPublishModal: readonly(showPublishModal),
    publishPlatform,
    publishCookie,
    isPublishing: readonly(isPublishing),
    publishStatus: readonly(publishStatus),
    showCookieHelp,
    // 方法
    openPublishModal,
    closePublishModal,
    doPublish
  }
}
