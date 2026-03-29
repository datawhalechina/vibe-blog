import { ref, type Ref } from 'vue'

/**
 * 小红书视频生成 Composable
 *
 * 职责：
 * - 讲解视频生成
 * - 视频进度管理
 * - 视频下载功能
 * - 视频链接复制
 */

export interface VideoOptions {
  model: string
  style: string
  duration: string
}

export function useXhsVideo() {
  // 视频选项
  const videoModel = ref('sora2')
  const videoStyle = ref('ghibli_summer')
  const videoDuration = ref('60')

  // 视频状态
  const isGenerating = ref(false)
  const showProgress = ref(false)
  const progressPercent = ref(0)
  const progressText = ref('准备中...')
  const videoUrl = ref('')

  /**
   * 生成讲解视频
   */
  const generate = async (
    images: string[],
    scripts: string[]
  ): Promise<{ success: boolean; video_url?: string; error?: string }> => {
    if (!images || images.length === 0) {
      return { success: false, error: '请先生成小红书图片' }
    }

    isGenerating.value = true
    showProgress.value = true
    progressPercent.value = 0
    progressText.value = '准备生成讲解视频...'
    videoUrl.value = ''

    // 模拟进度
    let progress = 0
    const progressInterval = setInterval(() => {
      if (progress < 90) {
        progress += Math.random() * 5
        progressPercent.value = Math.min(progress, 90)

        if (progress < 20) progressText.value = '创建时间线...'
        else if (progress < 40) progressText.value = '生成动画指令...'
        else if (progress < 80)
          progressText.value = `生成视频片段 (${Math.floor(progress / 20)}/${images.length})...`
        else progressText.value = '合成最终视频...'
      }
    }, 2000)

    try {
      const response = await fetch('/api/xhs/explanation-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          images,
          scripts,
          style: videoStyle.value,
          target_duration: parseInt(videoDuration.value),
          video_model: videoModel.value
        })
      })

      clearInterval(progressInterval)
      const result = await response.json()

      if (result.success && result.video_url) {
        videoUrl.value = result.video_url
        progressPercent.value = 100
        progressText.value = '✅ 视频生成完成！'

        setTimeout(() => {
          showProgress.value = false
        }, 2000)

        return { success: true, video_url: result.video_url }
      } else {
        throw new Error(result.error || '视频生成失败')
      }
    } catch (error: any) {
      clearInterval(progressInterval)
      progressPercent.value = 100
      progressText.value = '❌ 生成失败: ' + error.message

      setTimeout(() => {
        showProgress.value = false
      }, 5000)

      return { success: false, error: error.message }
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 下载视频
   */
  const download = () => {
    if (!videoUrl.value) {
      alert('没有可下载的视频')
      return
    }

    const a = document.createElement('a')
    a.href = videoUrl.value
    a.download = 'explanation_video.mp4'
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  /**
   * 复制视频链接
   */
  const copyUrl = async (): Promise<boolean> => {
    if (!videoUrl.value) {
      alert('没有可复制的链接')
      return false
    }

    try {
      await navigator.clipboard.writeText(videoUrl.value)
      alert('✅ 视频链接已复制到剪贴板')
      return true
    } catch (e) {
      prompt('请手动复制视频链接:', videoUrl.value)
      return false
    }
  }

  /**
   * 重置视频状态
   */
  const reset = () => {
    isGenerating.value = false
    showProgress.value = false
    progressPercent.value = 0
    progressText.value = '准备中...'
    videoUrl.value = ''
  }

  return {
    // 选项
    videoModel,
    videoStyle,
    videoDuration,

    // 状态（只读）
    isGenerating: readonly(isGenerating) as Readonly<Ref<boolean>>,
    showProgress: readonly(showProgress) as Readonly<Ref<boolean>>,
    progressPercent: readonly(progressPercent) as Readonly<Ref<number>>,
    progressText: readonly(progressText) as Readonly<Ref<string>>,
    videoUrl: readonly(videoUrl) as Readonly<Ref<string>>,

    // 方法
    generate,
    download,
    copyUrl,
    reset
  }
}

function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>
}
