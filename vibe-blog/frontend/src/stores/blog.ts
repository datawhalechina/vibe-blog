import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import axios from 'axios'

export const useBlogStore = defineStore('blog', () => {
  const blogs = ref([])
  const currentBlog = ref(null)
  const isLoading = ref(false)
  const progress = reactive({
    visible: false,
    items: [],
    status: 'idle'
  })

  const generateBlog = async (topic: string) => {
    isLoading.value = true
    progress.visible = true
    progress.items = []
    progress.status = 'generating'

    try {
      const response = await axios.post('/api/blog/generate', {
        topic,
        articleType: 'tutorial',
        articleLength: 'medium'
      }, {
        responseType: 'stream'
      })

      // 处理流式响应
      const reader = response.data.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              progress.items.push({
                type: data.type,
                message: data.message,
                timestamp: new Date().toLocaleTimeString()
              })
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }

      progress.status = 'completed'
    } catch (error) {
      progress.status = 'error'
      progress.items.push({
        type: 'error',
        message: '生成失败',
        timestamp: new Date().toLocaleTimeString()
      })
    } finally {
      isLoading.value = false
    }
  }

  const fetchBlogs = async () => {
    try {
      const response = await axios.get('/api/blog/list')
      blogs.value = response.data
    } catch (error) {
      console.error('获取博客列表失败', error)
    }
  }

  return {
    blogs,
    currentBlog,
    isLoading,
    progress,
    generateBlog,
    fetchBlogs
  }
})
