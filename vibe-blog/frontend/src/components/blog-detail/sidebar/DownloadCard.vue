<template>
  <div class="sidebar-card download-card">
    <div class="sidebar-card-header">
      <span class="card-title">$ download --local</span>
      <a href="#" class="man-link" title="帮助">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <path d="M12 17h.01"></path>
        </svg>
        man
      </a>
    </div>
    <div class="sidebar-card-body">
      <button class="download-btn primary" :disabled="isDownloading" @click="$emit('download')">
        <svg v-if="!isDownloading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" x2="12" y1="15" y2="3"></line>
        </svg>
        <span v-if="isDownloading" class="download-spinner"></span>
        {{ isDownloading ? '下载中...' : 'wget blog.zip' }}
      </button>
      <button class="download-btn secondary" @click="$emit('openPublish')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
          <polyline points="16 6 12 2 8 6"></polyline>
          <line x1="12" x2="12" y1="2" y2="15"></line>
        </svg>
        发布到 CSDN
      </button>
      <div class="download-hint">
        <span class="hint-tag">[HINT]</span> 下载完整的博客 ZIP 包（含 Markdown 和图片），或一键发布到 CSDN 平台
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  isDownloading?: boolean
}

defineProps<Props>()
defineEmits<{
  download: []
  openPublish: []
}>()
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

.man-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--string);
  text-decoration: none;
  transition: opacity 0.2s;
}

.man-link:hover {
  opacity: 0.8;
}

.sidebar-card-body {
  padding: 16px;
}

.download-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  margin-bottom: 10px;
  font-family: 'JetBrains Mono', monospace;
}

.download-btn.primary {
  background: linear-gradient(135deg, #cc8b4e, #b87a3d);
  color: #fff;
}

.download-btn.primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(204, 139, 78, 0.4);
}

.download-btn.secondary {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}

.download-btn.secondary:hover {
  background: var(--surface-hover);
  border-color: var(--primary);
}

.download-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.download-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.download-hint {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-top: 4px;
}

.hint-tag {
  color: var(--string);
  font-weight: 600;
}
</style>
