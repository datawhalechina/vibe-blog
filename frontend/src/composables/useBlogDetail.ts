import { ref, readonly } from 'vue'
import { useRouter } from 'vue-router'

/**
 * 博客详情数据接口
 */
export interface Blog {
  id: string
  title: string
  description: string
  content: string
  category: string
  theme: string
  tags: string[]
  author: string
  authorAvatar: string
  sourceUrl: string
  stars: number
  forks: number
  createdAt: string
  updatedAt: string
  // 博客属性
  articleType: string
  sectionsCount: number
  imagesCount: number
  codeBlocksCount: number
  wordCount: number
  // 封面视频
  coverVideo?: string
}

/**
 * Toast 通知接口
 */
export interface Toast {
  show: boolean
  message: string
  type: 'info' | 'success' | 'error'
}

/**
 * 博客详情 Composable
 *
 * 功能：
 * - 加载博客数据
 * - 格式化日期和字数
 * - Toast 通知
 * - 收藏功能
 */
export function useBlogDetail() {
  const router = useRouter()
  const blog = ref<Blog | null>(null)
  const isLoading = ref(true)
  const isFavorite = ref(false)
  const toast = ref<Toast>({ show: false, message: '', type: 'info' })

  /**
   * 显示 Toast 通知
   */
  const showToast = (message: string, type: 'info' | 'success' | 'error' = 'info') => {
    toast.value = { show: true, message, type }
    setTimeout(() => {
      toast.value.show = false
    }, 3000)
  }

  /**
   * 格式化日期
   */
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  /**
   * 格式化字数
   */
  const formatWordCount = (count: number) => {
    if (count >= 10000) {
      return (count / 10000).toFixed(1) + ' 万字'
    } else if (count >= 1000) {
      return (count / 1000).toFixed(1) + ' 千字'
    }
    return count + ' 字'
  }

  /**
   * 切换收藏状态
   */
  const toggleFavorite = () => {
    isFavorite.value = !isFavorite.value
    showToast(isFavorite.value ? '已添加到收藏' : '已取消收藏', 'success')
  }

  /**
   * 加载博客数据
   */
  const loadBlog = async (id: string) => {
    isLoading.value = true
    try {
      // 使用历史记录 API
      const response = await fetch(`/api/history/${id}`)
      const result = await response.json()

      if (result.success && result.record) {
        const record = result.record
        // 解析 outline 获取标签
        let outline: any = {}
        try {
          outline = JSON.parse(record.outline || '{}')
        } catch (e) {
          // 忽略解析错误
        }

        // 从 outline 或 markdown 中提取标题
        let blogTitle = outline.title || ''
        if (!blogTitle && record.markdown_content) {
          // 从 markdown 内容中提取第一个 # 标题
          const titleMatch = record.markdown_content.match(/^#\s+(.+)$/m)
          if (titleMatch) {
            blogTitle = titleMatch[1].trim()
          }
        }
        // 如果还没有标题，截取 topic 前 50 个字符
        if (!blogTitle) {
          blogTitle = (record.topic || '未命名博客').slice(0, 50)
          if (record.topic && record.topic.length > 50) {
            blogTitle += '...'
          }
        }

        // 计算字数
        const wordCount = (record.markdown_content || '').length

        // 计算图片数量
        const imageMatches = (record.markdown_content || '').match(/!\[.*?\]\(.*?\)/g)
        const imagesCount = imageMatches ? imageMatches.length : (record.images_count || 0)

        // 计算代码块数量
        const codeMatches = (record.markdown_content || '').match(/```[\s\S]*?```/g)
        const codeBlocksCount = codeMatches ? codeMatches.length : (record.code_blocks_count || 0)

        // 文章类型映射
        const articleTypeMap: Record<string, string> = {
          'mini': 'Mini',
          'short': '短文',
          'medium': '中等',
          'long': '长文',
          'custom': '自定义'
        }

        blog.value = {
          id: record.id,
          title: blogTitle,
          description: outline.summary || '',
          content: record.markdown_content || '',
          category: record.content_type || 'blog',
          theme: 'ai',
          tags: outline.keywords || [],
          author: 'vibe-blog',
          authorAvatar: 'https://avatars.githubusercontent.com/u/1?v=4',
          sourceUrl: '',
          stars: Math.floor(Math.random() * 1000) + 100,
          forks: Math.floor(Math.random() * 500) + 50,
          createdAt: record.created_at,
          updatedAt: record.created_at,
          // 博客属性
          articleType: articleTypeMap[record.article_type] || record.article_type || '短文',
          sectionsCount: record.sections_count || outline.sections?.length || 0,
          imagesCount: imagesCount,
          codeBlocksCount: codeBlocksCount,
          wordCount: wordCount,
          // 封面视频
          coverVideo: record.cover_video || ''
        }
      } else {
        showToast('加载失败: ' + (result.error || '记录不存在'), 'error')
        router.push('/')
      }
    } catch (e: any) {
      showToast('加载失败: ' + e.message, 'error')
      router.push('/')
    } finally {
      isLoading.value = false
    }
  }

  return {
    // 状态（只读）
    blog: readonly(blog),
    isLoading: readonly(isLoading),
    isFavorite: readonly(isFavorite),
    toast: readonly(toast),
    // 方法
    loadBlog,
    showToast,
    formatDate,
    formatWordCount,
    toggleFavorite
  }
}
