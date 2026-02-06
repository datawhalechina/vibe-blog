<template>
  <div v-if="visible" class="publish-modal" @click.self="$emit('close')">
    <div class="publish-modal-content">
      <div class="publish-modal-header">
        <h2>
          <Rocket :size="18" /> 发布到平台
        </h2>
        <button @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="publish-form">
        <div class="form-item">
          <label>选择平台</label>
          <select v-model="localPlatform">
            <option value="csdn">CSDN</option>
            <option value="zhihu">知乎</option>
            <option value="juejin">掘金</option>
          </select>
        </div>
        <div class="form-item">
          <label>
            Cookie
            <a href="javascript:void(0)" @click="showHelp = !showHelp">如何获取？</a>
          </label>
          <textarea
            v-model="localCookie"
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
          4. 选择对应域名，复制所有 Cookie
        </div>
        <button
          class="publish-submit-btn"
          :disabled="isPublishing || !localCookie.trim()"
          @click="handlePublish"
        >
          <Loader v-if="isPublishing" :size="14" class="spin" />
          <Rocket v-else :size="14" />
          {{ isPublishing ? '发布中...' : '立即发布' }}
        </button>
        <div v-if="status" class="publish-status" :class="statusType">
          {{ status }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Rocket, X, Loader } from 'lucide-vue-next'

interface Props {
  visible: boolean
  platform: string
  cookie: string
  isPublishing: boolean
  status: string
  statusType: string
}

interface Emits {
  (e: 'close'): void
  (e: 'update:platform', value: string): void
  (e: 'update:cookie', value: string): void
  (e: 'publish'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const showHelp = ref(false)

const localPlatform = computed({
  get: () => props.platform,
  set: (value) => emit('update:platform', value)
})

const localCookie = computed({
  get: () => props.cookie,
  set: (value) => emit('update:cookie', value)
})

const handlePublish = () => {
  if (!props.cookie.trim() || props.isPublishing) return
  emit('publish')
}
</script>

<style scoped>
.publish-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  padding: var(--space-lg);
}

.publish-modal-content {
  width: 100%;
  max-width: 600px;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-2xl);
  overflow: hidden;
}

.publish-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
}

.publish-modal-header h2 {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin: 0;
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
}

.publish-modal-header button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-all);
}

.publish-modal-header button:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.publish-form {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-item label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.form-item label a {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-normal);
  color: var(--color-primary);
  text-decoration: none;
}

.form-item label a:hover {
  text-decoration: underline;
}

.form-item select {
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: var(--transition-all);
}

.form-item select:hover {
  border-color: var(--color-border-hover);
}

.form-item select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.form-item textarea {
  min-height: 120px;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  resize: vertical;
  transition: var(--transition-all);
}

.form-item textarea:hover {
  border-color: var(--color-border-hover);
}

.form-item textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.form-item textarea::placeholder {
  color: var(--color-text-tertiary);
}

.cookie-warning {
  padding: var(--space-sm);
  background: var(--color-warning-light);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
}

.cookie-help {
  padding: var(--space-md);
  background: var(--color-info-light);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: var(--line-height-relaxed);
}

.publish-submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: var(--color-primary-gradient);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-inverse);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: var(--transition-all);
  box-shadow: var(--shadow-primary);
  position: relative;
  overflow: hidden;
}

.publish-submit-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.publish-submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-primary);
}

.publish-submit-btn:hover:not(:disabled)::before {
  left: 100%;
}

.publish-submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.publish-submit-btn:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.publish-status {
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  text-align: center;
}

.publish-status.success {
  background: var(--color-success-light);
  border: 1px solid var(--color-success);
  color: var(--color-success);
}

.publish-status.error {
  background: var(--color-error-light);
  border: 1px solid var(--color-error);
  color: var(--color-error);
}

.publish-status.info {
  background: var(--color-info-light);
  border: 1px solid var(--color-info);
  color: var(--color-info);
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .publish-modal {
    padding: var(--space-md);
  }

  .publish-modal-content {
    max-width: 100%;
  }

  .publish-modal-header {
    padding: var(--space-md);
  }

  .publish-modal-header h2 {
    font-size: var(--font-size-lg);
  }

  .publish-form {
    padding: var(--space-md);
    gap: var(--space-md);
  }

  .form-item textarea {
    min-height: 100px;
  }
}
</style>
