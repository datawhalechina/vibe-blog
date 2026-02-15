<template>
  <div
    v-if="visible"
    class="progress-drawer"
    :class="{ expanded: expanded, embedded: embedded }"
  >
    <!-- 最小化状态栏 -->
    <div class="progress-bar-mini" @click="$emit('toggle')">
      <div class="progress-bar-left">
        <span class="progress-indicator" :class="{ active: isLoading }"></span>
        <span class="progress-status">{{ statusBadge }}</span>
        <span class="progress-text">{{ progressText }}</span>
      </div>
      <div class="progress-bar-right">
        <span class="progress-logs">{{ progressItems.length }} logs</span>
        <button
          v-if="isLoading"
          class="progress-stop-btn"
          @click.stop="$emit('stop')"
        >
          <Square :size="10" /> 中断
        </button>
        <button class="progress-toggle-btn" @click.stop="$emit('toggle')">
          <ChevronRight :size="14" :class="{ 'rotate-down': expanded }" />
        </button>
        <button class="progress-close-btn" @click.stop="$emit('close')">
          <X :size="14" />
        </button>
      </div>
    </div>

    <!-- 展开的日志内容 -->
    <div
      v-show="expanded"
      class="progress-content"
      ref="progressContentRef"
    >
      <!-- Tab 栏（embedded 模式下隐藏，右侧 Card 已有报告面板） -->
      <div v-if="!embedded" class="progress-tabs">
        <button
          class="progress-tab"
          :class="{ active: activeTab === 'logs' }"
          @click="activeTab = 'logs'"
        >
          活动日志
        </button>
        <span class="progress-tab-divider">│</span>
        <button
          class="progress-tab"
          :class="{ active: activeTab === 'preview', disabled: !previewContent }"
          :disabled="!previewContent"
          @click="previewContent && (activeTab = 'preview')"
        >
          文章预览
        </button>
      </div>

      <!-- 活动日志 Tab -->
      <div v-show="activeTab === 'logs'" class="progress-logs-container" ref="progressBodyRef" style="contain: content;">
        <!-- DeerFlow ScrollContainer 滚动阴影 -->
        <div class="scroll-shadow scroll-shadow-top"></div>
        <div class="scroll-shadow scroll-shadow-bottom"></div>
        <!-- 任务启动信息 -->
        <div class="progress-task-header">
          <span class="progress-prompt">❯</span>
          <span class="progress-command">generate</span>
          <span class="progress-arg">--type</span>
          <span class="progress-value">{{ articleType }}</span>
          <span class="progress-arg">--length</span>
          <span class="progress-value">{{ targetLength }}</span>
          <span v-if="taskId" class="progress-task-id">{{ taskId }}</span>
        </div>

        <!-- DeerFlow ThoughtBlock：shadcn-vue Collapsible -->
        <Collapsible v-if="thoughtLogs.length > 0" v-model:open="thoughtExpanded" class="mb-4">
          <CollapsibleTrigger as-child>
            <Button
              variant="ghost"
              class="w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200 h-auto"
              :class="isLoading && !outlineData ? 'border-primary/20 bg-primary/5 shadow-sm' : 'border-border bg-card'"
            >
              <div class="flex w-full items-center gap-3">
                <Lightbulb :size="18" class="shrink-0 transition-colors duration-200" :class="isLoading && !outlineData ? 'text-primary' : 'text-muted-foreground'" />
                <span class="font-semibold leading-none transition-colors duration-200" :class="isLoading && !outlineData ? 'text-primary' : 'text-foreground'">深度思考</span>
                <div v-if="isLoading && !outlineData" class="deer-loading-dots" style="transform: scale(0.75)">
                  <div></div><div></div><div></div>
                </div>
                <div class="flex-grow" />
                <ChevronDown v-if="thoughtExpanded" :size="16" class="text-muted-foreground transition-transform duration-200" />
                <ChevronRight v-else :size="16" class="text-muted-foreground transition-transform duration-200" />
              </div>
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent class="mt-3">
            <Card :class="isLoading && !outlineData ? 'border-primary/20 bg-primary/5' : 'border-border'">
              <CardContent class="p-0">
                <div class="flex h-40 w-full overflow-y-auto">
                  <div class="w-full px-4 py-3">
                    <div
                      v-for="(log, i) in thoughtLogs"
                      :key="'thought-' + i"
                      class="text-xs leading-relaxed"
                      :class="i === thoughtLogs.length - 1 && isLoading ? 'text-primary' : 'text-muted-foreground opacity-80'"
                    >{{ log }}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>

        <!-- DeerFlow PlanCard：shadcn-vue Card -->
        <Card v-if="outlineData && waitingForOutline" class="mb-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <CardHeader>
            <CardTitle>
              <span class="search-query-animated">{{ outlineData.title || '深度研究' }}</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul class="my-2 flex list-decimal flex-col gap-4 border-l-2 pl-8">
              <li
                v-for="(title, i) in outlineData.sections_titles"
                :key="i"
                class="text-sm"
              >
                <h4 class="text-sm font-medium">{{ title }}</h4>
              </li>
            </ul>
          </CardContent>
          <CardFooter class="flex justify-end gap-2">
            <Button @click="$emit('confirmOutline', 'accept')">开始写作</Button>
            <Button variant="outline" @click="$emit('confirmOutline', 'edit')">修改大纲</Button>
          </CardFooter>
        </Card>

        <!-- DeerFlow ResearchCard：shadcn-vue Card -->
        <Card v-else-if="outlineData && !waitingForOutline" class="mb-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <CardHeader>
            <CardTitle>
              <span :class="isLoading ? 'search-query-animated' : ''">{{ outlineData.title || '深度研究' }}</span>
            </CardTitle>
          </CardHeader>
          <CardFooter>
            <span class="research-status-text">
              <span :key="researchStatusText" class="rolling-text-inner text-sm text-muted-foreground">{{ researchStatusText }}</span>
            </span>
          </CardFooter>
        </Card>

        <!-- 进度日志（framer-motion 风格入场动画） -->
        <TransitionGroup name="log-item" tag="div" class="progress-log-list">
          <div
            v-for="(item, index) in visibleItems"
            :key="'log-' + index + '-' + item.type + '-' + (item.data?.query || item.message || index)"
          >
            <!-- 搜索骨架屏（搜索中）：shadcn-vue Skeleton -->
            <div v-if="item.type === 'search' && item.data?.searching" class="activity-section">
              <div class="activity-label search-query-animated">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="activity-icon"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <span>搜索&nbsp;</span>
                <span class="activity-query">{{ item.data.query }}</span>
              </div>
              <div class="flex gap-2 mt-2">
                <Skeleton v-for="si in 2" :key="`skeleton-${si}`" class="h-16 w-40 rounded-md" />
              </div>
            </div>

            <!-- 搜索结果卡片（DeerFlow 风格方形卡片） -->
            <div v-else-if="item.type === 'search' && item.data?.results" class="activity-section">
              <div class="activity-label">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="activity-icon"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <span>搜索&nbsp;</span>
                <span class="activity-query">{{ item.data.query }}</span>
              </div>
              <ul class="card-grid">
                <li
                  v-for="(r, ri) in item.data.results.slice(0, 8)"
                  :key="'result-' + ri"
                  class="search-result-card"
                  :style="`animation: card-in 0.15s ease-out both; animation-delay: ${Math.min(ri * 50, 300)}ms`"
                >
                  <a class="search-result-card-inner" :href="r.url" target="_blank" rel="noopener">
                    <img class="card-tile-favicon" :src="`https://www.google.com/s2/favicons?domain=${r.domain}&sz=16`" :alt="r.domain" width="16" height="16" />
                    <span class="search-result-card-title">{{ r.title }}</span>
                  </a>
                </li>
              </ul>
            </div>

            <!-- 爬取完成卡片 -->
            <div v-else-if="item.type === 'crawl' && item.data" class="activity-section">
              <div class="activity-label search-query-animated">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="activity-icon"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
                <span>正在阅读</span>
              </div>
              <ul class="card-grid">
                <li class="card-tile" style="animation: card-in 0.15s ease-out both">
                  <a class="card-tile-inner" :href="item.data.url || '#'" target="_blank" rel="noopener">
                    <img v-if="item.data.url" class="card-tile-favicon" :src="`https://www.google.com/s2/favicons?domain=${new URL(item.data.url).hostname}&sz=16`" width="16" height="16" />
                    <span class="card-tile-title">{{ item.data.title || item.data.url || '未知页面' }}</span>
                  </a>
                </li>
              </ul>
            </div>

            <!-- 普通日志 -->
            <div
              v-else
              class="progress-log-item"
              :class="item.type"
            >
              <span class="progress-log-time">{{ item.time }}</span>
              <span class="progress-log-icon" :class="item.type">
                {{ getLogIcon(item.type) }}
              </span>
              <span class="progress-log-msg" v-html="item.message"></span>
              <div v-if="item.detail" class="progress-log-detail">
                <pre>{{ item.detail }}</pre>
              </div>
            </div>
          </div>
        </TransitionGroup>

        <!-- DeerFlow LoadingAnimation：三点弹跳 -->
        <div v-if="isLoading" class="progress-loading-line">
          <div class="deer-loading-dots">
            <div></div><div></div><div></div>
          </div>
          <span class="progress-loading-text">{{ progressText }}</span>
        </div>
      </div>

      <!-- 文章预览 Tab -->
      <div v-show="activeTab === 'preview'" class="progress-preview-container">
        <div v-if="previewContent" class="progress-preview-content" v-html="previewContent"></div>
        <div v-else class="progress-preview-empty">暂无预览内容</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Square, ChevronRight, ChevronDown, X, Lightbulb } from 'lucide-vue-next'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'

