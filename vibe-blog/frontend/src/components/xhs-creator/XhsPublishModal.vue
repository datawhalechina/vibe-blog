<template>
  <div v-if="show" class="publish-modal" @click.self="$emit('close')">
    <div class="publish-modal-content">
      <h3>🔐 输入小红书 Cookie</h3>
      <p>在浏览器开发者工具 → Network → 任意请求 → Headers → Cookie，复制粘贴即可：</p>
      <textarea
        :value="cookie"
        @input="$emit('update:cookie', ($event.target as HTMLTextAreaElement).value)"
        placeholder="直接粘贴 Cookie 字符串，如: a1=xxx; webId=yyy; web_session=zzz"
      ></textarea>
      <div class="modal-actions">
        <button class="cancel" @click="$emit('close')">取消</button>
        <button class="confirm" @click="$emit('publish')">确认发布</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  show?: boolean
  cookie?: string
}

defineProps<Props>()

defineEmits<{
  close: []
  'update:cookie': [value: string]
  publish: []
}>()
</script>

<style scoped>
.publish-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.publish-modal-content {
  background: var(--code-bg);
  border-radius: 12px;
  padding: 20px;
  max-width: 480px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  border: 1px solid var(--code-border);
}

.publish-modal-content h3 {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--code-text);
}

.publish-modal-content p {
  color: var(--code-text-secondary);
  font-size: 12px;
  margin-bottom: 10px;
}

.publish-modal-content textarea {
  width: 100%;
  height: 120px;
  padding: 10px;
  border: 1px solid var(--code-border);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  resize: vertical;
  background: var(--code-surface);
  color: var(--code-text);
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  justify-content: flex-end;
}

.modal-actions button {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  transition: all var(--transition-fast);
}

.modal-actions .cancel {
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  color: var(--code-text-secondary);
}

.modal-actions .cancel:hover {
  background: var(--code-surface-hover);
}

.modal-actions .confirm {
  background: var(--code-keyword);
  border: none;
  color: white;
  font-weight: 600;
}

.modal-actions .confirm:hover {
  background: #7c3aed;
}
</style>
