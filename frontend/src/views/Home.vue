<template>
  <div class="home-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="bg-animation"></div>

    <!-- 导航栏 -->
    <AppNavbar :app-config="appConfig" />

    <!-- Fullpage 滑动容器 -->
    <div
      class="fullpage-container"
      @wheel="onWheel"
      @touchstart="onTouchStart"
      @touchend="onTouchEnd"
    >
      <div class="fullpage-track" :style="{ transform: `translateY(-${currentSection * 100}vh)` }">
        <!-- 第一屏：Hero + 输入框 -->
        <section ref="sectionRefs" class="fullpage-section">
          <div class="first-screen">
            <HeroSection />
            <div class="main-content-wrapper">
              <div class="content-container">
                <BlogInputCard
                  v-model:topic="topic"
                  v-model:show-advanced-options="showAdvancedOptions"
                  :uploaded-documents="uploadedDocuments"
                  :is-loading="isLoading"
                  :is-enhancing="isEnhancing"
                  @generate="handleGenerate"
                  @enhance-topic="handleEnhanceTopic"
                  @file-upload="handleFileUpload"
                  @remove-document="removeDocument"
                />
                <div class="advanced-options-anchor">
                  <Transition name="slide-down">
                    <AdvancedOptionsPanel
                      v-if="showAdvancedOptions"
                      v-model:article-type="articleType"
                      v-model:target-length="targetLength"
                      v-model:audience-adaptation="audienceAdaptation"
                      v-model:image-style="imageStyle"
                      v-model:generate-cover-video="generateCoverVideo"
                      v-model:video-aspect-ratio="videoAspectRatio"
                      v-model:deep-thinking="deepThinking"
                      v-model:background-investigation="backgroundInvestigation"
                      v-model:interactive="interactive"
                      v-model:custom-config="customConfig"
                      :image-styles="imageStyles"
                      :app-config="appConfig"
                    />
                  </Transition>
                </div>
              </div>
            </div>
            <div class="scroll-hint" @click="goToSection(1)">
              <span class="scroll-hint-text">scroll</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="scroll-hint-arrow">
                <path d="M12 5v14M5 12l7 7 7-7"/>
              </svg>
            </div>
            <Footer class="first-screen-footer" />
          </div>
        </section>

        <!-- 第二屏：历史记录（保持原布局） -->
        <section ref="secondSectionRef" class="fullpage-section">
          <div class="history-section history-visible">
            <div class="content-container">
              <BlogHistoryList
                :show-list="showBlogList"
                :current-tab="currentHistoryTab"
                :content-type="historyContentType"
                v-model:show-cover-preview="showCoverPreview"
                :records="historyRecords"
                :total="historyTotal"
                :current-page="historyCurrentPage"
                :total-pages="historyTotalPages"
                :content-type-filters="contentTypeFilters"
                :animated="currentSection >= 1"
                @toggle-list="showBlogList = !showBlogList"
                @switch-tab="switchHistoryTab"
                @filter-content-type="filterByContentType"
                @load-detail="loadHistoryDetail"
                @load-more="loadMoreHistory"
              />
            </div>
          </div>
          <Footer />
        </section>
      </div>

      <!-- 侧边指示器 -->
      <div class="section-indicators">
        <div
          v-for="i in totalSections"
          :key="i"
          class="section-dot"
          :class="{ active: currentSection === i - 1 }"
          @click="goToSection(i - 1)"
        />
      </div>
    </div>

    <!-- 进度面板 - fixed 定位，放在顶层 -->
    <ProgressDrawer
      :visible="showProgress"
      :expanded="terminalExpanded"
      :is-loading="isLoading"
      :status-badge="statusBadge"
      :progress-text="progressText"
      :progress-items="progressItems"
      :article-type="articleType"
      :target-length="targetLength"
      :task-id="currentTaskId"
      :outline-data="outlineData"
      :waiting-for-outline="waitingForOutline"
      :preview-content="previewContent"
      @toggle="toggleTerminal"
      @close="closeProgress"
      @stop="stopGeneration"
      @confirm-outline="handleConfirmOutline"
    />

    <!-- 发布弹窗 -->
    <PublishModal
      :visible="showPublishModal"
      v-model:platform="publishPlatform"
      v-model:cookie="publishCookie"
      :is-publishing="isPublishing"
      :status="publishStatus"
      :status-type="publishStatusType"
      @close="showPublishModal = false"
      @publish="doPublish"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '../stores/theme'
