<template>
  <div v-if="show" class="result-section show">
    <h2 class="result-title">🎉 生成完成</h2>

    <div class="copy-section">
      <h3>📝 推荐标题</h3>
      <div class="titles-list">
        <div
          v-for="(title, i) in result?.titles || []"
          :key="i"
          class="title-item"
          :class="{ primary: i === 0 }"
        >
          {{ i === 0 ? '⭐ ' : '' }}{{ title }}
        </div>
      </div>

      <h3>📄 文案内容</h3>
      <div class="copy-content">{{ result?.copywriting || '' }}</div>

      <h3 style="margin-top: 16px">🏷️ 推荐标签</h3>
      <div class="tags-list">
        <span v-for="tag in result?.tags || []" :key="tag" class="tag">#{{ tag }}</span>
      </div>
    </div>

    <div class="publish-section">
      <h3>🚀 发布到小红书</h3>
      <p style="color: #666; font-size: 14px; margin-bottom: 16px">
        请先在浏览器登录小红书创作者中心，然后使用浏览器扩展导出 Cookie
      </p>
      <div class="publish-buttons">
        <button class="publish-btn outline" @click="$emit('copy-copywriting')">
          📋 复制文案
        </button>
        <button class="publish-btn outline" @click="$emit('download-images')">
          📥 下载图片
        </button>
        <button class="publish-btn primary" @click="$emit('open-publish')">
          🚀 一键发布
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { XhsResult } from '../../composables/xhs/useXhsGenerator'

interface Props {
  show?: boolean
  result?: XhsResult | null
}

defineProps<Props>()

defineEmits<{
  'copy-copywriting': []
  'download-images': []
  'open-publish': []
}>()
</script>

<style scoped>
.result-section {
  margin-top: 28px;
  padding-top: 28px;
  border-top: 2px solid var(--code-border);
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.result-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--code-text);
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 文案区域 */
.copy-section {
  background: var(--glass-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  padding: 20px;
  margin-top: 20px;
  transition: all var(--transition-normal);
}

.copy-section:hover {
  box-shadow: var(--shadow-md);
}

.copy-section h3 {
  font-size: 15px;
  margin-bottom: 14px;
  color: var(--code-text);
  font-weight: 600;
}

.titles-list {
  margin-bottom: 14px;
}

.title-item {
  padding: 10px 14px;
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--code-text-secondary);
  transition: all var(--transition-fast);
  cursor: pointer;
}

.title-item:hover {
  border-color: var(--code-keyword);
  background: rgba(139, 92, 246, 0.05);
}

.title-item.primary {
  background: rgba(139, 92, 246, 0.12);
  border-color: var(--code-keyword);
  color: var(--code-keyword);
  font-weight: 500;
}

.copy-content {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 10px;
  padding: 14px;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  color: var(--code-text-secondary);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.tag {
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.3);
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 11px;
  color: var(--code-keyword);
  transition: all var(--transition-fast);
  cursor: pointer;
}

.tag:hover {
  background: rgba(139, 92, 246, 0.2);
  transform: scale(1.05);
}

/* 发布区域 */
.publish-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--code-border);
}

.publish-section h3 {
  margin-bottom: 10px;
  font-size: 14px;
  color: var(--code-text);
}

.publish-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.publish-btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.publish-btn.outline {
  background: var(--code-bg);
  border: 1px solid var(--code-keyword);
  color: var(--code-keyword);
}

.publish-btn.outline:hover {
  background: rgba(139, 92, 246, 0.1);
}

.publish-btn.primary {
  background: var(--code-keyword);
  border: none;
  color: white;
  font-weight: 600;
}

.publish-btn.primary:hover {
  background: #7c3aed;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}
</style>
