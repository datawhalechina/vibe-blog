<template>
  <div class="generate-container">
    <!-- 双栏主体 -->
    <div class="generate-main">
      <!-- 左栏：活动日志 -->
      <div class="generate-left" v-show="!isMobile || mobileTab === 'activity'" :style="!isMobile ? { width: splitRatio + '%', flexShrink: 0 } : {}">
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

      <!-- 可拖拽分割线 -->
      <div v-if="!isMobile" class="split-handle" @pointerdown="handlePointerDown">
        <div class="split-handle-line"></div>
      </div>

      <!-- 右栏：研究面板（Card 容器） -->
      <div class="generate-right" v-show="!isMobile || mobileTab === 'preview'" :style="!isMobile ? { width: (100 - splitRatio) + '%' } : {}">
        <div class="research-card">
          <!-- 右上角工具栏（DeerFlow lucide + Tooltip） -->
          <div class="card-toolbar">
            <TooltipProvider :delay-duration="200">
              <Tooltip v-if="isLoading">
                <TooltipTrigger as-child>
                  <Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:bg-red-400/10" @click="stopGeneration">
                    <Square :size="16" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>停止</TooltipContent>
              </Tooltip>
              <TokenUsageRing v-if="tokenUsage" :token-usage="tokenUsage" :size="24" />
              <template v-if="previewContent && !isLoading">
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button variant="ghost" size="icon" class="h-8 w-8" @click="toggleEdit">
                      <Undo2 v-if="isEditing" :size="16" />
                      <Pencil v-else :size="16" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{{ isEditing ? '取消编辑' : '编辑' }}</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button variant="ghost" size="icon" class="h-8 w-8" @click="handleCopy">
                      <Check v-if="copied" :size="16" />
                      <Copy v-else :size="16" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{{ copied ? '已复制' : '复制' }}</TooltipContent>
                </Tooltip>
                <Tooltip v-if="completedBlogId">
                  <TooltipTrigger as-child>
                    <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="evaluateLoading" @click="handleEvaluate">
                      <GraduationCap :size="16" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>质量评估</TooltipContent>
                </Tooltip>
                <ExportMenu
                  :content="previewContent"
                  :filename="outlineTitle"
                  :is-downloading="exportComposable.isDownloading.value"
                  @export="handleExport"
                />
              </template>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button variant="ghost" size="icon" class="h-8 w-8" as="a" href="https://github.com/datawhalechina/vibe-blog" target="_blank" rel="noopener">
                    <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true">
                      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                    </svg>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>在 GitHub 上点赞</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button variant="ghost" size="icon" class="h-8 w-8" @click="settingsOpen = true">
                    <SettingsIcon :size="16" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>设置</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button variant="ghost" size="icon" class="h-8 w-8" @click="goBack">
                    <XIcon :size="16" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>关闭</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <!-- 设置弹窗 -->
          <SettingsDialog v-model:open="settingsOpen" />

          <!-- 报告内容 -->
          <div class="card-tab-content">
            <div class="report-scroll">
              <!-- DeerFlow ScrollContainer 滚动阴影 -->
              <div class="scroll-shadow scroll-shadow-top"></div>
              <div class="scroll-shadow scroll-shadow-bottom"></div>
              <div v-if="isEditing" ref="editAreaRef" class="edit-area">
                <div
                  v-if="showSelectionToolbar"
                  class="selection-toolbar"
                  :style="{
                    top: `${selectionToolbarPosition.top}px`,
                    left: `${selectionToolbarPosition.left}px`,
                  }"
                  @mousedown.prevent
                >
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="加粗" @click="applyMarkdownFormat('bold')">
                    <Bold :size="15" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="斜体" @click="applyMarkdownFormat('italic')">
                    <Italic :size="15" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="行内代码" @click="applyMarkdownFormat('code')">
                    <Code2 :size="15" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="标题" @click="applyMarkdownFormat('heading')">
                    <Heading2 :size="15" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="引用" @click="applyMarkdownFormat('quote')">
                    <Quote :size="15" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="无序列表" @click="applyMarkdownFormat('list')">
                    <List :size="15" />
                  </Button>
                  <div class="selection-toolbar-divider"></div>
                  <Button variant="ghost" size="icon" class="h-8 w-8" title="润色" @click="openPolishDialog">
                    <Sparkles :size="15" />
                  </Button>
                </div>
                <textarea
                  ref="editTextareaRef"
                  v-model="editableContent"
                  class="edit-textarea"
                  @mouseup="handleTextSelection"
                  @keyup="handleTextSelection"
                  @scroll="handleEditScroll"
                  @input="handleEditInput"
                ></textarea>
              </div>
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

    <Dialog :open="showPolishDialog" @update:open="(v: boolean) => { if (!v) closePolishDialog() }">
      <DialogContent class="max-w-lg font-mono">
        <DialogHeader>
          <DialogTitle>润色</DialogTitle>
          <DialogDescription>先生成润色结果，确认后再替换原文。</DialogDescription>
        </DialogHeader>

        <div class="polish-dialog-body">
          <div class="polish-panel">
            <div class="polish-panel-label">原文</div>
            <div class="polish-selected-text">{{ selectedTextPreview }}</div>
          </div>
          <Input
            v-model="polishInstruction"
            placeholder="输入润色目标，例如：更专业、更简洁、更口语化"
            @keydown.enter="handlePolish"
          />
          <div v-if="polishedTextPreview" class="polish-panel">
            <div class="polish-panel-label">润色结果</div>
            <div class="polish-selected-text polish-result-text">{{ polishedTextPreview }}</div>
          </div>
          <div class="polish-dialog-actions">
            <Button variant="outline" @click="closePolishDialog">取消</Button>
            <Button v-if="polishedTextPreview" variant="outline" :disabled="polishLoading || !canPolish" @click="handlePolish">
              <Loader2 v-if="polishLoading" class="animate-spin" />
              <span>{{ polishLoading ? '润色中...' : '重新润色' }}</span>
            </Button>
            <Button v-if="polishedTextPreview" :disabled="polishLoading" @click="applyPolishedText">
              确认替换
            </Button>
            <Button v-else :disabled="polishLoading || !canPolish" @click="handlePolish">
              <Loader2 v-if="polishLoading" class="animate-spin" />
              <span>{{ polishLoading ? '润色中...' : '开始润色' }}</span>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStream } from '@/composables/useTaskStream'