import * as api from '../services/api'
import { isSpinningStatus } from '../utils/helpers'

// Components
import AppNavbar from '../components/home/AppNavbar.vue'
import HeroSection from '../components/home/HeroSection.vue'
import BlogInputCard from '../components/home/BlogInputCard.vue'
import AdvancedOptionsPanel from '../components/home/AdvancedOptionsPanel.vue'
import ProgressDrawer from '../components/home/ProgressDrawer.vue'
import BlogHistoryList from '../components/home/BlogHistoryList.vue'
import PublishModal from '../components/home/PublishModal.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()
const themeStore = useThemeStore()

// ========== 应用配置 ==========
const appConfig = reactive<{ features: Record<string, boolean> }>({ features: {} })
const isDarkMode = computed(() => themeStore.isDark)

// ========== 输入状态 ==========
const topic = ref('')
const showAdvancedOptions = ref(false)

// ========== Fullpage 滑动 ==========
const currentSection = ref(0)
const totalSections = 2
const secondSectionRef = ref<HTMLElement | null>(null)
let isAnimating = false
let wheelAccum = 0

const goToSection = (index: number) => {
  if (isAnimating || index < 0 || index >= totalSections || index === currentSection.value) return
  isAnimating = true
  currentSection.value = index
  setTimeout(() => { isAnimating = false }, 700)
}

const onWheel = (e: WheelEvent) => {
  // 第二屏：检查是否在滚动边界
  if (currentSection.value === 1 && secondSectionRef.value) {
    const el = secondSectionRef.value
    const atTop = el.scrollTop <= 0
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1

    // 在顶部往上滑 → 回到第一屏
    if (atTop && e.deltaY < 0) {
      e.preventDefault()
      goToSection(0)
      return
    }
    // 没到边界 → 让内容正常滚动，不拦截
    if (!atBottom || e.deltaY <= 0) return
  }

  // 第一屏：拦截滚动，触发翻页
  if (currentSection.value === 0) {
    e.preventDefault()
    wheelAccum += e.deltaY
    if (Math.abs(wheelAccum) > 50) {
      if (wheelAccum > 0) goToSection(1)
      wheelAccum = 0
    }
  }
}

let touchStartY = 0
const onTouchStart = (e: TouchEvent) => { touchStartY = e.touches[0].clientY }
const onTouchEnd = (e: TouchEvent) => {
  const diff = touchStartY - e.changedTouches[0].clientY
  if (currentSection.value === 1 && secondSectionRef.value) {
    const atTop = secondSectionRef.value.scrollTop <= 0
    if (diff < -50 && atTop) { goToSection(0); return }
    return // 第二屏内让触摸滚动正常工作
  }
  if (Math.abs(diff) > 50) {
    if (diff > 0) goToSection(1)
  }
}

// ========== 高级选项 ==========
const articleType = ref('tutorial')
const targetLength = ref('mini')
const audienceAdaptation = ref('default')
const imageStyle = ref('cartoon')
const generateCoverVideo = ref(false)
const videoAspectRatio = ref('16:9')
const deepThinking = ref(false)
const backgroundInvestigation = ref(true)
const interactive = ref(true)
const imageStyles = ref<Array<{ id: string; name: string; icon: string }>>([
  { id: 'cartoon', name: '默认风格', icon: '🎨' }
])
const customConfig = reactive({
  sectionsCount: 4,
  imagesCount: 4,
  codeBlocksCount: 2,
  targetWordCount: 3500
})

