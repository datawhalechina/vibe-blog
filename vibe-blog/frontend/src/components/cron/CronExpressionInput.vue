<template>
  <div class="cron-expr-input">
    <div class="input-row">
      <input
        v-model="text"
        class="expr-field"
        :placeholder="placeholder"
        @keydown.enter="parse"
      />
      <button class="parse-btn" :disabled="!text.trim() || parsing" @click="parse">
        <Loader v-if="parsing" :size="14" class="spin" />
        <span v-else>解析</span>
      </button>
    </div>
    <div v-if="result" class="parse-result" :class="{ 'parse-error': result.type === 'error' }">
      <span v-if="result.type !== 'error'">{{ result.description || result.cron_expression }}</span>
      <span v-else>{{ result.error || '解析失败' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader } from 'lucide-vue-next'

const props = defineProps<{
  modelValue?: any
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: any]
}>()

const text = ref('')
const parsing = ref(false)
const result = ref<any>(null)

async function parse() {
  if (!text.value.trim()) return
  parsing.value = true
  try {
    const res = await fetch('/api/scheduler/parse-schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value }),
    })
    result.value = await res.json()
    emit('update:modelValue', result.value)
  } catch {
    result.value = { type: 'error', error: '解析失败' }
    emit('update:modelValue', null)
  } finally {
    parsing.value = false
  }
}
</script>

<style scoped>
.cron-expr-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 8px);
}
.input-row {
  display: flex;
  gap: var(--space-sm, 8px);
}
.expr-field {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-bg-input);
  color: var(--color-foreground);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  outline: none;
  transition: border-color 0.2s;
}
.expr-field:focus {
  border-color: var(--color-primary);
}
.parse-btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: var(--color-primary);
  color: var(--color-primary-foreground);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.parse-btn:disabled {
  opacity: var(--opacity-disabled, 0.5);
  cursor: not-allowed;
}
.parse-result {
  padding: 6px 10px;
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  background: var(--color-success-light);
  color: var(--color-success);
}
.parse-error {
  background: var(--color-error-light);
  color: var(--color-error);
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
