<template>
  <div class="generate-container">
    <!-- 双栏主体 -->
    <div class="generate-main">
      <!-- 左栏：活动日志 -->
      <div class="generate-left" v-show="!isMobile || mobileTab === 'activity'">
        <ProgressDrawer
          :visible="true"
          :expanded="true"
          :embedded="true"
          :is-loading="isLoading"
          :status-badge="statusBadge"
          :progress-text="progressText"
          :progress-items="progressItems"
          :article-type="'blog'"
          :target-length="''"
          :task-id="currentTaskId"
          :outline-data="outlineData"
          :waiting-for-outline="waitingForOutline"
          :preview-content="previewContent"
          @close="goBack"
          @stop="stopGeneration"
          @toggle="() => {}"
          @confirm-outline="confirmOutline"
        />
      </div>

      <!-- 右栏：研究面板（Card 容器） -->
      <div class="generate-right" v-show="!isMobile || mobileTab === 'preview'">
        <div class="research-card">
          <!-- 右上角工具栏（对齐 DeerFlow 图标按钮） -->
          <div class="card-toolbar">
            <button v-if="isLoading" class="icon-btn stop-btn" title="停止" @click="stopGeneration">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
            </button>
            <template v-if="previewContent && !isLoading">
              <button class="icon-btn" title="编辑" @click="toggleEdit">
                <svg v-if="!isEditing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>
              </button>
              <button class="icon-btn" title="复制" @click="handleCopy">
                <svg v-if="!copied" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
              </button>
              <button v-if="completedBlogId" class="icon-btn" title="质量评估" :disabled="evaluateLoading" @click="handleEvaluate">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
              </button>
              <ExportMenu
                :content="previewContent"
                :filename="outlineTitle"
                :is-downloading="exportComposable.isDownloading.value"
                @export="handleExport"
              />
            </template>
            <button class="icon-btn" title="关闭" @click="goBack">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>

          <!-- 居中标题区（对齐 DeerFlow TabsList 位置） -->
          <div class="card-tabs">
            <div class="card-tabs-list">
              <span class="card-tab active">报告</span>
            </div>
          </div>

          <!-- 报告内容 -->
          <div class="card-tab-content">
            <div class="report-scroll">
              <!-- DeerFlow ScrollContainer 滚动阴影 -->
              <div class="scroll-shadow scroll-shadow-top"></div>
              <div class="scroll-shadow scroll-shadow-bottom"></div>
              <textarea
                v-if="isEditing"
                v-model="editableContent"
                class="edit-textarea"
              ></textarea>
              <div v-else-if="previewContent" id="preview-content" ref="previewRef" class="preview-panel" v-html="renderedHtml"></div>
              <div v-else class="preview-empty">
                <div class="preview-empty-icon">📝</div>
                <div class="preview-empty-text">文章内容将在写作阶段实时显示</div>
              </div>
              <div v-if="isLoading && previewContent" class="loading-dots">
                <span></span><span></span><span></span>
              </div>
              <div v-if="completedBlogId && !isLoading" class="preview-footer">
                <button class="view-article-btn" @click="router.push(`/blog/${completedBlogId}`)">
                  📖 查看文章
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 移动端 Tab 栏 -->
    <div v-if="isMobile" class="mobile-tabs">
      <button
        class="mobile-tab" :class="{ active: mobileTab === 'activity' }"
        @click="mobileTab = 'activity'"
      >活动日志</button>
      <button
        class="mobile-tab" :class="{ active: mobileTab === 'preview' }"
        @click="mobileTab = 'preview'"
        :disabled="!previewContent"
      >文章预览</button>
    </div>

    <!-- 引用悬浮卡片 -->
    <CitationTooltip
      :visible="tooltipVisible"
      :citation="tooltipCitation"
      :index="tooltipIndex"
      :position="tooltipPosition"
    />

    <!-- 质量评估对话框 -->
    <QualityDialog
      :visible="showQualityDialog"
      :evaluation="evaluationData"
      :loading="evaluateLoading"
      @close="showQualityDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStream } from '@/composables/useTaskStream'
import { useExport } from '@/composables/useExport'
import { useMarkdownRenderer } from '@/composables/useMarkdownRenderer'
import { scanCitationLinks } from '@/utils/citationMatcher'
import type { Citation } from '@/utils/citationMatcher'
import * as api from '@/services/api'
import ProgressDrawer from '@/components/home/ProgressDrawer.vue'
import ExportMenu from '@/components/generate/ExportMenu.vue'
import QualityDialog from '@/components/generate/QualityDialog.vue'
import CitationTooltip from '@/components/generate/CitationTooltip.vue'

