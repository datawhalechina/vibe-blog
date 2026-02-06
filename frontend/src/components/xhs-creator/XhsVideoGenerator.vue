<template>
  <div v-if="show" class="video-section">
    <h3 style="margin-bottom: 12px; color: #333">🎬 生成讲解视频</h3>
    <p style="color: #666; font-size: 14px; margin-bottom: 16px">
      将所有图片合成为一个完整的动画讲解视频，适合发布到小红书、抖音等平台
    </p>
    <div class="video-options">
      <select :value="videoModel" @change="$emit('update:videoModel', ($event.target as HTMLSelectElement).value)">
        <option value="sora2">🎬 Sora2 (推荐)</option>
        <option value="veo3">🎥 Veo3</option>
      </select>
      <select :value="videoStyle" @change="$emit('update:videoStyle', ($event.target as HTMLSelectElement).value)">
        <option value="ghibli_summer">🌻 宫崎骏夏日风</option>
        <option value="cartoon">🎨 卡通活泼风</option>
        <option value="scientific">🔬 科普专业风</option>
      </select>
      <select :value="videoDuration" @change="$emit('update:videoDuration', ($event.target as HTMLSelectElement).value)">
        <option value="30">30 秒</option>
        <option value="60">60 秒</option>
        <option value="90">90 秒</option>
        <option value="120">2 分钟</option>
      </select>
      <button class="video-btn" :disabled="isGenerating" @click="$emit('generate')">
        🎬 {{ isGenerating ? '生成中...' : '生成讲解视频' }}
      </button>
    </div>

    <!-- 视频生成进度 -->
    <div v-if="showProgress" class="video-progress-container show">
      <div class="video-progress-bar">
        <div class="video-progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <div class="video-progress-text">{{ progressText }}</div>
    </div>

    <!-- 视频结果展示 -->
    <div v-if="videoUrl" class="video-result-container show">
      <h4 style="margin-bottom: 12px; color: #333">✅ 讲解视频已生成</h4>
      <video :src="videoUrl" controls autoplay loop muted playsinline></video>
      <div class="video-actions">
        <button @click="$emit('download')">📥 下载视频</button>
        <button @click="$emit('copy-url')">📋 复制链接</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  show?: boolean
  videoModel?: string
  videoStyle?: string
  videoDuration?: string
  isGenerating?: boolean
  showProgress?: boolean
  progressPercent?: number
  progressText?: string
  videoUrl?: string
}

defineProps<Props>()

defineEmits<{
  'update:videoModel': [value: string]
  'update:videoStyle': [value: string]
  'update:videoDuration': [value: string]
  generate: []
  download: []
  'copy-url': []
}>()
</script>

<style scoped>
.video-section {
  margin-top: 20px;
  padding: 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
}

.video-options {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.video-options select {
  padding: 8px 12px;
  border: 1px solid var(--code-border);
  border-radius: 6px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  background: var(--code-bg);
  color: var(--code-text);
  cursor: pointer;
}

.video-btn {
  padding: 10px 20px;
  background: var(--code-string);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all 0.2s;
}

.video-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.video-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.video-progress-container {
  margin-top: 12px;
  padding: 12px;
  background: var(--code-bg);
  border-radius: 6px;
  border: 1px solid var(--code-border);
}

.video-progress-bar {
  height: 6px;
  background: var(--code-border);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.video-progress-fill {
  height: 100%;
  background: var(--code-string);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.video-progress-text {
  font-size: 11px;
  color: var(--code-text-muted);
  text-align: center;
}

.video-result-container {
  margin-top: 12px;
}

.video-result-container video {
  width: 100%;
  max-width: 350px;
  border-radius: 8px;
  border: 1px solid var(--code-border);
}

.video-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.video-actions button {
  padding: 8px 16px;
  background: var(--code-bg);
  border: 1px solid var(--code-string);
  border-radius: 6px;
  color: var(--code-string);
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.video-actions button:hover {
  background: rgba(34, 197, 94, 0.1);
}
</style>
