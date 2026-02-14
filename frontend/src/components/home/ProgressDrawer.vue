<template>
  <div
    v-if="visible"
    class="progress-drawer"
    :class="{ expanded: expanded }"
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
      <!-- Tab 栏 -->
      <div class="progress-tabs">
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

        <!-- 大纲审批卡片（交互式模式） -->
        <div v-if="outlineData && waitingForOutline" class="outline-approval-card">
          <div class="outline-card-header">
            <span class="outline-card-title">📋 {{ outlineData.title }}</span>
            <span class="outline-card-badge">待确认</span>
          </div>
          <div class="outline-card-sections">
            <div
              v-for="(title, i) in outlineData.sections_titles"
              :key="i"
              class="outline-section-item"
            >
              <span class="outline-section-num">{{ i + 1 }}.</span>
              <span class="outline-section-title">{{ title }}</span>
            </div>
          </div>
          <div class="outline-card-actions">
            <span class="outline-prompt">?</span>
            <span class="outline-hint">confirm outline</span>
            <button class="outline-btn outline-btn-accept" @click="$emit('confirmOutline', 'accept')">
              (Y) 开始写作
            </button>
            <button class="outline-btn outline-btn-edit" @click="$emit('confirmOutline', 'edit')">
              (e) 修改
            </button>
          </div>
        </div>

        <!-- 大纲已确认状态 -->
        <div v-else-if="outlineData && !waitingForOutline" class="outline-confirmed-card">
          <span class="outline-confirmed-icon">✓</span>
          <span class="outline-confirmed-text">大纲已确认: {{ outlineData.title }}</span>
        </div>

        <!-- 进度日志 -->
        <div class="progress-log-list">
          <template
            v-for="(item, index) in visibleItems"
            :key="index"
          >
            <!-- 搜索结果卡片 -->
            <div v-if="item.type === 'search' && item.data?.results" class="progress-log-item search">
              <div class="search-results-block">
                <div class="search-query">$ search "{{ item.data.query }}"</div>
                <div class="search-tree">
                  <a
                    v-for="(r, ri) in item.data.results.slice(0, 8)"
                    :key="ri"
                    class="search-card"
                    :href="r.url"
                    target="_blank"
                    rel="noopener"
                    :style="ri < 6 ? `animation: card-in 0.2s ease-out both; animation-delay: ${Math.min(ri * 50, 300)}ms` : 'animation: none'"
                  >
                    <span class="search-card-index">[{{ ri + 1 }}]</span>
                    <img class="search-card-favicon" :src="`https://www.google.com/s2/favicons?domain=${r.domain}&sz=16`" :alt="r.domain" width="16" height="16" />
                    <span class="search-card-domain">{{ r.domain }}</span>
                    <span class="search-card-title">{{ r.title }}</span>
                  </a>
                </div>
              </div>
            </div>

            <!-- 爬取完成卡片 -->
            <div v-else-if="item.type === 'crawl' && item.data" class="progress-log-item crawl">
              <div class="crawl-block">
                <span class="crawl-prefix">$ crawl</span>
                <a class="crawl-link" :href="item.data.url || '#'" target="_blank" rel="noopener">
                  {{ item.data.title || item.data.url || '未知页面' }}
                </a>
                <span v-if="item.data.contentLength" class="crawl-size">→ {{ (item.data.contentLength / 1024).toFixed(1) }}KB ✓</span>
                <span v-else-if="item.data.count" class="crawl-size">→ {{ item.data.count }} 篇 ✓</span>
              </div>
            </div>

            <!-- 普通日志 -->
            <div
              v-else
              v-memo="[item.message, item.type, item.detail]"
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
          </template>

          <!-- 加载动画 -->
          <div v-if="isLoading" class="progress-loading-line">
            <span class="progress-spinner"></span>
            <span class="progress-loading-text">{{ progressText }}</span>
          </div>
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
import { Square, ChevronRight, X } from 'lucide-vue-next'

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

/* 大纲审批卡片 */
.outline-approval-card {
  margin-bottom: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-primary-light);
  border-radius: var(--radius-md);
}

.outline-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.outline-card-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.outline-card-badge {
  font-size: var(--font-size-xs);
  padding: 2px var(--space-sm);
  background: var(--color-warning-light);
  color: var(--color-warning);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.outline-card-sections {
  margin-bottom: var(--space-md);
}

.outline-section-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
  padding: 2px 0;
  font-size: var(--font-size-xs);
}

.outline-section-num {
  color: var(--color-text-muted);
  min-width: 20px;
}

.outline-section-title {
  color: var(--color-terminal-keyword, var(--color-primary));
}

.outline-card-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding-top: var(--space-sm);
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
}

.outline-prompt {
  color: var(--color-warning);
  font-weight: var(--font-weight-bold);
}

.outline-hint {
  color: var(--color-text-muted);
}

.outline-btn {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.outline-btn-accept {
  color: var(--color-success);
  border-color: var(--color-success);
}

.outline-btn-accept:hover {
  background: var(--color-success-light);
}

.outline-btn-edit {
  color: var(--color-text-secondary);
}

.outline-btn-edit:hover {
  background: var(--color-bg-input);
}

/* 大纲已确认 */
.outline-confirmed-card {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-success-light);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
}

.outline-confirmed-icon {
  color: var(--color-success);
  font-weight: var(--font-weight-bold);
}

.outline-confirmed-text {
  color: var(--color-text-secondary);
}

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

.progress-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
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

/* 搜索结果卡片 */
.search-results-block {
  padding: var(--space-xs) 0;
}

.search-query {
  font-size: var(--font-size-xs);
  color: var(--color-terminal-keyword, var(--color-primary));
  margin-bottom: var(--space-xs);
}

.search-tree {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: var(--space-sm);
  border-left: 1px solid var(--color-text-muted, var(--color-border));
}

.search-card {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 3px var(--space-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
  overflow: hidden;
}

.search-card:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.search-card-index {
  color: var(--color-text-muted, var(--color-border));
  flex-shrink: 0;
  width: 24px;
}

.search-card-favicon {
  flex-shrink: 0;
  border-radius: 2px;
}

.search-card-domain {
  color: var(--color-terminal-string, var(--color-success));
  flex-shrink: 0;
  min-width: 80px;
}

.search-card-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 爬取卡片 */
.crawl-block {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-xs);
  padding: var(--space-xs) 0;
}

.crawl-prefix {
  color: var(--color-terminal-keyword, var(--color-primary));
  flex-shrink: 0;
}

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
