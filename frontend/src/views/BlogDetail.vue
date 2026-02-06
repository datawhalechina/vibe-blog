<template>
  <div class="blog-detail-container" :class="{ 'dark-mode': isDark }">
    <!-- 导航栏 -->
    <BlogDetailNav :category="blog?.category" />

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：博客内容 -->
      <div class="content-area">
        <BlogDetailBreadcrumb :title="blog?.title" />
        <BlogDetailTitle :title="blog?.title" :description="blog?.description" />
        <BlogDetailStats
          :stars="blog?.stars"
          :forks="blog?.forks"
          :updated-at="blog?.updatedAt"
          :format-date="formatDate"
        />
        <BlogDetailContent :content="renderedContent" :is-loading="isLoading" />
      </div>

      <!-- 右侧：侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-sticky">
          <AuthorCard
            :author="blog?.author"
            :author-avatar="blog?.authorAvatar"
            :category="blog?.category"
            :source-url="blog?.sourceUrl"
            :is-favorite="isFavorite"
            @toggle-favorite="toggleFavorite"
          />
          <TagsCard :tags="blog?.tags" />
          <StatsCard
            :article-type="blog?.articleType"
            :sections-count="blog?.sectionsCount"
            :images-count="blog?.imagesCount"
            :code-blocks-count="blog?.codeBlocksCount"
          />
          <DownloadCard
            :is-downloading="isDownloading"
            @download="handleDownload"
            @open-publish="handleOpenPublish"
          />
          <VideoCard :cover-video="blog?.coverVideo" />
        </div>
      </aside>
    </div>

    <!-- Toast 通知 -->
    <div v-if="toast.show" class="toast" :class="toast.type">
      <svg v-if="toast.type === 'success'" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <svg v-else-if="toast.type === 'error'" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
        <line x1="18" x2="6" y1="6" y2="18"></line>
        <line x1="6" x2="18" y1="6" y2="18"></line>
      </svg>
      <svg v-else class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M12 16v-4"></path>
        <path d="M12 8h.01"></path>
      </svg>
      {{ toast.message }}
    </div>

    <!-- 发布弹窗 -->
    <PublishModal
      :show="showPublishModal"
      :platform="publishPlatform"
      :cookie="publishCookie"
      :is-publishing="isPublishing"
      :status="publishStatus"
      :show-help="showCookieHelp"
      @close="closePublishModal"
      @update:platform="publishPlatform = $event"
      @update:cookie="publishCookie = $event"
      @toggle-help="showCookieHelp = !showCookieHelp"
      @publish="handlePublish"
    />

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from '../stores/theme'
import { useBlogDetail } from '../composables/useBlogDetail'
import { useMermaidRenderer } from '../composables/useMermaidRenderer'
import { useMarkdownRenderer } from '../composables/useMarkdownRenderer'
import { useDownload } from '../composables/useDownload'
import { usePublish } from '../composables/usePublish'

// 导入组件
import BlogDetailNav from '../components/blog-detail/BlogDetailNav.vue'
import BlogDetailBreadcrumb from '../components/blog-detail/BlogDetailBreadcrumb.vue'
import BlogDetailTitle from '../components/blog-detail/BlogDetailTitle.vue'
import BlogDetailStats from '../components/blog-detail/BlogDetailStats.vue'
import BlogDetailContent from '../components/blog-detail/BlogDetailContent.vue'
import AuthorCard from '../components/blog-detail/sidebar/AuthorCard.vue'
import TagsCard from '../components/blog-detail/sidebar/TagsCard.vue'
import StatsCard from '../components/blog-detail/sidebar/StatsCard.vue'
import DownloadCard from '../components/blog-detail/sidebar/DownloadCard.vue'
import VideoCard from '../components/blog-detail/sidebar/VideoCard.vue'
import PublishModal from '../components/blog-detail/PublishModal.vue'
import Footer from '../components/Footer.vue'

const route = useRoute()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)

// 使用 composables
const {
  blog,
  isLoading,
  isFavorite,
  toast,
  loadBlog,
  showToast,
  formatDate,
  toggleFavorite
} = useBlogDetail()

const { renderMermaid } = useMermaidRenderer()

const renderedContent = computed(() => {
  if (!blog.value?.content) return ''
  const { renderedContent } = useMarkdownRenderer(blog.value.content)
  return renderedContent.value
})

const { isDownloading, downloadMarkdown } = useDownload()

const {
  showPublishModal,
  publishPlatform,
  publishCookie,
  isPublishing,
  publishStatus,
  showCookieHelp,
  openPublishModal,
  closePublishModal,
  doPublish
} = usePublish()

// 下载处理
const handleDownload = () => {
  if (!blog.value) return
  downloadMarkdown(
    blog.value.content,
    blog.value.title,
    (message) => showToast(message, 'success'),
    (message) => showToast(message, 'error')
  )
}

// 打开发布弹窗
const handleOpenPublish = () => {
  if (!blog.value) return
  openPublishModal(blog.value.content, (message) => showToast(message, 'error'))
}

// 发布处理
const handlePublish = () => {
  if (!blog.value) return
  doPublish(
    blog.value.title,
    blog.value.content,
    (message) => showToast(message, 'error')
  )
}

// 生命周期
onMounted(() => {
  const id = route.params.id as string
  if (id) {
    loadBlog(id)
  }
})

// 监听内容变化，渲染 Mermaid
watch(() => blog.value?.content, () => {
  setTimeout(renderMermaid, 100)
})
</script>

<style scoped>
.blog-detail-container {
  --bg: #ffffff;
  --surface: #f8fafc;
  --surface-hover: #f1f5f9;
  --border: #e2e8f0;
  --text: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --primary: #8b5cf6;
  --primary-light: rgba(139, 92, 246, 0.1);
  --keyword: #8b5cf6;
  --string: #22c55e;
  --number: #f59e0b;
  --comment: #64748b;
  --function: #3b82f6;
  --variable: #ec4899;
  --star: #eab308;
  --fork: #3b82f6;
  --calendar: #22c55e;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
  --glass-bg: rgba(255, 255, 255, 0.8);
  --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, var(--surface) 0%, #f1f5f9 50%, #dbeafe 100%);
  color: var(--text);
}

.blog-detail-container.dark-mode {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-hover: #334155;
  --border: #334155;
  --text: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --keyword: #a78bfa;
  --string: #4ade80;
  --number: #fbbf24;
  --function: #60a5fa;
  --variable: #f472b6;
  --glass-bg: rgba(15, 23, 42, 0.85);
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #172554 100%);
}

/* 主内容区 */
.main-content {
  display: flex;
  gap: 32px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.content-area {
  flex: 1;
  min-width: 0;
}

/* 侧边栏 */
.sidebar {
  width: 350px;
  flex-shrink: 0;
}

.sidebar-sticky {
  position: sticky;
  top: 88px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: calc(100vh - 112px);
  overflow-y: auto;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 14px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  z-index: 1001;
  box-shadow: var(--shadow-lg);
  animation: toastIn 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 10px;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.toast.success {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
  color: #16a34a;
}

.toast.error {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #dc2626;
}

.toast-icon {
  flex-shrink: 0;
}

/* 响应式 */
@media (max-width: 1024px) {
  .main-content {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .sidebar-sticky {
    position: static;
    max-height: none;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
}
</style>