import { useExport } from '@/composables/useExport'
import { useMarkdownRenderer } from '@/composables/useMarkdownRenderer'
import { useTypingAnimation } from '@/composables/useTypingAnimation'
import { useResizableSplit } from '@/composables/useResizableSplit'
import { scanCitationLinks } from '@/utils/citationMatcher'
import type { Citation } from '@/utils/citationMatcher'
import {
  Square,
  Pencil,
  Undo2,
  Copy,
  Check,
  GraduationCap,
  Settings as SettingsIcon,
  X as XIcon,
  Loader2,
  Bold,
  Italic,
  Code2,
  Heading2,
  Quote,
  List,
  Sparkles,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import * as api from '@/services/api'
import ProgressDrawer from '@/components/home/ProgressDrawer.vue'
import TokenUsageRing from '@/components/home/TokenUsageRing.vue'
import ExportMenu from '@/components/generate/ExportMenu.vue'
import QualityDialog from '@/components/generate/QualityDialog.vue'
import CitationTooltip from '@/components/generate/CitationTooltip.vue'
import SettingsDialog from '@/components/generate/SettingsDialog.vue'

const route = useRoute()
const router = useRouter()

// 移动端响应式
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)
const mobileTab = ref<'activity' | 'preview'>('activity')
const settingsOpen = ref(false)
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
  tokenUsage,
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
const editAreaRef = ref<HTMLElement | null>(null)
const editTextareaRef = ref<HTMLTextAreaElement | null>(null)
const { renderMarkdown } = useMarkdownRenderer()

// 打字动画：流式文本逐字显示
const { displayedContent: typedPreview } = useTypingAnimation({
  content: previewContent,
  enabled: isLoading,
  speed: 80,
})