const MAX_VISIBLE_LOGS = 100

interface ProgressItem {
  time: string
  message: string
  type: string
  detail?: string
  data?: any
}

interface OutlineData {
  title: string
  sections_titles: string[]
  sections?: any[]
}

interface Props {
  visible: boolean
  expanded: boolean
  isLoading: boolean
  statusBadge: string
  progressText: string
  progressItems: ProgressItem[]
  articleType: string
  targetLength: string
  taskId: string | null
  outlineData: OutlineData | null
  waitingForOutline: boolean
  previewContent: string
  embedded?: boolean
}

interface Emits {
  (e: 'toggle'): void
  (e: 'close'): void
  (e: 'stop'): void
  (e: 'confirmOutline', action: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const activeTab = ref<'logs' | 'preview'>('logs')
const progressContentRef = ref<HTMLElement | null>(null)
const progressBodyRef = ref<HTMLElement | null>(null)

const visibleItems = computed(() => {
  const items = props.progressItems
  return items.length > MAX_VISIBLE_LOGS
    ? items.slice(items.length - MAX_VISIBLE_LOGS)
    : items
})

// Auto-scroll to bottom when new items are added
watch(
  () => props.progressItems.length,
  async () => {
    await nextTick()
    if (progressBodyRef.value) {
      progressBodyRef.value.scrollTop = progressBodyRef.value.scrollHeight
    }
  }
)

// DeerFlow ThoughtBlock: 从日志中提取思考过程
const thoughtLogs = computed(() => {
  return props.progressItems
    .filter(item => item.type === 'info' || item.type === 'stream' || item.type === 'warning')
    .map(item => item.message)
    .filter(msg => msg && !msg.startsWith('✅'))
})

// DeerFlow ResearchCard: 研究状态文字（RollingText 效果）
const researchStatusText = computed(() => {
  if (!props.outlineData || props.waitingForOutline) return ''
  if (!props.isLoading) return '报告已生成'
  // 根据最新日志判断当前阶段
  const lastItem = props.progressItems[props.progressItems.length - 1]
  if (!lastItem) return '正在研究...'
  if (lastItem.type === 'search' && lastItem.data?.searching) return '正在搜索...'
  if (lastItem.type === 'search' && lastItem.data?.results) return '搜索完成，正在分析...'
  if (lastItem.type === 'crawl') return '正在阅读网页...'
  if (lastItem.message?.includes('写作')) return '正在生成报告...'
  if (lastItem.message?.includes('审阅') || lastItem.message?.includes('review')) return '正在审阅报告...'
  return '正在研究...'
})

// DeerFlow ThoughtBlock: 折叠状态
const thoughtExpanded = ref(false)

const getLogIcon = (type: string) => {
  const icons: Record<string, string> = {
    'info': '○',
    'success': '✓',
    'error': '✗',
    'stream': '◐',
    'warning': '⚠'
  }
  return icons[type] || '○'
}
</script>

<style scoped>
.progress-drawer {
  position: fixed;
  bottom: var(--space-lg);
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 48px);
  max-width: 1200px;
  z-index: var(--z-modal);
  font-family: var(--font-mono);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  transition: var(--transition-all);
}

.progress-drawer.embedded {
  position: relative;
  bottom: auto;
  left: auto;
  transform: none;
  width: 100%;
  max-width: none;
  z-index: auto;
  border: none;
  border-radius: 0;
  box-shadow: none;
  height: 100%;
  display: flex;
  flex-direction: column;
}

@media (min-width: 1440px) {
  .progress-drawer {
    max-width: 1352px;
  }
}

/* 最小化状态栏 */
.progress-bar-mini {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  transition: var(--transition-colors);
  height: 40px;
  min-height: 40px;
  max-height: 40px;
  overflow: hidden;
}

.progress-bar-mini:hover {
  background: var(--color-bg-input);
}

.progress-bar-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.progress-indicator {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-border);
  flex-shrink: 0;
}

