import { ref, readonly } from 'vue'

/**
 * 下载功能 Composable
 *
 * 功能：
 * - 下载 Markdown ZIP 文件
 * - 下载状态管理
 */
export function useDownload() {
  const isDownloading = ref(false)

  /**
   * 下载 Markdown ZIP 文件
   */
  const downloadMarkdown = async (
    content: string,
    title: string,
    onSuccess: (message: string) => void,
    onError: (message: string) => void
  ) => {
    if (!content) {
      onError('没有可下载的内容')
      return
    }

    if (isDownloading.value) return
    isDownloading.value = true

    const safeTitle = title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').substring(0, 50)

    try {
      // 调用后端 API 导出包含图片的 Markdown ZIP
      const response = await fetch('/api/export/markdown', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          markdown: content,
          title: title
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || '导出失败')
      }

      // 获取 ZIP 文件
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)

      // 下载 ZIP 文件
      const a = document.createElement('a')
      a.href = url
      a.download = `${safeTitle}_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      onSuccess('ZIP 文件已下载')
    } catch (error: any) {
      onError('下载失败: ' + error.message)
    } finally {
      isDownloading.value = false
    }
  }

  return {
    isDownloading: readonly(isDownloading),
    downloadMarkdown
  }
}
