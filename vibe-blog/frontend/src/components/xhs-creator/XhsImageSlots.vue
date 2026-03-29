<template>
  <div v-if="show" class="images-section">
    <h3 style="margin-bottom: 12px">📷 信息图预览</h3>
    <div class="images-grid">
      <div
        v-for="(img, index) in imageSlots"
        :key="index"
        class="image-card"
        :class="{ loading: img.loading }"
        :id="`image-slot-${index}`"
        @mouseenter="handleMouseEnter(index)"
        @mouseleave="handleMouseLeave(index)"
      >
        <template v-if="img.loading">
          <div class="placeholder">
            <div class="mini-spinner"></div>
            <span>{{ img.statusText || `第 ${index + 1} 页` }}</span>
          </div>
        </template>
        <template v-else>
          <img :src="img.url" :alt="`第${index + 1}张`" />
          <div class="caption">第 {{ index + 1 }} 页{{ index === 0 ? ' (封面)' : '' }}</div>
          <!-- 分镜提示浮窗 -->
          <div v-if="img.showTooltip && img.prompt" class="prompt-tooltip">
            <div class="tooltip-header">
              <span>🎨 第 {{ index + 1 }} 页视觉指令</span>
              <button @click.stop="$emit('copy-prompt', index)">复制</button>
            </div>
            <pre>{{ img.prompt }}</pre>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ImageSlot } from '../../composables/xhs/useXhsImages'

interface Props {
  show?: boolean
  imageSlots?: ImageSlot[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'copy-prompt': [index: number]
  'update-tooltip': [index: number, show: boolean]
}>()

const handleMouseEnter = (index: number) => {
  emit('update-tooltip', index, true)
}

const handleMouseLeave = (index: number) => {
  emit('update-tooltip', index, false)
}
</script>

<style scoped>
.images-section {
  margin-bottom: 20px;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.image-card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--code-border);
  background: var(--code-bg);
  position: relative;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.image-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: var(--shadow-lg);
  border-color: var(--code-variable);
}

.image-card img {
  width: 100%;
  aspect-ratio: 3/4;
  object-fit: cover;
  transition: transform var(--transition-normal);
}

.image-card:hover img {
  transform: scale(1.05);
}

.image-card .caption {
  padding: 10px;
  font-size: 11px;
  color: var(--code-text-secondary);
  text-align: center;
  background: linear-gradient(0deg, var(--code-surface) 0%, transparent 100%);
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.image-card.loading {
  background: var(--code-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 3/4;
}

.image-card.loading .placeholder {
  text-align: center;
  color: var(--code-text-muted);
  font-size: 12px;
}

.mini-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--code-border);
  border-top-color: var(--code-keyword);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 图片提示浮窗 */
.prompt-tooltip {
  position: absolute;
  top: 0;
  left: 105%;
  width: 320px;
  max-height: 350px;
  background: var(--code-bg);
  border-radius: 8px;
  border: 1px solid var(--code-border);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  overflow: hidden;
}

.tooltip-header {
  background: var(--code-surface);
  color: var(--code-text);
  padding: 10px 12px;
  font-weight: 500;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--code-border);
}

.tooltip-header button {
  background: var(--code-keyword);
  border: none;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}

.tooltip-header button:hover {
  background: #7c3aed;
}

.prompt-tooltip pre {
  padding: 12px;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 280px;
  overflow-y: auto;
  background: var(--code-bg);
  color: var(--code-text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .prompt-tooltip {
    left: 0;
    width: 100%;
  }
}
</style>
