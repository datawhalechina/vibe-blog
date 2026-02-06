<template>
  <div class="xhs-container" :class="{ 'dark-mode': isDark }">
    <!-- 终端风格导航栏 -->
    <nav class="terminal-nav">
      <div class="terminal-nav-left">
        <div class="terminal-dots">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="terminal-title">$ xhs-creator --generate</span>
      </div>
      <div class="terminal-nav-right">
        <a
          href="https://github.com/datawhalechina/vibe-blog"
          target="_blank"
          rel="noopener noreferrer"
          class="nav-cmd"
          title="GitHub - vibe-blog"
        >
          GitHub
        </a>
        <router-link to="/" class="nav-cmd">cd ~/blog</router-link>
        <button class="theme-toggle" @click="themeStore.toggleTheme()">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>

    <!-- 页面标题 -->
    <div class="container">
      <div class="page-title">
        <h1>> 小红书创作助手_</h1>
        <p class="code-comment">// 输入主题，一键生成小红书风格信息图系列</p>
      </div>

      <!-- 输入卡片 -->
      <XhsInputCard
        v-model:topic="topic"
        v-model:page-count="pageCount"
        v-model:visual-style="visualStyle"
        v-model:generate-video="generateVideo"
        :is-loading="generator.isLoading.value"
        :error-msg="generator.errorMsg.value"
        @generate="handleGenerate"
      />

      <!-- 进度面板 -->
      <XhsProgressPanel
        :show="showProgress"
        :progress-percent="progress.progressPercent.value"
        :progress-title="progress.progressTitle.value"
        :current-stage-text="progress.currentStageText.value"
        :time-estimate="progress.timeEstimate.value"
        :image-sub-progress="progress.imageSubProgress.value"
        :stages="progress.stages"
        :stage-statuses="progress.stageStatuses"
        :stage-details="progress.stageDetails"
        :get-stage-class="progress.getStageClass"
        :get-stage-status="progress.getStageStatus"
        @cancel="handleCancel"
      />

      <!-- 结果区域 -->
      <div v-if="showResult" class="result-container">
        <!-- 图片槽位 -->
        <XhsImageSlots
          :show="showResult"
          :image-slots="images.imageSlots.value"
          @copy-prompt="images.copyPrompt"
          @update-tooltip="handleUpdateTooltip"
        />

        <!-- 文案展示 -->
        <XhsResultDisplay
          :show="showResult"
          :result="generator.currentResult.value"
          @copy-copywriting="handleCopyCopywriting"
          @download-images="handleDownloadImages"
          @open-publish="publish.openModal"
        />

        <!-- 视频生成器 -->
        <XhsVideoGenerator
          :show="showResult"
          v-model:video-model="video.videoModel.value"
          v-model:video-style="video.videoStyle.value"
          v-model:video-duration="video.videoDuration.value"
          :is-generating="video.isGenerating.value"
          :show-progress="video.showProgress.value"
          :progress-percent="video.progressPercent.value"
          :progress-text="video.progressText.value"
          :video-url="video.videoUrl.value"
          @generate="handleGenerateVideo"
          @download="video.download"
          @copy-url="video.copyUrl"
        />
      </div>
    </div>

    <!-- 发布弹窗 -->
    <XhsPublishModal
      :show="publish.showModal.value"
      v-model:cookie="publish.cookieInput.value"
      @close="publish.closeModal"
      @publish="handlePublish"
    />

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import * as api from '../services/api'
import { useThemeStore } from '../stores/theme'

// Composables
import { useXhsGenerator } from '../composables/xhs/useXhsGenerator'
import { useXhsProgress } from '../composables/xhs/useXhsProgress'
import { useXhsImages } from '../composables/xhs/useXhsImages'
import { useXhsVideo } from '../composables/xhs/useXhsVideo'
import { useXhsPublish } from '../composables/xhs/useXhsPublish'

// Components
import XhsInputCard from '../components/xhs-creator/XhsInputCard.vue'
import XhsProgressPanel from '../components/xhs-creator/XhsProgressPanel.vue'
import XhsImageSlots from '../components/xhs-creator/XhsImageSlots.vue'
import XhsResultDisplay from '../components/xhs-creator/XhsResultDisplay.vue'
import XhsVideoGenerator from '../components/xhs-creator/XhsVideoGenerator.vue'
import XhsPublishModal from '../components/xhs-creator/XhsPublishModal.vue'
import Footer from '../components/Footer.vue'

