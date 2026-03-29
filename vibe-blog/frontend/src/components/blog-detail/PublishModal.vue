<template>
  <div v-if="show" class="publish-modal-overlay" @click.self="$emit('close')">
    <div class="publish-modal">
      <div class="publish-modal-header">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" style="display: inline; vertical-align: middle; margin-right: 8px;">
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
            <polyline points="16 6 12 2 8 6"></polyline>
            <line x1="12" x2="12" y1="2" y2="15"></line>
          </svg>
          发布到平台
        </h3>
        <button class="modal-close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="publish-modal-body">
        <div class="form-group">
          <label>选择平台</label>
          <select :value="platform" @change="$emit('update:platform', ($event.target as HTMLSelectElement).value)" class="form-select">
            <option value="csdn">CSDN</option>
            <option value="zhihu">知乎</option>
            <option value="juejin">掘金</option>
          </select>
        </div>

        <div class="form-group">
          <label>
            Cookie
            <a href="javascript:void(0)" class="help-link" @click="$emit('toggleHelp')">如何获取？</a>
          </label>
          <textarea
            :value="cookie"
            @input="$emit('update:cookie', ($event.target as HTMLTextAreaElement).value)"
            class="form-textarea"
            placeholder="直接粘贴浏览器复制的 Cookie，如：name=value; name2=value2; ..."
          ></textarea>
          <div class="cookie-warning">
            ⚠️ <strong>安全提示：</strong>服务端不会存储您的 Cookie，仅用于本次发布。
          </div>
        </div>

        <div v-if="showHelp" class="cookie-help">
          <strong>获取 Cookie 步骤：</strong><br>
          1. 在浏览器登录目标平台（如 CSDN）<br>
          2. 按 F12 打开开发者工具<br>
          3. 切换到 Application → Cookies<br>
          4. 选择对应域名，复制所有 Cookie<br>
          5. 或安装 "EditThisCookie" 扩展一键导出 JSON
        </div>

        <button
          class="publish-submit-btn"
          :disabled="isPublishing"
          @click="$emit('publish')"
        >
          <span v-if="isPublishing" class="download-spinner"></span>
          <svg v-if="!isPublishing" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="margin-right: 6px;">
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
            <polyline points="16 6 12 2 8 6"></polyline>
            <line x1="12" x2="12" y1="2" y2="15"></line>
          </svg>
          {{ isPublishing ? '发布中...' : '立即发布' }}
        </button>

        <div v-if="status.show" class="publish-status" :class="{ success: status.success }">
          {{ status.message }}
          <a v-if="status.url" :href="status.url" target="_blank" class="view-link">查看文章</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface PublishStatus {
  show: boolean
  success: boolean
  message: string
  url: string
}

interface Props {
  show?: boolean
  platform?: string
  cookie?: string
  isPublishing?: boolean
  status?: PublishStatus
  showHelp?: boolean
}

defineProps<Props>()
defineEmits<{
  close: []
  'update:platform': [value: string]
  'update:cookie': [value: string]
  toggleHelp: []
  publish: []
}>()
</script>

<style scoped>
.publish-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.publish-modal {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.publish-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.publish-modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text);
}

.modal-close-btn {
  width: 32px;
  height: 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 20px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close-btn:hover {
  background: var(--surface-hover);
  color: #ef4444;
}

.publish-modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.help-link {
  color: var(--primary);
  margin-left: 8px;
  text-decoration: none;
}

.help-link:hover {
  text-decoration: underline;
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
}

.form-textarea {
  width: 100%;
  height: 120px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  background: var(--surface);
  color: var(--text);
  resize: vertical;
}

.form-textarea::placeholder {
  color: var(--text-muted);
}

.cookie-warning {
  margin-top: 8px;
  padding: 10px 12px;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.cookie-help {
  background: var(--surface);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.publish-submit-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}

.publish-submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.publish-submit-btn:disabled {
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

.publish-status {
  margin-top: 12px;
  padding: 12px;
  background: var(--surface);
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
  color: var(--text-secondary);
}

.publish-status.success {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.view-link {
  color: var(--primary);
  margin-left: 8px;
}
</style>
