<template>
  <div class="generate-container">
    <!-- 顶部工具栏 -->
    <div class="generate-toolbar">
      <button class="toolbar-btn back-btn" @click="goBack">← 返回</button>
      <div class="toolbar-status">
        <span class="status-badge" :class="statusBadge">{{ statusBadge || '准备中' }}</span>
        <span class="status-text">{{ progressText }}</span>
      </div>
      <div class="toolbar-actions">
        <ExportMenu
          v-if="previewContent"
          :content="previewContent"
          :filename="outlineTitle"
          :is-downloading="exportComposable.isDownloading.value"
          @export="handleExport"
        />
        <button
          v-if="completedBlogId"
          class="toolbar-btn evaluate-btn"
          :disabled="evaluateLoading"
          @click="handleEvaluate"
        >
          {{ evaluateLoading ? '评估中...' : '📊 质量评估' }}
        </button>
        <button
          v-if="isLoading"
          class="toolbar-btn stop-btn"
          @click="stopGeneration"
        >
          ⏹ 停止
        </button>
      </div>
    </div>

    <!-- 双栏主体 -->
    <div class="generate-main">
      <!-- 左栏：活动日志 -->
      <div class="generate-left">
        <ProgressDrawer
          :visible="true"
          :expanded="true"
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

      <!-- 右栏：文章预览 -->
      <div class="generate-right">
        <div v-if="previewContent" ref="previewRef" class="preview-panel" v-html="renderedHtml"></div>
        <div v-else class="preview-empty">
          <div class="preview-empty-icon">📝</div>
          <div class="preview-empty-text">文章内容将在写作阶段实时显示</div>
        </div>
      </div>
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
  connectSSE,
  confirmOutline,
  stopGeneration,
  addProgressItem,
} = useTaskStream()

const exportComposable = useExport()
const { renderMarkdown } = useMarkdownRenderer()

// 预览渲染
const previewRef = ref<HTMLElement | null>(null)
const renderedHtml = computed(() => renderMarkdown(previewContent.value))
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

// 导出处理
const handleExport = (format: string) => {
  const formatMap: Record<string, 'markdown' | 'html' | 'txt' | 'word'> = {
    markdown: 'markdown',
    html: 'html',
    text: 'txt',
    word: 'word',
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

// 引用悬浮卡片：扫描预览区域的链接
const setupCitationHover = () => {
  if (!previewRef.value || !citations.value.length) return

  const matches = scanCitationLinks(previewRef.value, citations.value)
  matches.forEach(({ element, citation, index }) => {
    element.addEventListener('mouseenter', (e: MouseEvent) => {
      const rect = element.getBoundingClientRect()
      tooltipVisible.value = true
      tooltipCitation.value = citation
      tooltipIndex.value = index
      tooltipPosition.value = { top: rect.bottom + 8, left: rect.left }
    })
    element.addEventListener('mouseleave', () => {
      tooltipVisible.value = false
    })
  })
}

// 监听预览内容变化，重新绑定引用悬浮
watch([renderedHtml, citations], () => {
  nextTick(() => setupCitationHover())
})

// 返回首页
const goBack = () => {
  router.push('/')
}

// 页面加载时连接 SSE
onMounted(() => {
  const taskId = route.params.taskId as string
  if (taskId) {
    currentTaskId.value = taskId
    isLoading.value = true
    addProgressItem(`任务 ${taskId} 已连接`)
    connectSSE(taskId, (data) => {
      // 完成后可跳转详情
      if (data.id) {
        addProgressItem(`文章已生成，可点击查看详情`)
      }
    })
  }
})

onUnmounted(() => {
  tooltipVisible.value = false
})
</script>

<style scoped>
.generate-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg-primary, #0a0a0a);
  color: var(--color-text-primary, #e0e0e0);
}

.generate-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-md, 16px);
  padding: var(--space-sm, 8px) var(--space-lg, 24px);
  border-bottom: 1px solid var(--color-border, #222);
  background: var(--color-bg-elevated, #111);
  flex-shrink: 0;
}

.toolbar-btn {
  padding: var(--space-xs, 4px) var(--space-sm, 8px);
  background: transparent;
  border: 1px solid var(--color-border, #333);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text-secondary, #999);
  font-size: var(--font-size-xs, 12px);
  font-family: var(--font-mono, monospace);
  cursor: pointer;
  transition: all 0.2s;
}

.toolbar-btn:hover {
  color: var(--color-text-primary, #e0e0e0);
  border-color: var(--color-primary, #4ade80);
}

.stop-btn {
  color: #f87171;
  border-color: #f87171;
}

.stop-btn:hover {
  background: rgba(248, 113, 113, 0.1);
}

.evaluate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toolbar-status {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

.status-text {
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #666);
  font-family: var(--font-mono, monospace);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
}

.generate-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.generate-left {
  width: 420px;
  min-width: 320px;
  border-right: 1px solid var(--color-border, #222);
  overflow-y: auto;
}

.generate-right {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg, 24px);
}

.preview-panel {
  max-width: 800px;
  margin: 0 auto;
  line-height: 1.8;
  font-size: 15px;
}

.preview-panel :deep(h1) { font-size: 1.8em; margin: 1em 0 0.5em; color: var(--color-text-primary, #e0e0e0); }
.preview-panel :deep(h2) { font-size: 1.4em; margin: 1.2em 0 0.4em; color: var(--color-text-primary, #e0e0e0); border-bottom: 1px solid var(--color-border, #222); padding-bottom: 0.3em; }
.preview-panel :deep(h3) { font-size: 1.2em; margin: 1em 0 0.3em; color: var(--color-text-secondary, #ccc); }
.preview-panel :deep(p) { margin: 0.6em 0; }
.preview-panel :deep(code) { background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
.preview-panel :deep(pre) { background: rgba(255,255,255,0.04); padding: 16px; border-radius: 8px; overflow-x: auto; margin: 1em 0; }
.preview-panel :deep(a) { color: #4ade80; text-decoration: underline; cursor: pointer; }
.preview-panel :deep(img) { max-width: 100%; border-radius: 8px; margin: 1em 0; }
.preview-panel :deep(blockquote) { border-left: 3px solid #4ade80; padding-left: 16px; margin: 1em 0; color: var(--color-text-muted, #888); }

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-md, 16px);
  color: var(--color-text-muted, #555);
}

.preview-empty-icon {
  font-size: 48px;
  opacity: 0.3;
}

.preview-empty-text {
  font-size: var(--font-size-sm, 14px);
  font-family: var(--font-mono, monospace);
}
</style>