// 可拖拽分割线
const { splitRatio, handlePointerDown } = useResizableSplit({
  defaultRatio: 40,
  minRatio: 25,
  maxRatio: 65,
  storageKey: 'vibe-blog-generate-split',
})

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
  const html = renderMarkdown(typedPreview.value)
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
const showPolishDialog = ref(false)
const showSelectionToolbar = ref(false)
const polishInstruction = ref('')
const polishLoading = ref(false)
const polishedText = ref('')
const selectedText = ref('')
const selectionRange = ref({ start: 0, end: 0 })
const selectionToolbarPosition = ref({ top: 0, left: 0 })
const selectedTextPreview = computed(() => selectedText.value.trim())
const polishedTextPreview = computed(() => polishedText.value.trim())
const canPolish = computed(() => selectedTextPreview.value.length > 0)

// 编辑模式切换（对齐 DeerFlow research-block.tsx:633）
const toggleEdit = () => {
  if (isEditing.value) {
    // 撤销：恢复原始内容
    resetSelectionState()
    editableContent.value = ''
    isEditing.value = false
  } else {
    // 进入编辑：复制当前预览内容到 textarea
    editableContent.value = previewContent.value
    isEditing.value = true
  }
}

const resetSelectionState = () => {
  showPolishDialog.value = false
  showSelectionToolbar.value = false
  polishLoading.value = false
  polishedText.value = ''
  polishInstruction.value = ''
  selectedText.value = ''
  selectionRange.value = { start: 0, end: 0 }
}

const closePolishDialog = () => {
  resetSelectionState()
}

const updateSelectionToolbarPosition = (start: number, end: number) => {
  const textarea = editTextareaRef.value
  const editArea = editAreaRef.value
  if (!textarea || !editArea) return

  const textareaRect = textarea.getBoundingClientRect()
  const editAreaRect = editArea.getBoundingClientRect()
  const mirror = document.createElement('div')
  const mirrorStyle = window.getComputedStyle(textarea)

  const styleKeys = [
    'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
    'fontFamily', 'lineHeight', 'letterSpacing', 'textAlign', 'textTransform',
    'textIndent', 'textDecoration', 'tabSize'
  ] as const

  mirror.style.position = 'fixed'
  mirror.style.top = `${textareaRect.top}px`
  mirror.style.left = `${textareaRect.left}px`
  mirror.style.whiteSpace = 'pre-wrap'
  mirror.style.wordBreak = 'break-word'
  mirror.style.pointerEvents = 'none'
  mirror.style.visibility = 'hidden'

  styleKeys.forEach((key) => {
    mirror.style[key] = mirrorStyle[key]
  })

  mirror.textContent = editableContent.value.slice(0, start)

  const selectedSpan = document.createElement('span')
  selectedSpan.textContent = editableContent.value.slice(start, end) || ' '
  mirror.appendChild(selectedSpan)

  document.body.appendChild(mirror)
  mirror.scrollTop = textarea.scrollTop
  mirror.scrollLeft = textarea.scrollLeft

  const selectedRect = selectedSpan.getBoundingClientRect()
  document.body.removeChild(mirror)

  const rawTop = selectedRect.top - editAreaRect.top - 12
  const rawLeft = selectedRect.left - editAreaRect.left + (selectedRect.width / 2)
  const clampedLeft = Math.min(Math.max(rawLeft, 72), Math.max(editAreaRect.width - 72, 72))

  selectionToolbarPosition.value = {
    top: Math.max(rawTop, 8),
    left: clampedLeft,
  }
}

const handleTextSelection = async () => {
  const textarea = editTextareaRef.value
  if (!textarea) return

  const start = textarea.selectionStart ?? 0
  const end = textarea.selectionEnd ?? 0
  if (end <= start) {
    resetSelectionState()
    return
  }

  const rawSelectedText = editableContent.value.slice(start, end)
  if (!rawSelectedText.trim()) {
    resetSelectionState()
    return
  }

  selectionRange.value = { start, end }
  selectedText.value = rawSelectedText
  polishedText.value = ''
  showPolishDialog.value = false
  await nextTick()
  updateSelectionToolbarPosition(start, end)
  showSelectionToolbar.value = true
}