// ========== 文档上传 ==========
interface UploadedDocument {
  id: string
  filename: string
  status: string
  fileSize?: number
  wordCount?: number
  errorMessage?: string
}
const uploadedDocuments = ref<UploadedDocument[]>([])

// ========== 生成状态 ==========
const isLoading = ref(false)
const isEnhancing = ref(false)
const showProgress = ref(false)
const terminalExpanded = ref(true)
const currentTaskId = ref<string | null>(null)
let eventSource: EventSource | null = null

// ========== 交互式模式状态 ==========
const outlineData = ref<{ title: string; sections_titles: string[]; sections?: any[] } | null>(null)
const waitingForOutline = ref(false)
const previewContent = ref('')

// ========== 进度面板 ==========
interface ProgressItem {
  time: string
  message: string
  type: string
  detail?: string
}
const progressItems = ref<ProgressItem[]>([])
const statusBadge = ref('准备中')
const progressText = ref('等待开始')

// ========== 历史记录 ==========
const showBlogList = ref(true)
const currentHistoryTab = ref('blogs')
const historyContentType = ref('all')
const showCoverPreview = ref(false)
const historyRecords = ref<api.HistoryRecord[]>([])
const historyTotal = ref(0)
const historyCurrentPage = ref(1)
const historyTotalPages = ref(1)
const contentTypeFilters = ref([
  { label: '全部', value: 'all' },
  { label: '博客', value: 'blog' },
  { label: '小红书', value: 'xhs' }
])

// ========== 发布 ==========
const showPublishModal = ref(false)
const publishPlatform = ref('csdn')
const publishCookie = ref('')
const isPublishing = ref(false)
const publishStatus = ref('')
const publishStatusType = ref('')

// ========== 文件上传 ==========
const handleFileUpload = async (files: FileList) => {
  for (const file of Array.from(files)) {
    await uploadDocument(file)
  }
}

const uploadDocument = async (file: File) => {
  const tempId = 'temp_' + Date.now()
  uploadedDocuments.value.push({
    id: tempId,
    filename: file.name,
    status: 'uploading',
    fileSize: file.size
  })

  try {
    const data = await api.uploadDocument(file)
    uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== tempId)

    if (data.success && data.document_id) {
      uploadedDocuments.value.push({
        id: data.document_id,
        filename: data.filename || file.name,
        status: data.status || 'pending',
        fileSize: file.size
      })
      pollDocumentStatus(data.document_id)
    } else {
      alert('上传失败: ' + (data.error || '未知错误'))
    }
  } catch (error: any) {
    uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== tempId)
    alert('上传失败: ' + error.message)
  }
}

const pollDocumentStatus = async (docId: string) => {
  let attempts = 0
  const maxAttempts = 60

  const poll = async () => {
    if (attempts >= maxAttempts) {
      updateDocStatus(docId, 'timeout')
      return
    }

    try {
      const data = await api.getDocumentStatus(docId)
      if (data.success) {
        updateDocStatus(docId, data.status || 'pending', data.markdown_length, data.error_message)
        if (data.status === 'ready' || data.status === 'error') return
      }
    } catch (error) {
      console.error('Poll document status error:', error)
    }

    attempts++
    setTimeout(poll, 2000)
  }

  poll()
}

const updateDocStatus = (docId: string, status: string, wordCount?: number, errorMessage?: string) => {
  const doc = uploadedDocuments.value.find(d => d.id === docId)
  if (doc) {
    doc.status = status
    if (wordCount) doc.wordCount = wordCount
    if (errorMessage) doc.errorMessage = errorMessage
  }
}

const removeDocument = (docId: string) => {
  uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== docId)
}

const getReadyDocumentIds = () => {
  return uploadedDocuments.value.filter(d => d.status === 'ready').map(d => d.id)
}

// ========== 主题优化（Prompt 增强） ==========
const handleEnhanceTopic = async () => {
  if (!topic.value.trim() || isEnhancing.value || isLoading.value) return
  isEnhancing.value = true
  try {
    const data = await api.enhanceTopic(topic.value)
    if (data.success && data.enhanced_topic) {
      topic.value = data.enhanced_topic
    }
  } catch (error: any) {
    console.error('主题优化失败:', error)
  } finally {
    isEnhancing.value = false
  }
}