const route = useRoute()
const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)

// 输入状态
const topic = ref('')
const pageCount = ref('4')
const visualStyle = ref('hand_drawn')
const generateVideo = ref('false')

// UI 状态
const showProgress = ref(false)
const showResult = ref(false)

// 使用 composables
const generator = useXhsGenerator()
const progress = useXhsProgress()
const images = useXhsImages()
const video = useXhsVideo()
const publish = useXhsPublish()

// 大纲和分镜数据
const outlineData = ref<any>(null)
const storyboardPrompts = ref<any[]>([])

/**
 * 开始生成
 */
const handleGenerate = async () => {
  if (!topic.value.trim()) return

  showProgress.value = true
  showResult.value = false
  progress.reset()
  images.initPlaceholders(parseInt(pageCount.value))
  showResult.value = true

  const result = await generator.generate(
    {
      topic: topic.value,
      count: parseInt(pageCount.value),
      style: visualStyle.value,
      generate_video: generateVideo.value === 'true'
    },
    {
      onProgress: (data) => {
        progress.updateProgress(data.progress, data.message)
        progress.updateStageIndicators(data.stage, data.sub_progress)
      },
      onSearch: (data) => {
        progress.updateStageDetail(
          'search',
          `${data.results_count} 条结果\n来源: ${data.sources?.join(', ') || '通用'}`
        )
      },
      onOutline: (data) => {
        progress.updateStageDetail('outline', `${data.summary || ''}\n点击查看完整大纲`)
        outlineData.value = data
      },
      onContent: (data) => {
        progress.updateStageDetail(
          'content',
          `标题: ${data.titles?.[0] || ''}\n标签: ${data.tags?.slice(0, 3).join(', ') || ''}`
        )
      },
      onStoryboard: (data) => {
        progress.updateStageDetail('storyboard', `共 ${data.total} 个分镜\n悬浮图片查看视觉指令`)
        storyboardPrompts.value = data.prompts || []
        if (data.prompts) {
          images.setImagePrompts(data.prompts)
        }
      },
      onImageProgress: (data) => {
        if (data.status === 'generating') {
          images.updateImageStatus(data.index, `第 ${data.index + 1} 页 生成中...`)
        } else if (data.status === 'failed') {
          images.updateImageStatus(data.index, `第 ${data.index + 1} 页 失败`)
        }
      },
      onImage: (data) => {
        images.setImageUrl(data.index, data.url)
      },
      onVideo: (data) => {
        progress.updateStageDetail('video', '动画封面已生成')
      },
      onComplete: (data) => {
        progress.markComplete()
        images.ensureAllImagesLoaded(data.image_urls || [])

        setTimeout(() => {
          showProgress.value = false
        }, 3000)
      },
      onError: (message) => {
        progress.markError(message)
        setTimeout(() => {
          showProgress.value = false
        }, 5000)
      },
      onCancelled: () => {
        progress.markCancelled()
        setTimeout(() => {
          showProgress.value = false
        }, 3000)
      }
    }
  )
}

/**
 * 取消生成
 */
const handleCancel = async () => {
  await generator.cancel()
}

/**
 * 复制文案
 */
const handleCopyCopywriting = () => {
  publish.copyCopywriting(generator.currentResult.value)
}

/**
 * 下载图片
 */
const handleDownloadImages = () => {
  const urls = generator.currentResult.value?.image_urls
  if (urls) {
    images.downloadAll(urls)
  }
}

/**
 * 生成讲解视频
 */
const handleGenerateVideo = async () => {
  const urls = generator.currentResult.value?.image_urls
  if (!urls) return

  // 获取每张图片对应的文案
  const scripts: string[] = []
  if (outlineData.value?.pages) {
    outlineData.value.pages.forEach((p: any) => scripts.push(p.content || ''))
  } else if (generator.currentResult.value?.pages) {
    generator.currentResult.value.pages.forEach((p) => scripts.push(p.content || ''))
  }
  while (scripts.length < urls.length) scripts.push('')

  await video.generate(urls, scripts)
}

/**
 * 发布到小红书
 */
const handlePublish = async () => {
  const result = await publish.publish(generator.currentResult.value)

  if (result.success) {
    alert('🎉 发布成功！' + (result.url ? '\n笔记链接: ' + result.url : ''))
    publish.closeModal()
  } else {
    alert('❌ 发布失败: ' + result.error)
  }
}

/**
 * 更新图片 tooltip
 */
