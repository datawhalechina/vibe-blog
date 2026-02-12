<template>
  <div class="dashboard-container" :class="{ 'dark-mode': isDarkMode }">
    <AppNavbar :app-config="{ title: '任务中心' }" />

    <div class="dashboard-content">
      <h1 class="dashboard-title">任务中心</h1>

      <!-- 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.running_count }}</div>
          <div class="stat-label">处理中</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.queued_count }}</div>
          <div class="stat-label">等待中</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.completed_today }}</div>
          <div class="stat-label">今日完成</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.failed_count }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>

      <!-- 处理中的任务 -->
      <section class="task-section" v-if="running.length">
        <h2>处理中</h2>
        <div class="task-list">
          <div class="task-card running" v-for="task in running" :key="task.id">
            <div class="task-header">
              <span class="task-name">{{ task.name }}</span>
              <span class="task-stage">{{ task.current_stage }}</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
            </div>
            <div class="task-footer">
              <span class="task-detail">{{ task.stage_detail }}</span>
              <button class="btn-cancel" @click="cancelTask(task.id)">取消</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 等待中的任务 -->
      <section class="task-section" v-if="queued.length">
        <h2>等待中</h2>
        <div class="task-list">
          <div class="task-card queued" v-for="task in queued" :key="task.id">
            <div class="task-header">
              <span class="task-name">{{ task.name }}</span>
              <span class="task-badge queued-badge">排队 #{{ task.queue_position }}</span>
            </div>
            <div class="task-footer">
              <span class="task-detail">{{ task.generation?.topic }}</span>
              <button class="btn-cancel" @click="cancelTask(task.id)">取消</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 最近完成 -->
      <section class="task-section" v-if="history.length">
        <h2>最近完成</h2>
        <div class="task-list">
          <div class="task-card completed" v-for="record in history" :key="record.task_id">
            <div class="task-header">
              <span class="task-name">{{ record.task_name }}</span>
              <span class="task-badge" :class="record.status === 'completed' ? 'success-badge' : 'fail-badge'">
                {{ record.status === 'completed' ? '成功' : '失败' }}
              </span>
            </div>
            <div class="task-footer">
              <span class="task-detail">耗时 {{ formatDuration(record.duration_ms) }}</span>
              <span class="task-time">{{ formatTime(record.completed_at) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 定时任务 -->
      <section class="task-section">
        <div class="section-header">
          <h2>定时任务</h2>
          <button class="btn-add" @click="showScheduleForm = !showScheduleForm">
            {{ showScheduleForm ? '收起' : '+ 新建' }}
          </button>
        </div>

        <!-- 新建定时任务表单 -->
        <div class="schedule-form" v-if="showScheduleForm">
          <div class="form-row">
            <input v-model="scheduleForm.name" placeholder="任务名称" class="form-input" />
            <input v-model="scheduleForm.topic" placeholder="博客主题" class="form-input" />
          </div>
          <div class="form-row">
            <input v-model="scheduleForm.scheduleText" placeholder="调度时间，如：每天上午9点" class="form-input flex-2" />
            <button class="btn-parse" @click="parseScheduleText">解析</button>
          </div>
          <div class="parsed-result" v-if="parsedSchedule">
            <span v-if="parsedSchedule.type !== 'error'">{{ parsedSchedule.description }}</span>
            <span v-else class="error-text">{{ parsedSchedule.error }}</span>
          </div>
          <button class="btn-create" @click="createScheduledTask" :disabled="!canCreateSchedule">创建定时任务</button>
        </div>

        <!-- 定时任务列表 -->
        <div class="task-list" v-if="scheduledTasks.length">
          <div class="task-card scheduled" v-for="st in scheduledTasks" :key="st.id">
            <div class="task-header">
              <span class="task-name">{{ st.name }}</span>
              <span class="task-badge" :class="st.enabled ? 'active-badge' : 'paused-badge'">
                {{ st.enabled ? '运行中' : '已暂停' }}
              </span>
            </div>
            <div class="task-footer">
              <span class="task-detail">{{ st.next_run ? '下次: ' + formatTime(st.next_run) : '已暂停' }}</span>
              <div class="task-actions">
                <button class="btn-sm" @click="toggleSchedule(st)">
                  {{ st.enabled ? '暂停' : '恢复' }}
                </button>
                <button class="btn-sm btn-danger" @click="deleteSchedule(st.id)">删除</button>
              </div>
            </div>
          </div>
        </div>
        <div class="empty-hint" v-else-if="!showScheduleForm">暂无定时任务</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import AppNavbar from '../components/home/AppNavbar.vue'
import { useThemeStore } from '../stores/theme'

const API_BASE = ''
const themeStore = useThemeStore()
const isDarkMode = computed(() => themeStore.isDark)

// --- 响应式状态 ---
const stats = reactive({
  running_count: 0,
  queued_count: 0,
  completed_today: 0,
  failed_count: 0,
})
const running = ref<any[]>([])
const queued = ref<any[]>([])
const history = ref<any[]>([])
const scheduledTasks = ref<any[]>([])

// 定时任务表单
const showScheduleForm = ref(false)
const scheduleForm = reactive({ name: '', topic: '', scheduleText: '' })
const parsedSchedule = ref<any>(null)
const canCreateSchedule = computed(() =>
  scheduleForm.name && scheduleForm.topic && parsedSchedule.value?.type !== 'error' && parsedSchedule.value
)

let pollTimer: ReturnType<typeof setInterval> | null = null

// --- API 调用 ---
async function fetchSnapshot() {
  try {
    const res = await fetch(`${API_BASE}/api/queue/tasks`)
    const data = await res.json()
    Object.assign(stats, data.stats || {})
    running.value = data.running || []
    queued.value = data.queued || []
  } catch { /* 静默 */ }
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/queue/history?limit=10`)
    const data = await res.json()
    history.value = data.history || data || []
  } catch { /* 静默 */ }
}

async function fetchScheduledTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/scheduler/tasks`)
    const data = await res.json()
    scheduledTasks.value = Array.isArray(data) ? data : []
  } catch { /* 静默 */ }
}