// ========== 大纲确认（交互式模式） ==========
const handleConfirmOutline = async (action: string) => {
  if (!currentTaskId.value) return
  waitingForOutline.value = false
  try {
    const data = await api.confirmOutline(currentTaskId.value, action as 'accept' | 'edit')
    if (data.success) {
      addProgressItem(action === 'accept' ? '✓ 大纲已确认，开始写作' : '✓ 大纲已修改，重新规划', 'success')
      progressText.value = '写作中...'
    }
  } catch (error: any) {
    addProgressItem(`✗ 大纲确认失败: ${error.message}`, 'error')
  }
}

// ========== 生成博客 ==========
const handleGenerate = async () => {
  if (!topic.value.trim() || isLoading.value) return

  isLoading.value = true
  showProgress.value = true
  progressItems.value = []
  statusBadge.value = '准备中'
  outlineData.value = null
  waitingForOutline.value = false
  previewContent.value = ''

  const isStorybook = articleType.value === 'storybook'
  const isMini = targetLength.value === 'mini'
  const taskName = isStorybook ? '科普绘本' : (isMini ? 'Mini 博客' : '博客')
  progressText.value = `正在创建${taskName}生成任务...`

  try {
    let data: { success: boolean; task_id?: string; error?: string }

    if (isStorybook) {
      data = await api.createStorybookTask({
        content: topic.value,
        page_count: targetLength.value === 'short' ? 5 : (targetLength.value === 'medium' ? 8 : 12),
        target_audience: '技术小白',
        style: '可爱卡通风',
        generate_images: true
      })
    } else if (isMini) {
      data = await api.createMiniBlogTask({
        topic: topic.value,
        article_type: articleType.value,
        audience_adaptation: audienceAdaptation.value,
        image_style: imageStyle.value,
        document_ids: getReadyDocumentIds()
      })
    } else {
      const params: api.BlogGenerateParams = {
        topic: topic.value,
        article_type: articleType.value,
        target_length: targetLength.value,
        audience_adaptation: audienceAdaptation.value,
        document_ids: getReadyDocumentIds(),
        image_style: imageStyle.value,
        generate_cover_video: generateCoverVideo.value,
        video_aspect_ratio: videoAspectRatio.value,
        deep_thinking: deepThinking.value,
        background_investigation: backgroundInvestigation.value,
        interactive: interactive.value,
      }

      if (targetLength.value === 'custom') {
        params.custom_config = {
          sections_count: customConfig.sectionsCount,
          images_count: customConfig.imagesCount,
          code_blocks_count: customConfig.codeBlocksCount,
          target_word_count: customConfig.targetWordCount
        }
      }

      data = await api.createBlogTask(params)
    }

    if (data.success && data.task_id) {
      currentTaskId.value = data.task_id
      if (isStorybook) {
        // 绘本任务保持原有 SSE 逻辑
        addProgressItem(`✓ 任务创建成功 (ID: ${data.task_id})`, 'success')
        connectSSE(data.task_id)
      } else {
        // 博客/Mini 任务跳转到 Generate 页面
        router.push(`/generate/${data.task_id}`)
        return
      }
    } else {
      addProgressItem(`✗ 任务创建失败: ${data.error || '未知错误'}`, 'error')
      statusBadge.value = '错误'
      isLoading.value = false
    }
  } catch (error: any) {
    addProgressItem(`✗ 请求失败: ${error.message}`, 'error')
    statusBadge.value = '错误'
    isLoading.value = false
  }
}

// 流式预览节流（100ms）
let accumulatedPreview = ''
let completedSectionsContent = ''  // 已完成章节的累积内容
let currentSectionTitle = ''       // 当前正在写的章节标题
let previewTimer: ReturnType<typeof setTimeout> | null = null
const throttledUpdatePreview = (content: string) => {
  if (previewTimer) return
  previewTimer = setTimeout(() => {
    previewContent.value = content
    previewTimer = null
  }, 100)
}