.progress-indicator.active {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success-light);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.progress-status {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary);
  padding: 2px var(--space-sm);
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.progress-bar-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.progress-logs {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.progress-stop-btn,
.progress-toggle-btn,
.progress-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.progress-stop-btn:hover {
  background: var(--color-error-light);
  color: var(--color-error);
}

.progress-toggle-btn:hover,
.progress-close-btn:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.rotate-down {
  transform: rotate(90deg);
}

/* 展开的日志内容 */
.progress-content {
  max-height: 440px;
  overflow: hidden;
  border-top: 1px solid var(--color-border);
}

.embedded .progress-content {
  max-height: none;
  flex: 1;
  overflow-y: auto;
}

.embedded .progress-logs-container {
  max-height: none;
  height: auto;
}

/* Tab 栏 */
.progress-tabs {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
}

.progress-tab {
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.progress-tab:hover:not(.disabled) {
  color: var(--color-text-primary);
  background: var(--color-bg-input);
}

.progress-tab.active {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.progress-tab.disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.5;
}

.progress-tab-divider {
  color: var(--color-border);
  font-size: var(--font-size-xs);
  user-select: none;
}

/* ThoughtBlock / PlanCard / ResearchCard 已由 shadcn-vue 组件 + Tailwind 类替代 */

.research-status-text {
  position: relative;
  display: flex;
  align-items: center;
  height: 2em;
  overflow: hidden;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.rolling-text-inner {
  display: block;
  animation: rolling-in 0.3s ease-in-out;
}

@keyframes rolling-in {
  from { opacity: 0; transform: translateY(100%); }
  to { opacity: 1; transform: translateY(0); }
}

/* （旧大纲样式已被 PlanCard / ResearchCard 替代） */

/* 文章预览 */
.progress-preview-container {
  height: 100%;
  max-height: 400px;
  overflow-y: auto;
  padding: var(--space-lg);
  background: var(--color-bg-base);
}

.progress-preview-content {
  font-family: var(--font-sans, sans-serif);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-primary);
}

.progress-preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.progress-logs-container {
  position: relative;
  height: 100%;
  max-height: 400px;
  overflow-y: auto;
  padding: var(--space-md);
  background: var(--color-bg-base);
}

/* 任务启动信息 */
.progress-task-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  margin-bottom: var(--space-md);
  background: var(--color-bg-elevated);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
  flex-wrap: wrap;
}

.progress-prompt {
  color: var(--color-success);
  font-weight: var(--font-weight-bold);
}

.progress-command {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.progress-arg {
  color: var(--color-text-tertiary);
}

.progress-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.progress-task-id {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

/* 进度日志 */
.progress-log-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.progress-log-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-relaxed);
  transition: var(--transition-colors);
}

.progress-log-item:hover {
  background: var(--color-bg-elevated);
}

.progress-log-time {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  flex-shrink: 0;
  min-width: 60px;
}

.progress-log-icon {
  flex-shrink: 0;
  font-weight: var(--font-weight-bold);
}

.progress-log-icon.info {
  color: var(--color-info);
}

.progress-log-icon.success {
  color: var(--color-success);
}

.progress-log-icon.error {
  color: var(--color-error);
}

.progress-log-icon.warning {
  color: var(--color-warning);
}

.progress-log-icon.stream {
  color: var(--color-primary);
}

.progress-log-msg {
  flex: 1;
  color: var(--color-text-primary);
  word-break: break-word;
}

.progress-log-detail {
  margin-top: var(--space-xs);
  padding: var(--space-sm);
  background: var(--color-bg-base);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.progress-log-detail pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 加载动画 */
.progress-loading-line {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* DeerFlow LoadingAnimation：三点弹跳 */
.deer-loading-dots {
  display: flex;
}

.deer-loading-dots > div {
  width: 8px;
  height: 8px;
  margin: 2px 4px;
  border-radius: 50%;
  background-color: #a3a1a1;
  opacity: 1;
  animation: deer-bounce 0.5s infinite alternate;
}

.deer-loading-dots > div:nth-child(2) {
  animation-delay: 0.2s;
}

.deer-loading-dots > div:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes deer-bounce {
  to {
    opacity: 0.1;
    transform: translateY(-8px);
  }
}

.progress-loading-text {
  color: var(--color-text-secondary);
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .progress-drawer {
    bottom: var(--space-md);
    width: calc(100% - 32px);
  }

  .progress-bar-mini {
    padding: var(--space-xs) var(--space-sm);
  }

  .progress-bar-left {
    gap: var(--space-sm);
  }

  .progress-text {
    max-width: 150px;
  }

  .progress-logs {
    display: none;
  }

  .progress-task-header {
    font-size: 10px;
    gap: var(--space-xs);
  }

  .progress-task-id {
    width: 100%;
    margin-left: 0;
    margin-top: var(--space-xs);
  }

  .progress-logs-container {
    padding: var(--space-sm);
  }

  .progress-log-time {
    display: none;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .progress-text {
    max-width: 250px;
  }
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
  background: linear-gradient(to top, transparent, var(--color-bg-base));
  margin-bottom: -40px;
}

.scroll-shadow-bottom {
  bottom: 0;
  background: linear-gradient(to bottom, transparent, var(--color-bg-base));
  margin-top: -40px;
}

/* Scrollbar styling */
.progress-logs-container::-webkit-scrollbar {
  width: 8px;
}

.progress-logs-container::-webkit-scrollbar-track {
  background: var(--color-bg-base);
}

.progress-logs-container::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: var(--radius-full);
}

.progress-logs-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}

/* === DeerFlow 风格活动区块 === */
.activity-section {
  margin-top: var(--space-md);
  padding-left: var(--space-md);
}

.activity-section + .activity-section {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-lg);
  margin-top: var(--space-lg);
}

.activity-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  font-style: italic;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
}

