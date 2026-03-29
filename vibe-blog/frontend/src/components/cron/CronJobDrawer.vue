<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="visible" class="drawer-overlay" @click.self="$emit('close')">
        <div class="drawer-panel">
          <!-- Header -->
          <div class="drawer-header">
            <div class="terminal-dots">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <span class="drawer-title">{{ isEdit ? '$ edit-task' : '$ new-task' }}</span>
            <button class="close-btn" @click="$emit('close')">
              <X :size="16" />
            </button>
          </div>

          <!-- Form -->
          <div class="drawer-body">
            <label class="form-label">// 任务名称</label>
            <input v-model="form.name" class="form-input" placeholder="e.g. daily-tech-blog" />

            <label class="form-label">// 博客主题</label>
            <input v-model="form.topic" class="form-input" placeholder="e.g. Vue 3 最佳实践" />

            <label class="form-label">// 调度时间</label>
            <CronExpressionInput
              v-model="parsedSchedule"
              placeholder="每天上午9点 / 0 9 * * *"
            />

            <div class="form-row-switch">
              <label class="form-label" style="margin-bottom:0">// 启用</label>
              <button
                class="toggle-switch"
                :class="{ active: form.enabled }"
                @click="form.enabled = !form.enabled"
              >
                <span class="toggle-knob"></span>
              </button>
            </div>
            <!-- Edit mode info -->
            <div v-if="isEdit && job" class="edit-info">
              <div class="info-row">
                <span class="info-label">下次执行</span>
                <span class="info-value">{{ formatTime(job.next_run_at) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">上次执行</span>
                <span class="info-value">{{ formatTime(job.last_run_at) }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">上次状态</span>
                <CronStatusBadge :status="job.last_status" />
              </div>
              <div v-if="job.last_error" class="info-row">
                <span class="info-label">错误</span>
                <span class="info-value error-text">{{ job.last_error }}</span>
              </div>
            </div>

            <!-- Footer buttons -->
            <div class="drawer-footer">
              <button class="btn-save" :disabled="!canSave" @click="handleSave">
                $ save
              </button>
              <button v-if="isEdit" class="btn-delete" @click="$emit('delete', job)">
                $ rm -f
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { X } from 'lucide-vue-next'
import CronExpressionInput from './CronExpressionInput.vue'
import CronStatusBadge from './CronStatusBadge.vue'
import type { CronJobView } from '@/composables/useCronJobs'

const props = defineProps<{
  visible: boolean
  job?: CronJobView | null
}>()

const emit = defineEmits<{
  close: []
  save: [payload: Record<string, any>]
  delete: [job: CronJobView | null | undefined]
}>()

const isEdit = computed(() => !!props.job)

const form = reactive({
  name: '',
  topic: '',
  enabled: true,
})
const parsedSchedule = ref<any>(null)

const canSave = computed(() =>
  form.name.trim() && form.topic.trim() && parsedSchedule.value && parsedSchedule.value.type !== 'error'
)

watch(() => props.visible, (v) => {
  if (v && props.job) {
    form.name = props.job.name
    form.topic = props.job.generation?.topic || ''
    form.enabled = props.job.enabled
  } else if (v) {
    form.name = ''
    form.topic = ''
    form.enabled = true
    parsedSchedule.value = null
  }
})

function handleSave() {
  if (!canSave.value) return
  const trigger = parsedSchedule.value.type === 'cron'
    ? { type: 'cron', cron_expression: parsedSchedule.value.cron_expression }
    : { type: 'once', scheduled_at: parsedSchedule.value.scheduled_at }
  emit('save', {
    name: form.name,
    trigger,
    generation: { topic: form.topic },
    enabled: form.enabled,
  })
}

function formatTime(t?: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
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
  overflow-y: auto;
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
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-label {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-syntax-comment);
  margin-bottom: 2px;
  margin-top: 12px;
}
.form-input {
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
.form-input:focus { border-color: var(--color-primary); }

.form-row-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
}
.toggle-switch {
  position: relative;
  width: 40px;
  height: 22px;
  border: none;
  border-radius: 11px;
  background: var(--color-border);
  cursor: pointer;
  transition: background 0.2s;
}
.toggle-switch.active { background: var(--color-primary); }
.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  transition: transform 0.2s;
}
.toggle-switch.active .toggle-knob { transform: translateX(18px); }

.edit-info {
  margin-top: 20px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-muted);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--font-size-xs);
}
.info-label {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}
.info-value {
  color: var(--color-foreground);
  font-family: var(--font-mono);
}
.error-text { color: var(--color-error); }

.drawer-footer {
  display: flex;
  gap: var(--space-sm, 8px);
  margin-top: auto;
  padding-top: 20px;
}
.btn-save {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: var(--color-primary);
  color: var(--color-primary-foreground);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-save:disabled { opacity: var(--opacity-disabled, 0.5); cursor: not-allowed; }
.btn-delete {
  padding: 10px 16px;
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md, 8px);
  background: transparent;
  color: var(--color-error);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background 0.2s;
}
.btn-delete:hover { background: var(--color-error-light); }

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
.drawer-enter-from .drawer-panel {
  transform: translateX(100%);
}
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}
</style>