const connectSSE = (taskId: string) => {
  accumulatedPreview = ''
  completedSectionsContent = ''
  currentSectionTitle = ''
  eventSource = api.createTaskStream(taskId)

  eventSource.addEventListener('connected', () => {
    addProgressItem('🔗 已连接到服务器')
    statusBadge.value = '运行中'
  })

  eventSource.addEventListener('progress', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    const icon = getStageIcon(d.stage)
    addProgressItem(`${icon} ${d.message}`, d.stage === 'error' ? 'error' : 'info')
    progressText.value = d.message
  })

  eventSource.addEventListener('log', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    let icon = '📝'
    const loggerIcons: Record<string, string> = {
      generator: '⚙️', researcher: '🔍', planner: '📋', writer: '✍️',
      questioner: '❓', coder: '💻', artist: '🎨', reviewer: '✅',
      assembler: '📦', search_service: '🌐', blog_service: '🖼️'
    }
    icon = loggerIcons[d.logger] || icon
    const isSuccess = d.message?.includes('完成') || d.message?.includes('成功')
    addProgressItem(`${icon} ${d.message}`, isSuccess ? 'success' : 'info')
    progressText.value = d.message
  })

  eventSource.addEventListener('stream', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    if (d.stage === 'outline') updateStreamItem(d.accumulated)
  })

  // 交互式模式：大纲待确认
  eventSource.addEventListener('outline_ready', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    outlineData.value = {
      title: d.title || '',
      sections_titles: d.sections_titles || [],
      sections: d.sections || [],
    }
    waitingForOutline.value = true
    addProgressItem('📋 大纲已生成，等待确认...', 'info')
    progressText.value = '等待大纲确认'
  })

  // 流式写作内容（两种模式都有）
  eventSource.addEventListener('writing_chunk', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    const sectionTitle = d.section_title || ''
    // 检测章节切换：把之前章节的内容存入已完成缓冲区
    if (sectionTitle && sectionTitle !== currentSectionTitle) {
      if (currentSectionTitle) {
        completedSectionsContent = accumulatedPreview
      }
      currentSectionTitle = sectionTitle
    }
    if (d.accumulated) {
      accumulatedPreview = completedSectionsContent
        ? completedSectionsContent + '\n\n' + d.accumulated
        : d.accumulated
      throttledUpdatePreview(accumulatedPreview)
    } else if (d.delta) {
      accumulatedPreview += d.delta
      throttledUpdatePreview(accumulatedPreview)
    }
  })

  eventSource.addEventListener('result', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    const data = d.data || {}

    switch (d.type) {
      case 'search_started':
        progressItems.value.push({
          time: new Date().toLocaleTimeString(),
          message: `🔍 搜索: ${data.query || ''}`,
          type: 'search',
          data: { query: data.query, searching: true },
        })
        break

      case 'search_results': {
        let idx = -1
        for (let si = progressItems.value.length - 1; si >= 0; si--) {
          const it = progressItems.value[si]
          if (it.type === 'search' && it.data?.searching) {
            if (it.data?.query === data.query) { idx = si; break }
            if (idx < 0) idx = si
          }
        }
        if (idx >= 0) {
          progressItems.value[idx] = {
            time: new Date().toLocaleTimeString(),
            message: `🔍 ${data.query || '搜索结果'}`,
            type: 'search',
            data: data,
          }
        } else {
          progressItems.value.push({
            time: new Date().toLocaleTimeString(),
            message: `🔍 ${data.query || '搜索结果'}`,
            type: 'search',
            data: data,
          })
        }
        break
      }

      case 'crawl_completed':
        if (data.url) {
          progressItems.value.push({
            time: new Date().toLocaleTimeString(),
            message: `📖 正在阅读: ${data.title || data.url}`,
            type: 'crawl',
            data: data,
          })
        } else if (data.count) {
          addProgressItem(`📖 深度抓取完成: ${data.count} 篇高质量素材`, 'success')
        }
        break

      case 'search_completed':
        // 将残留的 searching 骨架屏转换为完成状态（不删除，保留动画体验）
        for (let ci = progressItems.value.length - 1; ci >= 0; ci--) {
          const it = progressItems.value[ci]
          if (it.type === 'search' && it.data?.searching) {
            progressItems.value[ci] = {
              time: new Date().toLocaleTimeString(),
              message: `✅ 搜索完成: ${it.data?.query || ''}`,
              type: 'success',
            }
          }
        }
        addProgressItem(`✅ ${data.message || '搜索完成'}`, 'success')
        break

      case 'researcher_complete':
        // 兜底：清除所有残留的 searching 骨架屏
        for (let ci = progressItems.value.length - 1; ci >= 0; ci--) {
          const it = progressItems.value[ci]
          if (it.type === 'search' && it.data?.searching) {
            progressItems.value.splice(ci, 1)
          }
        }
        if (data.document_count > 0 || data.web_count > 0) {
          addProgressItem(`📊 知识来源: 文档 ${data.document_count} 条, 网络 ${data.web_count} 条`, 'info')
        }
        if (data.key_concepts?.length > 0) {
          addProgressItem(`💡 核心概念: ${data.key_concepts.join(', ')}`, 'success')
        }
        addProgressItem('素材收集阶段结束', 'divider')
        break

      case 'outline_complete':
        if (data.sections_titles?.length > 0) {
          const titles = data.sections_titles.map((t: string, i: number) => `${i + 1}. ${t}`).join('\n')
          addProgressItem(`📋 大纲: ${data.title}`, 'success', titles)
        }
        addProgressItem('大纲规划阶段结束', 'divider')
        break

      case 'section_complete':
        addProgressItem(`✍️ 章节 ${data.section_index} 完成: ${data.title} (${data.content_length} 字)`, 'success')
        break

      case 'check_knowledge_complete':
        if (data.gaps_count > 0) {
          addProgressItem(`🔎 知识空白: ${data.gaps_count} 个 (搜索 ${data.search_count}/${data.max_search_count})`, 'info',
            data.gaps?.join('\n'))
        }
        break

      case 'refine_search_complete':
        addProgressItem(`🌐 第 ${data.round} 轮搜索: 获取 ${data.results_count} 条结果`, 'info')
        break

      case 'enhance_knowledge_complete':
        addProgressItem(`📚 内容增强完成: 累积知识 ${data.knowledge_length} 字`, 'success')
        break

      case 'questioner_complete':
        addProgressItem(data.needs_deepen ? '❓ 内容需要深化' : '✅ 内容深度检查通过',
          data.needs_deepen ? 'info' : 'success')
        break

      case 'coder_complete':
        addProgressItem(`💻 代码示例: ${data.code_blocks_count} 个代码块`, 'success')
        break

      case 'artist_complete':
        addProgressItem(`🎨 配图描述: ${data.images_count} 张`, 'success')
        break

      case 'reviewer_complete':
        addProgressItem(`✅ 质量审核: ${data.score} 分 ${data.passed ? '通过' : '需修订'}`,
          data.passed ? 'success' : 'warning')
        addProgressItem('内容审核阶段结束', 'divider')
        break

      case 'assembler_complete':
        addProgressItem(`📦 文档组装完成: ${data.markdown_length} 字`, 'success')
        addProgressItem('文档组装阶段结束', 'divider')
        break

      default:
        if (data.message) {
          addProgressItem(`📌 ${data.message}`, 'info')
        }
    }
  })

  eventSource.addEventListener('complete', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    addProgressItem('🎉 生成完成！', 'success')
    statusBadge.value = '已完成'
    progressText.value = '生成完成'
    isLoading.value = false

    loadHistory(1)
    eventSource?.close()
    eventSource = null

    setTimeout(() => {
      if (d.id) {
        router.push(`/blog/${d.id}`)
      } else if (d.book_id) {
        router.push(`/book/${d.book_id}`)
      }
    }, 1000)
  })

  eventSource.addEventListener('error', (e: MessageEvent) => {
    if (e.data) {
      const d = JSON.parse(e.data)
      addProgressItem(`❌ 错误: ${d.message}`, 'error')
    }
    statusBadge.value = '错误'
    isLoading.value = false
  })

  eventSource.onerror = () => {
    if (eventSource?.readyState === EventSource.CLOSED) {
      addProgressItem('🔌 连接已关闭')
      isLoading.value = false
    }
  }
}

