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
      <!-- 日志内容区 -->
      <div class="progress-logs-container" ref="progressBodyRef">
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

        <!-- 进度日志 -->
        <div class="progress-log-list">
          <div
            v-for="(item, index) in progressItems"
            :key="index"
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

          <!-- 加载动画 -->
          <div v-if="isLoading" class="progress-loading-line">
            <span class="progress-spinner"></span>
            <span class="progress-loading-text">{{ progressText }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Square, ChevronRight, X } from 'lucide-vue-next'

interface ProgressItem {
  time: string
  message: string
  type: string
  detail?: string
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
}

interface Emits {
  (e: 'toggle'): void
  (e: 'close'): void
  (e: 'stop'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const progressContentRef = ref<HTMLElement | null>(null)
const progressBodyRef = ref<HTMLElement | null>(null)

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
  max-height: 400px;
  overflow: hidden;
  border-top: 1px solid var(--color-border);
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
</style>
