<template>
  <div v-if="show" class="progress-container show">
    <div class="progress-header">
      <span class="progress-title">{{ progressTitle }}</span>
      <button class="cancel-btn" @click="$emit('cancel')">取消生成</button>
    </div>

    <div class="main-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }">
          <div class="progress-glow"></div>
        </div>
      </div>
      <span class="progress-percent">{{ progressPercent }}%</span>
    </div>

    <div class="stage-indicators">
      <template v-for="(stage, index) in stages" :key="stage.id">
        <div
          class="stage-item"
          :class="getStageClass(stage.id)"
          :data-stage="stage.id"
          @mouseenter="hoveredStage = stage.id"
          @mouseleave="hoveredStage = null"
        >
          <div class="stage-icon">{{ stage.icon }}</div>
          <div class="stage-name">{{ stage.name }}</div>
          <div class="stage-status">{{ getStageStatus(stage.id) }}</div>
          <div v-if="stage.id === 'images' && imageSubProgress" class="stage-sub-progress">
            ({{ imageSubProgress.current }}/{{ imageSubProgress.total }})
          </div>
          <div v-if="hoveredStage === stage.id && stageDetails[stage.id]" class="stage-detail">
            {{ stageDetails[stage.id] }}
          </div>
        </div>
        <div v-if="index < stages.length - 1" class="stage-arrow">→</div>
      </template>
    </div>

    <div class="progress-info">
      <span class="current-stage">{{ currentStageText }}</span>
      <span class="time-estimate">{{ timeEstimate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Stage, SubProgress } from '../../composables/xhs/useXhsProgress'

interface Props {
  show?: boolean
  progressPercent?: number
  progressTitle?: string
  currentStageText?: string
  timeEstimate?: string
  imageSubProgress?: SubProgress | null
  stages?: Stage[]
  stageStatuses?: Record<string, string>
  stageDetails?: Record<string, string>
  getStageClass?: (stageId: string) => string
  getStageStatus?: (stageId: string) => string
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  progressPercent: 0,
  progressTitle: '生成中...',
  currentStageText: '准备中...',
  timeEstimate: '预计剩余: --',
  stages: () => [],
  stageStatuses: () => ({}),
  stageDetails: () => ({})
})

defineEmits<{
  cancel: []
}>()

const hoveredStage = ref<string | null>(null)
</script>

<style scoped>
.progress-container {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  padding: 24px;
  margin-top: 24px;
  box-shadow: var(--shadow-md);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.progress-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--code-text);
}

.cancel-btn {
  padding: 8px 14px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}

.cancel-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}

.main-progress {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: var(--code-border);
  border-radius: 5px;
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--code-keyword), #7c3aed, var(--code-variable));
  background-size: 200% 100%;
  border-radius: 5px;
  transition: width 0.5s ease;
  position: relative;
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.progress-glow {
  display: none;
}

.progress-percent {
  font-size: 14px;
  font-weight: 700;
  color: var(--code-keyword);
  min-width: 50px;
  text-align: right;
}

/* 阶段指示器 */
.stage-indicators {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stage-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 14px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 10px;
  min-width: 65px;
  transition: all var(--transition-fast);
  position: relative;
  cursor: pointer;
}

.stage-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.stage-item.waiting {
  color: var(--code-text-muted);
}

.stage-item.active {
  background: rgba(139, 92, 246, 0.12);
  border-color: var(--code-keyword);
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.2);
}

.stage-item.active .stage-icon {
  animation: pulse 1s ease infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.stage-item.completed {
  background: rgba(34, 197, 94, 0.12);
  border-color: var(--code-string);
}

.stage-item.completed::after {
  content: '✓';
  position: absolute;
  top: -8px;
  right: -8px;
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, var(--code-string), #16a34a);
  color: white;
  border-radius: 50%;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.4);
}

.stage-icon {
  font-size: 18px;
  margin-bottom: 6px;
}

.stage-name {
  font-size: 10px;
  font-weight: 600;
  color: var(--code-text);
}

.stage-status {
  font-size: 9px;
  color: var(--code-text-muted);
  margin-top: 3px;
}

.stage-item.active .stage-status {
  color: var(--code-keyword);
  font-weight: 500;
}

.stage-item.completed .stage-status {
  color: var(--code-string);
  font-weight: 500;
}

.stage-sub-progress {
  font-size: 9px;
  color: var(--code-keyword);
  font-weight: 700;
  margin-top: 3px;
}

.stage-arrow {
  color: var(--code-text-muted);
  font-size: 12px;
  opacity: 0.5;
}

/* 阶段详情悬浮 */
.stage-detail {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: var(--code-text);
  color: var(--code-bg);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 11px;
  white-space: pre-line;
  min-width: 180px;
  max-width: 280px;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  margin-bottom: 8px;
  line-height: 1.5;
}

.stage-detail::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #333;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--code-border);
}

.current-stage {
  font-size: 12px;
  color: var(--code-text-secondary);
}

.time-estimate {
  font-size: 11px;
  color: var(--code-text-muted);
}
</style>