const getStageIcon = (stage: string) => {
  const icons: Record<string, string> = {
    start: '🚀', research: '🔍', plan: '📋', write: '✍️',
    code: '💻', review: '✅', image: '🎨', assemble: '📦',
    complete: '🎉', error: '❌'
  }
  return icons[stage] || '○'
}

const updateStreamItem = (content: string) => {
  const existing = progressItems.value.find(item => item.type === 'stream')
  if (existing) {
    existing.message = content
  } else {
    addProgressItem(content, 'stream')
  }
}

const addProgressItem = (message: string, type = 'info', detail?: string) => {
  progressItems.value.push({
    time: new Date().toLocaleTimeString(),
    message,
    type,
    ...(detail ? { detail } : {})
  })
}

const toggleTerminal = () => {
  terminalExpanded.value = !terminalExpanded.value
}

const closeProgress = () => {
  showProgress.value = false
  eventSource?.close()
  eventSource = null
}

const stopGeneration = async () => {
  if (currentTaskId.value) {
    try {
      const data = await api.cancelTask(currentTaskId.value)
      if (data.success) {
        addProgressItem('⏹️ 任务已取消', 'error')
      } else {
        addProgressItem(`⚠️ 取消失败: ${data.error}`, 'error')
      }
    } catch (e: any) {
      addProgressItem('⚠️ 取消请求失败', 'error')
    }
  }

  eventSource?.close()
  eventSource = null
  statusBadge.value = '已停止'
  isLoading.value = false
}