.activity-icon {
  margin-right: var(--space-sm);
  flex-shrink: 0;
}

.activity-query {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 方形卡片网格（对齐 DeerFlow h-40 w-40 flex-wrap gap-4） */
.card-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
  list-style: none;
  padding: 0;
  margin: 0;
  padding-right: var(--space-md);
}

.card-tile {
  width: 160px;
  height: 160px;
}

.card-tile-inner {
  display: flex;
  gap: var(--space-sm);
  width: 100%;
  height: 100%;
  padding: var(--space-sm);
  background: var(--color-muted);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-decoration: none;
  overflow: hidden;
  transition: background 0.15s;
}

.card-tile-inner:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.card-tile-favicon {
  flex-shrink: 0;
  margin-top: 2px;
  border-radius: 2px;
}

.card-tile-title {
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  word-break: break-word;
}

/* 骨架屏已由 shadcn-vue Skeleton 替代 */

@keyframes card-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* framer-motion 风格：TransitionGroup 入场/退场动画 */
.log-item-enter-active {
  transition: opacity 0.2s ease-out, transform 0.2s ease-out;
}

.log-item-leave-active {
  transition: opacity 0.15s ease-in, transform 0.15s ease-in;
}

.log-item-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.log-item-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.log-item-move {
  transition: transform 0.2s ease;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* DeerFlow RainbowText：明暗闪烁（textShine） */
.search-query-animated {
  background: linear-gradient(
    to right,
    rgba(var(--color-text-rgb, 100, 100, 100), 0.3) 15%,
    rgba(var(--color-text-rgb, 100, 100, 100), 0.75) 35%,
    rgba(var(--color-text-rgb, 100, 100, 100), 0.75) 65%,
    rgba(var(--color-text-rgb, 100, 100, 100), 0.3) 85%
  );
  background-size: 500% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: text-shine 2s ease-in-out infinite alternate;
}

@keyframes text-shine {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}

/* DeerFlow 风格：搜索结果方形卡片 */
.search-result-card {
  max-width: 160px;
}

.search-result-card-inner {
  display: flex;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-sm);
  background: var(--color-muted);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: background 0.15s;
}

.search-result-card-inner:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.search-result-card-title {
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  word-break: break-word;
}

/* 保留旧爬取样式兼容 */
.crawl-link {
  color: var(--color-terminal-string, var(--color-success));
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.crawl-link:hover {
  text-decoration: underline;
}

.crawl-size {
  color: var(--color-text-muted, var(--color-border));
  flex-shrink: 0;
}
</style>
