import { ref, type Ref } from 'vue'

/**
 * 小红书图片管理 Composable
 *
 * 职责：
 * - 图片槽位初始化
 * - 图片加载状态
 * - 图片下载功能
 * - Prompt 管理
 */

export interface ImageSlot {
  loading: boolean
  url: string
  prompt: string
  statusText: string
  showTooltip: boolean
}

export function useXhsImages() {
  const imageSlots = ref<ImageSlot[]>([])

  /**
   * 初始化图片占位符
   */
  const initPlaceholders = (count: number) => {
    imageSlots.value = Array.from({ length: count }, (_, i) => ({
      loading: true,
      url: '',
      prompt: '',
      statusText: `第 ${i + 1} 页`,
      showTooltip: false
    }))
  }

  /**
   * 更新图片状态
   */
  const updateImageStatus = (index: number, status: string) => {
    if (imageSlots.value[index]) {
      imageSlots.value[index].statusText = status
    }
  }

  /**
   * 设置图片 URL
   */
  const setImageUrl = (index: number, url: string) => {
    if (imageSlots.value[index]) {
      imageSlots.value[index].loading = false
      imageSlots.value[index].url = url
    }
  }

  /**
   * 设置图片 Prompt
   */
  const setImagePrompt = (index: number, prompt: string) => {
    if (imageSlots.value[index]) {
      imageSlots.value[index].prompt = prompt
    }
  }

  /**
   * 批量设置图片 Prompts
   */
  const setImagePrompts = (prompts: Array<{ index: number; prompt: string }>) => {
    prompts.forEach(p => {
      if (imageSlots.value[p.index]) {
        imageSlots.value[p.index].prompt = p.prompt || ''
      }
    })
  }

  /**
   * 确保所有图片都已加载
   */
  const ensureAllImagesLoaded = (urls: string[]) => {
    urls.forEach((url, index) => {
      if (imageSlots.value[index]?.loading) {
        imageSlots.value[index].loading = false
        imageSlots.value[index].url = url
      }
    })
  }

  /**
   * 下载所有图片
   */
  const downloadAll = async (urls: string[]): Promise<void> => {
    if (!urls || urls.length === 0) {
      alert('没有可下载的图片')
      return
    }

    alert(`开始下载 ${urls.length} 张图片`)

    for (let i = 0; i < urls.length; i++) {
      try {
        const response = await fetch(urls[i])
        const blob = await response.blob()
        const blobUrl = URL.createObjectURL(blob)

        const a = document.createElement('a')
        a.href = blobUrl
        a.download = `xhs_${i + 1}.jpg`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)

        await new Promise(r => setTimeout(r, 200))
        URL.revokeObjectURL(blobUrl)

        if (i < urls.length - 1) {
          await new Promise(r => setTimeout(r, 3000))
        }
      } catch (e) {
        console.error(`下载第 ${i + 1} 张图片失败:`, e)
        window.open(urls[i], '_blank')
      }
    }

    alert(`✓ 所有 ${urls.length} 张图片下载完成`)
  }

  /**
   * 复制图片 Prompt
   */
  const copyPrompt = async (index: number): Promise<boolean> => {
    const prompt = imageSlots.value[index]?.prompt
    if (!prompt) return false

    try {
      await navigator.clipboard.writeText(prompt)
      alert('已复制到剪贴板')
      return true
    } catch (e) {
      console.error('复制失败:', e)
      return false
    }
  }

  /**
   * 从历史记录加载图片
   */
  const loadFromHistory = (urls: string[]) => {
    imageSlots.value = urls.map((url, i) => ({
      loading: false,
      url,
      prompt: '',
      statusText: `第 ${i + 1} 页`,
      showTooltip: false
    }))
  }

  return {
    // 状态（只读）
    imageSlots: readonly(imageSlots) as Readonly<Ref<ImageSlot[]>>,

    // 方法
    initPlaceholders,
    updateImageStatus,
    setImageUrl,
    setImagePrompt,
    setImagePrompts,
    ensureAllImagesLoaded,
    downloadAll,
    copyPrompt,
    loadFromHistory
  }
}

function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>
}
