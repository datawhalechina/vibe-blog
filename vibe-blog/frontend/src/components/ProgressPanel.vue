<template>
  <div class="progress-panel" :class="{ 'theme-dark': theme === 'dark', 'theme-light': theme === 'light' }" v-if="visible">
    <!-- 计划列表区域 -->
    <div class="plan-section" v-if="planItems.length > 0">
      <div class="plan-list">
        <div
          v-for="(item, index) in planItems"
          :key="index"
          class="plan-item"
          :class="item.status"
        >
          <span class="plan-prefix">-</span>
          <span class="plan-text" :class="{ 'strikethrough': item.status === 'completed' }">
            {{ item.text }}
          </span>
        </div>
      </div>
      
      <!-- 验证方式 -->
      <div class="verify-section" v-if="verifySteps.length > 0">
        <div class="verify-title">验证方式</div>
        <div
          v-for="(step, index) in verifySteps"
          :key="index"
          class="verify-item"
        >
          <span class="verify-number">{{ index + 1 }}.</span>
          <span class="verify-text">{{ step.text }}</span>
          <div v-if="step.subItems" class="verify-sub-list">
            <div v-for="(sub, subIndex) in step.subItems" :key="subIndex" class="verify-sub-item">
              <span class="sub-prefix">-</span>
              <span class="sub-text">{{ sub }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 执行状态区域 -->
    <div class="execution-section">
      <!-- 当前执行状态 -->
      <div class="current-status" v-if="currentTask">
        <span class="status-bullet">●</span>
        <span class="status-text">{{ currentTask.message }}</span>
      </div>

      <!-- 正在执行的任务 -->
      <div class="active-task" v-if="activeTask">
        <div class="task-line">
          <span class="task-star">*</span>
          <span class="task-name">{{ activeTask.name }}</span>
          <span class="task-meta">(ctrl+c to interrupt · {{ formatTime(activeTask.elapsed) }} · {{ activeTask.status }})</span>
        </div>
        <div class="task-next" v-if="activeTask.next">
          <span class="next-prefix">└</span>
          <span class="next-label">Next:</span>
          <span class="next-text">{{ activeTask.next }}</span>
        </div>
      </div>

      <!-- 命令行提示符 -->
      <div class="prompt-line">
        <span class="prompt-symbol">›</span>
        <span class="cursor" v-if="isLoading">▌</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions" v-if="!isLoading && showActions">
      <button class="btn-secondary" @click="$emit('close')">
        关闭
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface PlanItem {
  text: string
  status: 'pending' | 'in_progress' | 'completed'
}

interface VerifyStep {
  text: string
  subItems?: string[]
}

interface CurrentTask {
  message: string
}

interface ActiveTask {
  name: string
  elapsed: number
  status: string
  next?: string
}

interface Props {
  visible?: boolean
  planItems?: PlanItem[]
  verifySteps?: VerifyStep[]
  currentTask?: CurrentTask | null
  activeTask?: ActiveTask | null
  isLoading?: boolean
  showActions?: boolean
  theme?: 'light' | 'dark'
}

const props = withDefaults(defineProps<Props>(), {
  visible: true,
  planItems: () => [],
  verifySteps: () => [],
  currentTask: null,
  activeTask: null,
  isLoading: false,
  showActions: true,
  theme: 'light'
})

const emit = defineEmits<{
  close: []
}>()

const formatTime = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds}s`
  }
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}

let timeInterval: ReturnType<typeof setInterval>

onMounted(() => {
  timeInterval = setInterval(() => {
    // 更新时间显示
  }, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.progress-panel {
  border-radius: 8px;
  overflow: hidden;
  margin: 24px 0;
  font-family: 'JetBrains Mono', 'Menlo', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.6;
  padding: 20px;
}

/* ========== 浅色主题 ========== */
.theme-light {
  background: #fafafa;
  border: 1px solid #e5e5e5;
  color: #1a1a1a;
}

.theme-light .plan-prefix { color: #888; }
.theme-light .plan-text { color: #1a1a1a; }
.theme-light .plan-text.strikethrough { color: #999; }
.theme-light .plan-item.completed .plan-text { color: #999; }
.theme-light .plan-item.in_progress .plan-text { color: #000; font-weight: 500; }

.theme-light .verify-title { color: #1a1a1a; }
.theme-light .verify-number { color: #1a1a1a; }
.theme-light .verify-text { color: #1a1a1a; }
.theme-light .sub-prefix { color: #888; }
.theme-light .sub-text { color: #666; }

.theme-light .status-bullet { color: #3b82f6; }
.theme-light .status-text { color: #1a1a1a; }

.theme-light .task-star { color: #dc2626; }
.theme-light .task-name { color: #dc2626; }
.theme-light .task-meta { color: #888; }
.theme-light .next-prefix { color: #888; }
.theme-light .next-label { color: #888; }
.theme-light .next-text { color: #666; }

.theme-light .prompt-symbol { color: #3b82f6; }
.theme-light .cursor { color: #1a1a1a; }

.theme-light .actions { border-top: 1px solid #e5e5e5; }
.theme-light .btn-secondary {
  border: 1px solid #d4d4d4;
  color: #666;
}
.theme-light .btn-secondary:hover {
  background: #f0f0f0;
  border-color: #bbb;
  color: #1a1a1a;
}

/* ========== 深色主题 ========== */
.theme-dark {
  background: #1a1a2e;
  border: 1px solid #333;
  color: #e0e0e0;
}

.theme-dark .plan-prefix { color: #888; }
.theme-dark .plan-text { color: #e0e0e0; }
.theme-dark .plan-text.strikethrough { color: #666; }
.theme-dark .plan-item.completed .plan-text { color: #666; }
.theme-dark .plan-item.in_progress .plan-text { color: #fff; }

.theme-dark .verify-title { color: #e0e0e0; }
.theme-dark .verify-number { color: #e0e0e0; }
.theme-dark .verify-text { color: #e0e0e0; }
.theme-dark .sub-prefix { color: #888; }
.theme-dark .sub-text { color: #888; }

.theme-dark .status-bullet { color: #3b82f6; }
.theme-dark .status-text { color: #e0e0e0; }

.theme-dark .task-star { color: #f59e0b; }
.theme-dark .task-name { color: #f59e0b; }
.theme-dark .task-meta { color: #666; }
.theme-dark .next-prefix { color: #666; }
.theme-dark .next-label { color: #666; }
.theme-dark .next-text { color: #888; }

.theme-dark .prompt-symbol { color: #3b82f6; }
.theme-dark .cursor { color: #fff; }

.theme-dark .actions { border-top: 1px solid #333; }
.theme-dark .btn-secondary {
  border: 1px solid #444;
  color: #888;
}
.theme-dark .btn-secondary:hover {
  background: #333;
  border-color: #555;
  color: #e0e0e0;
}

/* ========== 通用样式 ========== */
.plan-section {
  margin-bottom: 24px;
}

.plan-list {
  margin-bottom: 16px;
}

.plan-item {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}

.plan-prefix {
  flex-shrink: 0;
}

.plan-text.strikethrough {
  text-decoration: line-through;
}

.verify-section {
  margin-top: 16px;
}

.verify-title {
  margin-bottom: 12px;
}

.verify-item {
  margin-bottom: 8px;
}

.verify-number {
  margin-right: 4px;
}

.verify-sub-list {
  margin-left: 24px;
  margin-top: 4px;
}

.verify-sub-item {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}

.execution-section {
  margin-top: 20px;
}

.current-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 16px;
}

.status-bullet {
  flex-shrink: 0;
}

.active-task {
  margin-bottom: 16px;
}

.task-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-star {
  flex-shrink: 0;
}

.task-meta {
  font-size: 13px;
}

.task-next {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
  margin-top: 4px;
}

.prompt-line {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 16px;
}

.prompt-symbol {
  font-weight: bold;
}

.cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
}

.btn-secondary {
  padding: 8px 16px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
}

@media (max-width: 768px) {
  .progress-panel {
    padding: 16px;
    font-size: 13px;
  }

  .task-line {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-meta {
    margin-left: 16px;
  }
}
</style>
