<template>
  <div class="cron-job-card">
    <!-- Terminal title bar -->
    <div class="card-titlebar">
      <div class="terminal-dots">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
      </div>
      <span class="card-filename">{{ job.name }}</span>
      <CronStatusBadge :status="job.last_status" />
    </div>

    <!-- Card body -->
    <div class="card-body">
      <div class="card-meta">
        <span class="meta-item">
          <Clock :size="12" />
          <span>{{ job.schedule.human_readable || job.schedule.expr || job.schedule.kind }}</span>
        </span>
        <span v-if="job.next_run_at" class="meta-item">
          <CalendarClock :size="12" />
          <span>下次: {{ formatTime(job.next_run_at) }}</span>
        </span>
        <span class="meta-item tag-enabled" :class="{ paused: !job.enabled }">
          {{ job.enabled ? '// enabled' : '// paused' }}
        </span>
      </div>

      <div v-if="job.last_status === 'error' && job.last_error" class="card-error">
        <AlertTriangle :size="12" />
        <span>{{ job.last_error }} (x{{ job.consecutive_errors }})</span>
      </div>

      <!-- Actions -->
      <div class="card-actions">
        <button class="action-btn" title="编辑" @click="$emit('edit', job)">
          <Pencil :size="14" />
        </button>
        <button class="action-btn" :title="job.enabled ? '暂停' : '恢复'" @click="$emit('toggle', job)">
          <Pause v-if="job.enabled" :size="14" />
          <Play v-else :size="14" />
        </button>
        <button class="action-btn" title="执行" @click="$emit('run', job)">
          <Zap :size="14" />
        </button>
        <button v-if="job.last_status === 'error'" class="action-btn" title="重试" @click="$emit('retry', job)">
          <RotateCcw :size="14" />
        </button>
        <button class="action-btn" title="历史" @click="$emit('view-history', job)">
          <History :size="14" />
        </button>
        <button class="action-btn action-danger" title="删除" @click="$emit('delete', job)">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Clock, CalendarClock, AlertTriangle, Pencil,
  Pause, Play, Zap, RotateCcw, History, Trash2
} from 'lucide-vue-next'
import CronStatusBadge from './CronStatusBadge.vue'
import type { CronJobView } from '@/composables/useCronJobs'

defineProps<{ job: CronJobView }>()
defineEmits<{
  edit: [job: CronJobView]
  toggle: [job: CronJobView]
  delete: [job: CronJobView]
  retry: [job: CronJobView]
  run: [job: CronJobView]
  'view-history': [job: CronJobView]
}>()

function formatTime(t?: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.cron-job-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.cron-job-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card-hover);
}

/* Terminal title bar */
.card-titlebar {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 8px);
  padding: 8px 12px;
  background: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-xs);
}
.terminal-dots {
  display: flex;
  gap: 5px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.red { background: var(--color-dot-red); }
.dot.yellow { background: var(--color-dot-yellow); }
.dot.green { background: var(--color-dot-green); }
.card-filename {
  flex: 1;
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  color: var(--color-foreground);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Body */
.card-body {
  padding: 12px;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 8px;
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}
.tag-enabled {
  color: var(--color-success);
}
.tag-enabled.paused {
  color: var(--color-text-tertiary);
}

.card-error {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  margin-bottom: 8px;
  border-radius: var(--radius-sm, 4px);
  background: var(--color-error-light);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
}

/* Actions */
.card-actions {
  display: flex;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.action-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}
.action-danger:hover {
  color: var(--color-error);
  border-color: var(--color-error);
  background: var(--color-error-light);
}
</style>