async function cancelTask(taskId: string) {
  await fetch(`${API_BASE}/api/queue/tasks/${taskId}`, { method: 'DELETE' })
  await fetchSnapshot()
}

async function parseScheduleText() {
  try {
    const res = await fetch(`${API_BASE}/api/scheduler/parse-schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: scheduleForm.scheduleText }),
    })
    parsedSchedule.value = await res.json()
  } catch {
    parsedSchedule.value = { type: 'error', error: '解析失败' }
  }
}

async function createScheduledTask() {
  if (!canCreateSchedule.value || !parsedSchedule.value) return
  const trigger = parsedSchedule.value.type === 'cron'
    ? { type: 'cron', cron: parsedSchedule.value.cron }
    : { type: 'date', run_date: parsedSchedule.value.run_date }
  await fetch(`${API_BASE}/api/scheduler/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: scheduleForm.name,
      trigger,
      generation: { topic: scheduleForm.topic },
    }),
  })
  scheduleForm.name = ''
  scheduleForm.topic = ''
  scheduleForm.scheduleText = ''
  parsedSchedule.value = null
  showScheduleForm.value = false
  await fetchScheduledTasks()
}

async function toggleSchedule(st: any) {
  const action = st.enabled ? 'pause' : 'resume'
  await fetch(`${API_BASE}/api/scheduler/tasks/${st.id}/${action}`, { method: 'POST' })
  await fetchScheduledTasks()
}

async function deleteSchedule(id: string) {
  await fetch(`${API_BASE}/api/scheduler/tasks/${id}`, { method: 'DELETE' })
  await fetchScheduledTasks()
}

