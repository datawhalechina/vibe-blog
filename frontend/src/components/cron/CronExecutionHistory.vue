<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="visible" class="drawer-overlay" @click.self="$emit('close')">
        <div class="drawer-panel">
          <div class="drawer-header">
            <div class="terminal-dots">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <span class="drawer-title">$ history {{ jobName }}</span>
            <button class="close-btn" @click="$emit('close')">
              <X :size="16" />
            </button>
          </div>

          <div class="drawer-body">
            <div v-if="loading" class="loading-state">
              <Loader :size="20" class="spin" />
              <span>加载中...</span>
            </div>

            <div v-else-if="records.length === 0" class="empty-state">
              <FileX :size="32" />
              <span>暂无执行记录</span>
            </div>

            <div v-else class="history-list">
              <div v-for="rec in records" :key="rec.id || rec.executed_at" class="history-item">
                <div class="history-row">
                  <CronStatusBadge :status="rec.status" />
                  <span class="history-time">{{ formatTime(rec.executed_at) }}</span>
                  <span v-if="rec.duration_ms" class="history-duration">{{ formatDuration(rec.duration_ms) }}</span>
                </div>
                <div v-if="rec.error" class="history-error">{{ rec.error }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { X, Loader, FileX } from 'lucide-vue-next'
import CronStatusBadge from './CronStatusBadge.vue'

const props = defineProps<{
  visible: boolean
  jobId?: string | null
  jobName?: string
}>()

defineEmits<{ close: [] }>()

const loading = ref(false)
const records = ref<any[]>([])

watch(() => props.visible, async (v) => {
  if (v && props.jobId) {
    loading.value = true
    records.value = []
    try {
      const res = await fetch(`/api/scheduler/tasks/${props.jobId}/history`)
      if (res.ok) {
        const data = await res.json()
        records.value = Array.isArray(data) ? data : data.history || []
      }
    } catch {
      // silent
    } finally {
      loading.value = false
    }
  }
})

function formatTime(t?: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDuration(ms: number) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: var(--z-modal-backdrop, 1300);
  display: flex;
  justify-content: flex-end;
}
.drawer-panel {
  width: 400px;
  max-width: 100vw;
  height: 100vh;
  background: var(--color-background);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}
.drawer-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
  padding: 12px 16px;
  background: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
}
.terminal-dots { display: flex; gap: 5px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.red { background: var(--color-dot-red); }
.dot.yellow { background: var(--color-dot-yellow); }
.dot.green { background: var(--color-dot-green); }
.drawer-title {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.close-btn:hover { background: var(--color-bg-hover); }

.drawer-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm, 8px);
  padding: 40px 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.history-item {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-card);
}
.history-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.history-time {
  flex: 1;
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
}
.history-duration {
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
}
.history-error {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: var(--radius-sm, 4px);
  background: var(--color-error-light);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.3s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}
</style>