const updateSelectionAfterEdit = async (start: number, end: number) => {
  await nextTick()
  const textarea = editTextareaRef.value
  if (!textarea) return
  textarea.focus()
  textarea.setSelectionRange(start, end)
  selectionRange.value = { start, end }
  selectedText.value = editableContent.value.slice(start, end)
  updateSelectionToolbarPosition(start, end)
  showSelectionToolbar.value = true
}

const applyWrappedFormat = async (prefix: string, suffix: string = prefix) => {
  const { start, end } = selectionRange.value
  if (end <= start) return

  const selection = editableContent.value.slice(start, end)
  editableContent.value = `${editableContent.value.slice(0, start)}${prefix}${selection}${suffix}${editableContent.value.slice(end)}`
  previewContent.value = editableContent.value
  await updateSelectionAfterEdit(start + prefix.length, end + prefix.length)
}

const applyLinePrefixFormat = async (prefix: string) => {
  const { start, end } = selectionRange.value
  if (end <= start) return

  const lineStart = editableContent.value.lastIndexOf('\n', start - 1) + 1
  const selectedBlock = editableContent.value.slice(lineStart, end)
  const formattedBlock = selectedBlock
    .split('\n')
    .map(line => `${prefix}${line}`)
    .join('\n')

  editableContent.value = `${editableContent.value.slice(0, lineStart)}${formattedBlock}${editableContent.value.slice(end)}`
  previewContent.value = editableContent.value
  await updateSelectionAfterEdit(lineStart, lineStart + formattedBlock.length)
}

const applyMarkdownFormat = async (type: 'bold' | 'italic' | 'code' | 'heading' | 'quote' | 'list') => {
  if (!canPolish.value) return

  if (type === 'bold') {
    await applyWrappedFormat('**')
    return
  }
  if (type === 'italic') {
    await applyWrappedFormat('*')
    return
  }
  if (type === 'code') {
    await applyWrappedFormat('`')
    return
  }
  if (type === 'heading') {
    await applyLinePrefixFormat('## ')
    return
  }
  if (type === 'quote') {
    await applyLinePrefixFormat('> ')
    return
  }
  await applyLinePrefixFormat('- ')
}

const openPolishDialog = () => {
  if (!canPolish.value) return
  polishedText.value = ''
  showSelectionToolbar.value = false
  showPolishDialog.value = true
}

const handleEditScroll = () => {
  showSelectionToolbar.value = false
  if (showPolishDialog.value) {
    closePolishDialog()
  }
}

const handleEditInput = () => {
  previewContent.value = editableContent.value
  showSelectionToolbar.value = false
}

const handlePolish = async () => {
  if (!canPolish.value || polishLoading.value) return

  polishLoading.value = true
  try {
    const result = await api.polishSelectedText(selectedTextPreview.value, polishInstruction.value.trim())
    if (!result.success || !result.polished_text) {
      throw new Error(result.error || '润色失败')
    }

    polishedText.value = result.polished_text
    addProgressItem('润色结果已生成，可确认替换', 'success')
  } catch (error: any) {
    addProgressItem(`润色失败: ${error.message}`, 'error')
  } finally {
    polishLoading.value = false
  }
}

