<template>
  <div v-if="coverVideo" class="sidebar-card video-card">
    <div class="sidebar-card-header">
      <span class="card-title">$ ffplay cover.mp4</span>
      <span class="video-badge">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        VIDEO
      </span>
    </div>
    <div class="sidebar-card-body video-body">
      <div class="video-container">
        <video
          :src="coverVideo"
          controls
          loop
          muted
          autoplay
          playsinline
          class="cover-video"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
      <div class="video-actions">
        <a :href="coverVideo" download class="video-download-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" x2="12" y1="15" y2="3"></line>
          </svg>
          下载视频
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  coverVideo?: string
}

defineProps<Props>()
</script>

<style scoped>
.sidebar-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--glass-bg);
}

.sidebar-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 12px;
  color: var(--text-muted);
}

.video-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--number);
  background: rgba(245, 158, 11, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.video-body {
  padding: 0 !important;
}

.video-container {
  position: relative;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

.cover-video {
  width: 100%;
  display: block;
  max-height: 200px;
  object-fit: contain;
  transition: opacity 0.2s ease;
}

.cover-video:hover {
  opacity: 0.95;
}

.video-actions {
  padding: 12px;
  display: flex;
  justify-content: center;
  background: var(--surface);
  border-top: 1px solid var(--border);
}

.video-download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 12px;
  text-decoration: none;
  transition: all 0.2s ease;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
}

.video-download-btn:hover {
  background: var(--surface-hover);
  border-color: var(--number);
  color: var(--number);
  transform: translateY(-1px);
}
</style>