// ========== 历史记录 ==========
const loadHistory = async (page: number = 1) => {
  try {
    const data = await api.getHistory({
      page,
      page_size: 12,
      content_type: historyContentType.value === 'all' ? undefined : historyContentType.value
    })

    if (data.success) {
      if (page === 1) {
        historyRecords.value = data.records
      } else {
        historyRecords.value = [...historyRecords.value, ...data.records]
      }
      historyTotal.value = data.total
      historyCurrentPage.value = data.page
      historyTotalPages.value = data.total_pages
    }
  } catch (error) {
    console.error('Load history error:', error)
  }
}

const loadMoreHistory = () => {
  if (historyCurrentPage.value < historyTotalPages.value) {
    loadHistory(historyCurrentPage.value + 1)
  }
}

const switchHistoryTab = (tab: string) => {
  currentHistoryTab.value = tab
  if (tab === 'blogs') {
    loadHistory(1)
  }
}

const filterByContentType = (type: string) => {
  historyContentType.value = type
  loadHistory(1)
}

const loadHistoryDetail = async (historyId: string) => {
  try {
    const data = await api.getHistoryRecord(historyId)
    if (data.success && data.record) {
      const record = data.record

      if (record.content_type === 'xhs') {
        router.push(`/xhs?history_id=${historyId}`)
        return
      }

      router.push(`/blog/${historyId}`)
    }
  } catch (error) {
    console.error('Load history detail error:', error)
  }
}

// ========== 发布 ==========
const doPublish = async () => {
  if (!publishCookie.value.trim() || isPublishing.value) return

  isPublishing.value = true
  publishStatus.value = '发布中...'
  publishStatusType.value = 'info'

  try {
    // Implement publish logic here
    await new Promise(resolve => setTimeout(resolve, 2000))
    publishStatus.value = '发布成功！'
    publishStatusType.value = 'success'
  } catch (error: any) {
    publishStatus.value = `发布失败: ${error.message}`
    publishStatusType.value = 'error'
  } finally {
    isPublishing.value = false
  }
}