const applyPolishedText = async () => {
  if (!polishedTextPreview.value) return

  const { start, end } = selectionRange.value
  const nextText = polishedTextPreview.value
  editableContent.value = `${editableContent.value.slice(0, start)}${nextText}${editableContent.value.slice(end)}`
  previewContent.value = editableContent.value

  resetSelectionState()

  await nextTick()
  const textarea = editTextareaRef.value
  if (textarea) {
    const cursor = start + nextText.length
    textarea.focus()
    textarea.setSelectionRange(cursor, cursor)
  }
  addProgressItem('选中文本已润色并替换', 'success')
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

// 对齐 DeerFlow: 预览内容首次出现时自动切换到移动端预览 Tab
watch(previewContent, (val, oldVal) => {
  if (val && !oldVal) {
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
  resetSelectionState()
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
  background: linear-gradient(135deg, var(--color-bg-base) 0%, var(--color-muted) 50%, var(--color-bg-base) 100%);
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
  padding: 48px 16px 16px;
}

.generate-left {
  flex: none;
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

/* === 可拖拽分割线 === */
.split-handle {
  flex-shrink: 0;
  width: 8px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  touch-action: none;
}
.split-handle-line {
  width: 2px;
  height: 40px;
  border-radius: 1px;
  background: var(--color-border);
  transition: background 0.2s, height 0.2s;
}
.split-handle:hover .split-handle-line {
  background: var(--color-primary);
  height: 60px;
}

/* === Card 容器（对齐 DeerFlow Card） === */
.research-card {
  position: relative;
  height: 100%;
  width: 100%;
  padding-top: 16px;
  background: var(--glass-bg, var(--color-bg-elevated));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(12px);
}

/* === 图标按钮工具栏（对齐 DeerFlow absolute right-4） === */
.card-toolbar {
  position: absolute;
  right: 16px;
  top: 8px;
  display: flex;
  align-items: center;
  height: 36px;
  z-index: 10;
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
.preview-panel :deep(code) { background: var(--color-bg-input); padding: 2px 6px; border-radius: 4px; font-size: 0.875em; font-family: var(--font-mono); color: var(--color-syntax-variable, #ec4899); }
.preview-panel :deep(pre) { background: var(--color-terminal-bg); color: var(--color-terminal-text); padding: 16px; border-radius: 8px; overflow-x: auto; margin: 1em 0; border: 1px solid var(--color-border); }
.preview-panel :deep(pre code) { background: none; padding: 0; color: inherit; }
.preview-panel :deep(a) { color: var(--color-syntax-function, #3b82f6); text-decoration: none; }
.preview-panel :deep(a:hover) { text-decoration: underline; }
.preview-panel :deep(img) { max-width: 100%; border-radius: 8px; margin: 1em 0; }
.preview-panel :deep(blockquote) { border-left: 3px solid var(--color-border); padding-left: 16px; margin: 1em 0; color: var(--color-text-muted); font-style: italic; }
.preview-panel :deep(table) { width: 100%; border-collapse: collapse; margin: 1em 0; background: var(--color-bg-input); border-radius: 8px; overflow: hidden; border: 1px solid var(--color-border); }
.preview-panel :deep(th), .preview-panel :deep(td) { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--color-border); }
.preview-panel :deep(th) { background: var(--color-bg-base); font-weight: 600; color: var(--color-text-primary); }
.preview-panel :deep(tr:last-child td) { border-bottom: none; }
.preview-panel :deep(tr:hover td) { background: var(--color-bg-base); }
.preview-panel :deep(hr) { border: none; border-top: 1px solid var(--color-border); margin: 2em 0; }
.preview-panel :deep(strong) { font-weight: 600; }

/* === 编辑模式 === */
.edit-textarea {
  width: 100%;
  height: 100%;
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

.edit-area {
  position: relative;
  max-width: 800px;
  height: 100%;
  margin: 16px auto 0;
}

.selection-toolbar {
  position: absolute;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--color-bg-elevated) 88%, white 12%);
  box-shadow: var(--shadow-md, 0 10px 30px rgba(15, 23, 42, 0.12));
  backdrop-filter: blur(12px);
  transform: translate(-50%, calc(-100% - 8px));
}

.selection-toolbar-divider {
  width: 1px;
  height: 20px;
  margin: 0 4px;
  background: var(--color-border);
}

.edit-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-light);
}

.polish-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.polish-selected-text {
  max-height: 180px;
  overflow-y: auto;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-base);
  color: var(--color-text-muted);
  line-height: 1.7;
  font-size: 13px;
  white-space: pre-wrap;
}

.polish-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.polish-panel-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.polish-result-text {
  color: var(--color-text-primary);
  background: color-mix(in srgb, var(--color-primary-light) 30%, var(--color-bg-base) 70%);
}

.polish-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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
