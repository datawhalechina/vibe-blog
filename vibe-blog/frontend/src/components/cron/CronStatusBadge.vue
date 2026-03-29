<template>
  <span class="cron-status-badge" :class="statusClass">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status?: string | null
}>()

const statusClass = computed(() => {
  switch (props.status) {
    case 'ok': return 'badge-success'
    case 'error': return 'badge-error'
    case 'skipped': return 'badge-muted'
    default: return 'badge-muted'
  }
})

const label = computed(() => {
  switch (props.status) {
    case 'ok': return '成功'
    case 'error': return '失败'
    case 'skipped': return '跳过'
    default: return '未执行'
  }
})
</script>

<style scoped>
.cron-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full, 9999px);
  font-size: var(--font-size-xs, 0.75rem);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium, 500);
  line-height: 1.4;
}
.badge-success {
  background: var(--color-success-light);
  color: var(--color-success);
}
.badge-error {
  background: var(--color-error-light);
  color: var(--color-error);
}
.badge-muted {
  background: var(--color-secondary);
  color: var(--color-muted-foreground);
}
</style>