const handleUpdateTooltip = (index: number, show: boolean) => {
  if (images.imageSlots.value[index]) {
    images.imageSlots.value[index].showTooltip = show
  }
}

/**
 * 加载历史记录
 */
const loadXhsHistory = async (historyId: string) => {
  try {
    const data = await api.getHistoryRecord(historyId)

    if (data.success && data.record) {
      const record = data.record as any
      topic.value = record.topic || ''

      let imageUrls: string[] = []
      try {
        imageUrls = JSON.parse(record.xhs_image_urls || '[]')
      } catch (e) {}

      let tags: string[] = []
      try {
        tags = JSON.parse(record.xhs_hashtags || '[]')
      } catch (e) {}

      // 更新结果（通过直接修改 ref）
      ;(generator.currentResult as any).value = {
        id: record.id,
        topic: record.topic,
        image_urls: imageUrls,
        video_url: record.cover_video || '',
        titles: [record.topic],
        copywriting: record.xhs_copy_text || '',
        tags
      }

      images.loadFromHistory(imageUrls)
      showResult.value = true
    }
  } catch (error) {
    console.error('加载小红书历史详情失败:', error)
    alert('加载历史记录失败')
  }
}

// 初始化
onMounted(() => {
  const urlTopic = route.query.topic as string
  const sourceId = route.query.source_id as string
  const historyId = route.query.history_id as string

  if (urlTopic) topic.value = urlTopic
  if (sourceId) (window as any).xhsSourceId = sourceId
  if (historyId) loadXhsHistory(historyId)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS 变量 */
.xhs-container {
  --code-bg: #ffffff;
  --code-surface: #f8fafc;
  --code-surface-hover: #f1f5f9;
  --code-border: #e2e8f0;
  --code-text: #1e293b;
  --code-text-secondary: #64748b;
  --code-text-muted: #94a3b8;
  --code-keyword: #8b5cf6;
  --code-string: #22c55e;
  --code-number: #f59e0b;
  --code-comment: #64748b;
  --code-function: #3b82f6;
  --code-variable: #ec4899;
  --code-operator: #6b7280;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  --glass-bg: rgba(255, 255, 255, 0.85);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, var(--code-surface) 0%, #fdf4ff 50%, #fce7f3 100%);
  color: var(--code-text);
}

/* 深色模式 */
.xhs-container.dark-mode {
  --code-bg: #0f172a;
  --code-surface: #1e293b;
  --code-surface-hover: #334155;
  --code-border: #334155;
  --code-text: #f1f5f9;
  --code-text-secondary: #94a3b8;
  --code-text-muted: #64748b;
  --code-keyword: #a78bfa;
  --code-string: #4ade80;
  --code-number: #fbbf24;
  --code-function: #60a5fa;
  --code-variable: #f472b6;
  --glass-bg: rgba(15, 23, 42, 0.9);
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #4a1d6a 100%);
}

/* 终端导航栏 */
.terminal-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 28px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--code-border);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all var(--transition-normal);
}

.terminal-nav-left,
.terminal-nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.terminal-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  cursor: pointer;
}

.dot:hover {
  transform: scale(1.2);
}

.dot.red {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
}

.dot.yellow {
  background: linear-gradient(135deg, #eab308, #ca8a04);
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.4);
}

.dot.green {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
}

.terminal-title {
  font-size: 13px;
  color: var(--code-text-secondary);
  letter-spacing: 0.3px;
}

.nav-cmd {
  font-size: 13px;
  color: var(--code-function);
  text-decoration: none;
  padding: 8px 16px;
  background: var(--code-surface);
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.nav-cmd:hover {
  background: var(--code-surface-hover);
  border-color: var(--code-function);
  transform: translateY(-1px);
}

.theme-toggle {
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  font-size: 16px;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  background: var(--code-surface-hover);
  transform: rotate(15deg) scale(1.1);
}

/* 容器 */
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

/* 页面标题 */
.page-title {
  margin-bottom: 32px;
}

.page-title h1 {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--code-text) 0%, var(--code-variable) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.code-comment {
  color: var(--code-comment);
  font-style: italic;
  font-size: 14px;
  margin-top: 10px;
  opacity: 0.8;
}

/* 结果容器 */
.result-container {
  margin-top: 24px;
}

/* 响应式 */
@media (max-width: 768px) {
  .terminal-nav {
    padding: 12px 16px;
  }

  .terminal-title {
    display: none;
  }

  .container {
    padding: 16px;
  }
}
</style>