const route = useRoute()
const router = useRouter()

// 移动端响应式
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)
const mobileTab = ref<'activity' | 'preview'>('activity')
const activeTab = ref<'report' | 'activities'>('activities')
function onResize() { windowWidth.value = window.innerWidth }

// composables
const {
  isLoading,
  progressItems,
  progressText,
  statusBadge,
  currentTaskId,
  previewContent,
  outlineData,
  waitingForOutline,
  citations,
  completedBlogId,
  activeSectionIndex,
  connectSSE,
  confirmOutline,
  stopGeneration,
  addProgressItem,
} = useTaskStream()

const exportComposable = useExport()
const copied = ref(false)
const isEditing = ref(false)
const editableContent = ref('')
const { renderMarkdown } = useMarkdownRenderer()

// 预览渲染：给每个章节注入颜色标记
const previewRef = ref<HTMLElement | null>(null)
const sectionColors = [
  '#3b82f6', // 蓝
  '#10b981', // 绿
  '#f59e0b', // 橙
  '#8b5cf6', // 紫
  '#ec4899', // 粉
  '#06b6d4', // 青
  '#ef4444', // 红
  '#84cc16', // 黄绿
]
const renderedHtml = computed(() => {
  const html = renderMarkdown(previewContent.value)
  if (!html) return ''
  let sectionIdx = 0
  return html.replace(/<h2([\s>])/g, (_match, rest) => {
    const color = sectionColors[sectionIdx % sectionColors.length]
    const isActive = isLoading.value && sectionIdx === activeSectionIndex.value
    const cls = isActive ? 'section-heading section-active' : 'section-heading'
    const tag = `<h2 class="${cls}" style="border-bottom: 3px solid ${color}; padding-bottom: 4px;" data-section="${sectionIdx}"${rest}`
    sectionIdx++
    return tag
  })
})
const outlineTitle = computed(() => outlineData.value?.title || '博客')

// 质量评估
const showQualityDialog = ref(false)
const evaluationData = ref<any>(null)
const evaluateLoading = ref(false)

// 引用悬浮卡片
const tooltipVisible = ref(false)
const tooltipCitation = ref<Citation | null>(null)
const tooltipIndex = ref(0)
const tooltipPosition = ref({ top: 0, left: 0 })

// 编辑模式切换（对齐 DeerFlow research-block.tsx:633）
const toggleEdit = () => {
  if (isEditing.value) {
    // 撤销：恢复原始内容
    editableContent.value = ''
    isEditing.value = false
  } else {
    // 进入编辑：复制当前预览内容到 textarea
    editableContent.value = previewContent.value
    isEditing.value = true
  }
}