// ========== 初始化 ==========
onMounted(async () => {
  // Load app config
  try {
    const data = await api.getFrontendConfig()
    if (data.success && data.config) {
      Object.assign(appConfig, data.config)
    }
  } catch (error) {
    console.error('Load app config error:', error)
  }

  // Load image styles
  try {
    const data = await api.getImageStyles()
    if (data.success && data.styles) {
      imageStyles.value = data.styles
    }
  } catch (error) {
    console.error('Load image styles error:', error)
  }

  // Load history
  loadHistory(1)

  // 键盘支持
  const onKeydown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown') goToSection(currentSection.value + 1)
    if (e.key === 'ArrowUp') goToSection(currentSection.value - 1)
  }
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
})
</script>

<style scoped>
.home-container {
  height: 100vh;
  background: var(--color-bg-base);
  position: relative;
  overflow: hidden;
  transition: var(--transition-colors);
}

/* Background Animation */
.bg-animation {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.bg-animation::before {
  content: '';
  position: absolute;
  width: 200%;
  height: 200%;
  top: -50%;
  left: -50%;
  background: radial-gradient(circle, var(--color-primary-light) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: bg-scroll 60s linear infinite;
}

@keyframes bg-scroll {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

/* ===== Fullpage 滑动系统 ===== */
.fullpage-container {
  position: relative;
  height: calc(100vh - 60px);
  margin-top: 60px;
  overflow: hidden;
}

.fullpage-track {
  transition: transform 0.7s cubic-bezier(0.65, 0, 0.35, 1);
  will-change: transform;
}

.fullpage-section {
  height: calc(100vh - 60px);
  overflow-y: auto;
}

/* 侧边指示器 */
.section-indicators {
  position: fixed;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 50;
}

.section-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.3s;
}

.section-dot.active {
  background: var(--color-primary, #3b82f6);
  transform: scale(1.4);
}

.dark-mode .section-dot {
  background: rgba(255, 255, 255, 0.2);
}

.dark-mode .section-dot.active {
  background: var(--color-primary, #60a5fa);
}

/* 首屏 */
.first-screen {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

/* 第二屏 - 历史记录（保持原布局） */
.history-section {
  position: relative;
  z-index: 1;
  margin-top: 0;
  padding: 1.5rem 0;
  background: linear-gradient(to bottom, transparent, var(--color-muted) 50%, transparent);
}

.history-section.history-visible {
  opacity: 1;
  transform: none;
}

/* 首屏底部备案 */
.first-screen-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

/* 下滑提示 */
.scroll-hint {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  opacity: 0.5;
  animation: scroll-bounce 2s ease-in-out infinite;
  cursor: pointer;
}

.scroll-hint-arrow {
  opacity: 0.6;
}

@keyframes scroll-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(6px); }
}

/* 统一容器宽度 */
.main-content-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
}

.content-container {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.advanced-options-anchor {
  position: relative;
}

.advanced-options-anchor > * {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
}

/* 高级选项展开/收起动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Dark Mode */
.dark-mode {
  background: var(--color-bg-base);
}

/* Mobile */
@media (max-width: 767px) {
  .fullpage-container {
    height: calc(100vh - 56px);
    margin-top: 56px;
  }

  .fullpage-section {
    height: calc(100vh - 56px);
  }

  .content-container {
    padding: 1.5rem 1rem;
  }

  .section-indicators {
    right: 12px;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .content-container {
    padding: 2rem 1.5rem;
  }
}

/* Large Desktop */
@media (min-width: 1440px) {
  .content-container {
    max-width: 1400px;
    padding: 3rem 2rem;
  }
}

/* Reduce motion */
@media (prefers-reduced-motion: reduce) {
  .bg-animation::before {
    animation: none;
  }
  .fullpage-track {
    transition: none;
  }
}
</style>