// --- 格式化 ---
function formatDuration(ms: number) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`
}

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// --- 生命周期 ---
async function refreshAll() {
  await Promise.all([fetchSnapshot(), fetchHistory(), fetchScheduledTasks()])
}

onMounted(() => {
  refreshAll()
  pollTimer = setInterval(refreshAll, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: var(--color-bg-base, #f8f9fa);
  color: var(--color-text-primary, #1a1a2e);
}
.dashboard-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 80px 20px 40px;
}
.dashboard-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 24px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}
.stat-card {
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-primary, #8b5cf6);
}
.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary, #64748b);
  margin-top: 4px;
}

/* 任务区块 */
.task-section { margin-bottom: 28px; }
.task-section h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 12px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.section-header h2 { margin-bottom: 0; }
.task-list { display: flex; flex-direction: column; gap: 10px; }

/* 任务卡片 */
.task-card {
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  padding: 14px 16px;
  transition: border-color 0.2s;
}
.task-card:hover { border-color: var(--color-primary, #8b5cf6); }
.task-card.running { border-left: 3px solid #3b82f6; }
.task-card.queued { border-left: 3px solid #f59e0b; }
.task-card.completed { border-left: 3px solid #10b981; }
.task-card.scheduled { border-left: 3px solid #8b5cf6; }

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.task-name { font-weight: 600; font-size: 0.95rem; }
.task-stage { font-size: 0.8rem; color: #3b82f6; }
.task-badge {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 500;
}
.queued-badge { background: #fef3c7; color: #92400e; }
.success-badge { background: #d1fae5; color: #065f46; }
.fail-badge { background: #fee2e2; color: #991b1b; }
.active-badge { background: #ede9fe; color: #5b21b6; }
.paused-badge { background: #f1f5f9; color: #64748b; }

/* 进度条 */
.progress-bar {
  height: 6px;
  background: var(--color-border, #e2e8f0);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.task-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--color-text-secondary, #64748b);
}
.task-detail { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-time { font-size: 0.75rem; margin-left: 8px; }
.task-actions { display: flex; gap: 6px; }

/* 按钮 */
.btn-cancel, .btn-sm {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-bg-card, #fff);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel:hover, .btn-sm:hover {
  border-color: var(--color-primary, #8b5cf6);
  color: var(--color-primary, #8b5cf6);
}
.btn-danger { color: #ef4444; }
.btn-danger:hover { border-color: #ef4444; background: #fef2f2; }
.btn-add {
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px dashed var(--color-border, #e2e8f0);
  background: transparent;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--color-primary, #8b5cf6);
  transition: all 0.2s;
}
.btn-add:hover { background: var(--color-bg-card, #fff); border-style: solid; }

/* 表单 */
.schedule-form {
  background: var(--color-bg-card, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
}
.form-row { display: flex; gap: 10px; margin-bottom: 10px; }
.form-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-bg-base, #f8f9fa);
  color: inherit;
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.2s;
}
.form-input:focus { border-color: var(--color-primary, #8b5cf6); }
.form-input.flex-2 { flex: 2; }
.btn-parse {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--color-primary, #8b5cf6);
  color: #fff;
  font-size: 0.85rem;
  cursor: pointer;
}
.parsed-result {
  font-size: 0.8rem;
  color: #10b981;
  margin-bottom: 10px;
  padding: 6px 10px;
  background: #ecfdf5;
  border-radius: 6px;
}
.error-text { color: #ef4444; }
.btn-create {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: none;
  background: var(--color-primary, #8b5cf6);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-create:disabled { opacity: 0.5; cursor: not-allowed; }
.empty-hint {
  text-align: center;
  color: var(--color-text-secondary, #64748b);
  font-size: 0.85rem;
  padding: 20px;
}

/* 暗黑模式 */
.dark-mode .stat-card,
.dark-mode .task-card,
.dark-mode .schedule-form { background: #1e1e2e; border-color: #2d2d3f; }
.dark-mode .form-input { background: #16161e; border-color: #2d2d3f; }
.dark-mode .queued-badge { background: #422006; color: #fbbf24; }
.dark-mode .success-badge { background: #064e3b; color: #34d399; }
.dark-mode .fail-badge { background: #450a0a; color: #f87171; }
.dark-mode .active-badge { background: #2e1065; color: #a78bfa; }
.dark-mode .paused-badge { background: #1e293b; color: #94a3b8; }
.dark-mode .parsed-result { background: #064e3b; color: #34d399; }
.dark-mode .btn-danger:hover { background: #450a0a; }

/* 响应式 */
@media (max-width: 640px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .form-row { flex-direction: column; }
}
</style>