// 复制到剪贴板
const handleCopy = async () => {
  if (!previewContent.value) return
  await navigator.clipboard.writeText(previewContent.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}

// 导出处理
const handleExport = (format: string) => {
  const formatMap: Record<string, 'markdown' | 'html' | 'txt' | 'word' | 'pdf' | 'image'> = {
    markdown: 'markdown',
    html: 'html',
    text: 'txt',
    word: 'word',
    pdf: 'pdf',
  }
  exportComposable.exportAs(formatMap[format] || 'markdown', previewContent.value, outlineTitle.value)
}

// 质量评估
const handleEvaluate = async () => {
  if (!completedBlogId.value || evaluateLoading.value) return
  evaluateLoading.value = true
  showQualityDialog.value = true
  evaluationData.value = null

  try {
    const data = await api.evaluateArticle(completedBlogId.value)
    if (data.success && data.evaluation) {
      evaluationData.value = data.evaluation
    }
  } catch (error: any) {
    addProgressItem(`评估失败: ${error.message}`, 'error')
    showQualityDialog.value = false
  } finally {
    evaluateLoading.value = false
  }
}

// 引用悬浮卡片：hover 延迟 200ms 显示，离开 100ms 消失
let hoverShowTimer: ReturnType<typeof setTimeout> | null = null
let hoverHideTimer: ReturnType<typeof setTimeout> | null = null

const showTooltip = (citation: Citation, index: number, rect: DOMRect) => {
  if (hoverHideTimer) { clearTimeout(hoverHideTimer); hoverHideTimer = null }
  hoverShowTimer = setTimeout(() => {
    tooltipVisible.value = true
    tooltipCitation.value = citation
    tooltipIndex.value = index
    tooltipPosition.value = { top: rect.bottom + 8, left: rect.left }
  }, 200)
}

const hideTooltip = () => {
  if (hoverShowTimer) { clearTimeout(hoverShowTimer); hoverShowTimer = null }
  hoverHideTimer = setTimeout(() => {
    tooltipVisible.value = false
  }, 100)
}

const setupCitationHover = () => {
  if (!previewRef.value || !citations.value.length) return

  const matches = scanCitationLinks(previewRef.value, citations.value)
  matches.forEach(({ element, citation, index }) => {
    element.addEventListener('mouseenter', () => {
      const rect = element.getBoundingClientRect()
      showTooltip(citation, index, rect)
    })
    element.addEventListener('mouseleave', () => {
      hideTooltip()
    })
    // 对齐 DeerFlow citation.tsx:80-93 — 点击引用滚动到底部引用列表
    element.addEventListener('click', (e) => {
      const targetId = `ref-${index}`
      const refEl = document.getElementById(targetId)
      if (refEl) {
        e.preventDefault()
        refEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    })
  })
}

// 监听预览内容变化，重新绑定引用悬浮
watch([renderedHtml, citations], () => {
  nextTick(() => setupCitationHover())
})

// 对齐 DeerFlow: 预览内容首次出现时自动切换到 Report Tab
watch(previewContent, (val, oldVal) => {
  if (val && !oldVal) {
    activeTab.value = 'report'
    if (isMobile.value) {
      mobileTab.value = 'preview'
    }
  }
})

// 返回首页
const goBack = () => {
  router.push('/')
}

// 页面加载时连接 SSE
onMounted(() => {
  window.addEventListener('resize', onResize)
  const taskId = route.params.taskId as string
  if (taskId) {
    currentTaskId.value = taskId
    isLoading.value = true
    addProgressItem(`任务 ${taskId} 已连接`)
    connectSSE(taskId, (data) => {
      if (data.id) {
        addProgressItem(`文章已生成，可点击查看详情`)
      }
    })
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  tooltipVisible.value = false
  if (hoverShowTimer) clearTimeout(hoverShowTimer)
  if (hoverHideTimer) clearTimeout(hoverHideTimer)
})
</script>

<style scoped>
/* === 整体布局（对齐 DeerFlow main.tsx） === */
.generate-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg-base);
  color: var(--color-text-primary);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-family: var(--font-mono);
  background: var(--color-primary-light);
  color: var(--color-primary);
}

/* === 双栏布局（对齐 DeerFlow gap-8） === */
.generate-main {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 32px;
  padding: 48px 16px 16px;
}

.generate-left {
  flex-shrink: 0;
  width: 538px;
  overflow-y: auto;
  transition: all 0.3s ease-out;
}

.generate-right {
  flex: 1;
  min-width: 0;
  max-width: 960px;
  padding-bottom: 16px;
  transition: all 0.3s ease-out;
}

/* === Card 容器（对齐 DeerFlow Card） === */
.research-card {
  position: relative;
  height: 100%;
  width: 100%;
  padding-top: 16px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* === 图标按钮工具栏（对齐 DeerFlow absolute right-4） === */
.card-toolbar {
  position: absolute;
  right: 16px;
  top: 0;
  display: flex;
  align-items: center;
  height: 36px;
  z-index: 10;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: #9ca3af;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}

.icon-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-input);
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.icon-btn.stop-btn {
  color: #f87171;
}

.icon-btn.stop-btn:hover {
  background: rgba(248, 113, 113, 0.1);
}

/* === 居中 Tabs（对齐 DeerFlow TabsList） === */
.card-tabs {
  display: flex;
  justify-content: center;
  width: 100%;
  flex-shrink: 0;
}

.card-tabs-list {
  display: inline-flex;
  background: var(--color-bg-input);
  border-radius: var(--radius-md);
  padding: 4px;
}

.card-tab {
  padding: 6px 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.card-tab.active {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
}

.card-tab:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* === Tab 内容区 === */
.card-tab-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.report-scroll {
  position: relative;
  height: 100%;
  overflow-y: auto;
  padding: 0 32px 80px;
}

/* DeerFlow ScrollContainer 滚动阴影 */
.scroll-shadow {
  position: sticky;
  left: 0;
  right: 0;
  height: 40px;
  z-index: 10;
  pointer-events: none;
}

.scroll-shadow-top {
  top: 0;
  background: linear-gradient(to top, transparent, var(--color-bg-elevated));
  margin-bottom: -40px;
}

.scroll-shadow-bottom {
  bottom: 0;
  background: linear-gradient(to bottom, transparent, var(--color-bg-elevated));
  margin-top: -40px;
}

.activities-scroll {
  height: 100%;
  overflow-y: auto;
  padding: 16px 32px;
}

.activities-placeholder {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

/* === 移动端 Tab 栏 === */
.mobile-tabs {
  display: flex;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  flex-shrink: 0;
}

.mobile-tab {
  flex: 1;
  padding: var(--space-sm);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.mobile-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.mobile-tab:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* === 查看文章按钮 === */
.preview-footer {
  display: flex;
  justify-content: center;
  padding: var(--space-lg);
}

.view-article-btn {
  padding: var(--space-sm) var(--space-lg);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.15s;
}

.view-article-btn:hover {
  background: var(--color-primary);
  color: white;
}

/* === 加载三点动画（对齐 DeerFlow LoadingAnimation） === */
.loading-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 48px 16px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: dot-bounce 1.4s ease-in-out infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.16s; }
.loading-dots span:nth-child(3) { animation-delay: 0.32s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

@media (max-width: 767px) {
  .generate-main {
    flex-direction: column;
    gap: 0;
    padding: 0;
  }
  .generate-left,
  .generate-right {
    width: 100%;
    min-width: 0;
    max-width: none;
  }
  .generate-left { flex-shrink: 1; }
  .research-card { border-radius: 0; border-left: none; border-right: none; }
}

/* === 报告面板（对齐 DeerFlow prose 排版） === */
.preview-panel {
  max-width: 800px;
  margin: 16px auto 0;
  line-height: 1.75;
  font-size: 15px;
  color: var(--color-text-primary);
}

.preview-panel :deep(h1) { font-size: 2em; margin: 1.2em 0 0.6em; font-weight: 700; }
.preview-panel :deep(h2) { font-size: 1.5em; margin: 1.4em 0 0.5em; font-weight: 600; padding-bottom: 0.3em; }
.preview-panel :deep(h2.section-heading) { border-bottom-width: 3px; border-bottom-style: solid; transition: all 0.3s ease; }
.preview-panel :deep(h2.section-active) { animation: section-pulse 1.5s ease-in-out infinite; }

@keyframes section-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.preview-panel :deep(h3) { font-size: 1.25em; margin: 1.2em 0 0.4em; font-weight: 600; }
.preview-panel :deep(h4) { font-size: 1em; margin: 1em 0 0.3em; font-weight: 600; }
.preview-panel :deep(p) { margin: 0.8em 0; }
.preview-panel :deep(ul), .preview-panel :deep(ol) { margin: 0.8em 0; padding-left: 1.6em; }
.preview-panel :deep(li) { margin: 0.3em 0; }
.preview-panel :deep(code) { background: var(--color-bg-input); padding: 2px 6px; border-radius: 4px; font-size: 0.875em; font-family: var(--font-mono); }
.preview-panel :deep(pre) { background: var(--color-terminal-bg); color: var(--color-terminal-text); padding: 16px; border-radius: 8px; overflow-x: auto; margin: 1em 0; }
.preview-panel :deep(pre code) { background: none; padding: 0; }
.preview-panel :deep(a) { color: var(--color-primary); text-decoration: underline; text-underline-offset: 2px; }
.preview-panel :deep(img) { max-width: 100%; border-radius: 8px; margin: 1em 0; }
.preview-panel :deep(blockquote) { border-left: 3px solid var(--color-border); padding-left: 16px; margin: 1em 0; color: var(--color-text-muted); font-style: italic; }
.preview-panel :deep(table) { width: 100%; border-collapse: collapse; margin: 1em 0; }
.preview-panel :deep(th), .preview-panel :deep(td) { border: 1px solid var(--color-border); padding: 8px 12px; text-align: left; }
.preview-panel :deep(th) { background: var(--color-bg-input); font-weight: 600; }
.preview-panel :deep(hr) { border: none; border-top: 1px solid var(--color-border); margin: 2em 0; }
.preview-panel :deep(strong) { font-weight: 600; }

/* === 编辑模式 === */
.edit-textarea {
  width: 100%;
  height: 100%;
  max-width: 800px;
  margin: 16px auto 0;
  display: block;
  padding: 20px;
  background: var(--color-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.8;
  resize: none;
  outline: none;
  box-sizing: border-box;
}

.edit-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

/* === 空状态 === */
.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-md);
  color: var(--color-text-muted);
}

.preview-empty-icon {
  font-size: 48px;
  opacity: 0.3;
}

.preview-empty-text {
  font-size: var(--font-size-sm);
}
</style>
