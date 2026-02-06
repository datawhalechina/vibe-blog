<template>
  <div class="input-card">
    <div class="form-group">
      <label>📌 输入主题</label>
      <textarea
        :value="topic"
        @input="$emit('update:topic', ($event.target as HTMLTextAreaElement).value)"
        class="text-input"
        placeholder="例如：RAG技术入门、Redis缓存原理、Python装饰器详解..."
      ></textarea>
    </div>

    <div class="options-row">
      <div class="option-group">
        <label>📄 页面数量</label>
        <select :value="pageCount" @change="$emit('update:pageCount', ($event.target as HTMLSelectElement).value)">
          <option value="3">3 页</option>
          <option value="4">4 页</option>
          <option value="5">5 页</option>
          <option value="6">6 页</option>
        </select>
      </div>
      <div class="option-group">
        <label>🎨 视觉风格</label>
        <select :value="visualStyle" @change="$emit('update:visualStyle', ($event.target as HTMLSelectElement).value)">
          <option value="hand_drawn">温暖手绘风</option>
          <option value="claymation">黏土动画风</option>
          <option value="ghibli_summer">🌻 宫崎骏的夏天（漫画分镜）</option>
        </select>
      </div>
      <div class="option-group">
        <label>🎬 动画封面</label>
        <select :value="generateVideo" @change="$emit('update:generateVideo', ($event.target as HTMLSelectElement).value)">
          <option value="false">仅静态图</option>
          <option value="true">生成动画</option>
        </select>
      </div>
    </div>

    <button
      class="generate-btn"
      :disabled="isLoading || !topic.trim()"
      @click="$emit('generate')"
    >
      ✨ 开始生成
    </button>

    <div v-if="errorMsg" class="error-msg show">{{ errorMsg }}</div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  topic?: string
  pageCount?: string
  visualStyle?: string
  generateVideo?: string
  isLoading?: boolean
  errorMsg?: string
}

defineProps<Props>()

defineEmits<{
  'update:topic': [value: string]
  'update:pageCount': [value: string]
  'update:visualStyle': [value: string]
  'update:generateVideo': [value: string]
  generate: []
}>()
</script>

<style scoped>
.input-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 20px;
  padding: 28px;
  box-shadow: var(--shadow-lg);
  transition: all var(--transition-normal);
}

.input-card:hover {
  box-shadow: var(--shadow-xl);
}

/* 表单 */
.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  margin-bottom: 10px;
  font-weight: 600;
  color: var(--code-text);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-input {
  width: 100%;
  padding: 16px;
  border: 1px solid var(--code-border);
  border-radius: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  resize: vertical;
  min-height: 100px;
  background: var(--code-surface);
  color: var(--code-text);
  transition: all var(--transition-fast);
}

.text-input:focus {
  outline: none;
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.12);
  background: var(--code-bg);
}

/* 选项行 */
.options-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.option-group {
  flex: 1;
  min-width: 140px;
}

.option-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--code-text-secondary);
  font-weight: 500;
}

.option-group select {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--code-border);
  border-radius: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: var(--code-surface);
  color: var(--code-text);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.option-group select:hover {
  border-color: var(--code-keyword);
}

.option-group select:focus {
  outline: none;
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

/* 生成按钮 */
.generate-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed, var(--code-variable));
  background-size: 200% 200%;
  border: none;
  border-radius: 12px;
  color: white;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.35);
  position: relative;
  overflow: hidden;
}

.generate-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.generate-btn:hover:not(:disabled)::before {
  left: 100%;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.45);
  background-position: 100% 0;
}

.generate-btn:active {
  transform: translateY(0);
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 错误消息 */
.error-msg {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  padding: 12px 16px;
  border-radius: 8px;
  margin-top: 16px;
  font-size: 13px;
}

/* 响应式 */
@media (max-width: 768px) {
  .options-row {
    flex-direction: column;
  }
}
</style>
