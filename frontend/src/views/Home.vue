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
import { useTaskStream } from '../composables/useTaskStream'
import { useDocumentUpload } from '../composables/useDocumentUpload'
import { useGenerationForm } from '../composables/useGenerationForm'
import { useHomeHistory } from '../composables/useHomeHistory'

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
const imageStyles = ref<Array<{ id: string; name: string; icon: string }>>([
  { id: 'cartoon', name: '默认风格', icon: '🎨' }
])

const {
  uploadedDocuments,
  handleFileUpload,
  removeDocument,
  getReadyDocumentIds,
} = useDocumentUpload({ onError: (message) => alert(message) })

// ========== 生成状态 ==========
const terminalExpanded = ref(true)
const {
  isLoading,
  showProgress,
  progressItems,
  progressText,
  statusBadge,
  currentTaskId,
  previewContent,
  outlineData,
  waitingForOutline,
  connectSSE,
  confirmOutline: handleConfirmOutline,
  stopGeneration,
  closeProgress,
  addProgressItem,
} = useTaskStream()

const {
  topic,
  showAdvancedOptions,
  articleType,
  targetLength,
  audienceAdaptation,
  imageStyle,
  generateCoverVideo,
  videoAspectRatio,
  deepThinking,
  backgroundInvestigation,
  interactive,
  customConfig,
  isEnhancing,
  taskName,
  enhanceTopic: handleEnhanceTopic,
  createTask,
} = useGenerationForm({
  getReadyDocumentIds,
  isGenerating: isLoading,
})

// ========== 历史记录 ==========
const showBlogList = ref(true)
const showCoverPreview = ref(false)
const {
  currentHistoryTab,
  historyContentType,
  historyRecords,
  historyTotal,
  historyCurrentPage,
  historyTotalPages,
  contentTypeFilters,
  loadHistory,
  loadMoreHistory,
  switchHistoryTab,
  filterByContentType,
  loadHistoryDetail,
} = useHomeHistory({ router })

// ========== 发布 ==========
const showPublishModal = ref(false)
const publishPlatform = ref('csdn')
const publishCookie = ref('')
const isPublishing = ref(false)
const publishStatus = ref('')
const publishStatusType = ref('')

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

  progressText.value = `正在创建${taskName.value}生成任务...`

  try {
    const task = await createTask()
    const data = task.response

    if (data.success && data.task_id) {
      currentTaskId.value = data.task_id
      if (task.kind === 'storybook') {
        addProgressItem(`✓ 任务创建成功 (ID: ${data.task_id})`, 'success')
        connectSSE(data.task_id, (result) => {
          loadHistory(1)
          setTimeout(() => {
            if (result.id) {
              router.push(`/blog/${result.id}`)
            } else if (result.book_id) {
              router.push(`/book/${result.book_id}`)
            }
          }, 1000)
        })
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

const toggleTerminal = () => {
  terminalExpanded.value = !terminalExpanded.value
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
  z-index: 2;
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
  cursor: pointer;
}

.scroll-hint-arrow {
  opacity: 0.6;
  animation: scroll-bounce 2s ease-in-out infinite;
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
