<template>
  <div class="dashboard-container" :class="{ 'dark-mode': isDarkMode }">
    <AppNavbar :app-config="{ features: {} }" />

    <main class="dashboard-content">
      <header class="page-header">
        <div>
          <p class="page-path">$ pwd: ~ / dashboard</p>
          <h1 class="dashboard-title">$ task-center --view={{ activeTab }}</h1>
        </div>
        <div class="view-tabs" role="tablist" aria-label="任务中心视图">
          <button
            class="tab-button"
            :class="{ active: activeTab === 'queue' }"
            role="tab"
            :aria-selected="activeTab === 'queue'"
            data-tab="queue"
            @click="setTab('queue')"
          >
            <ListTodo :size="15" />
            <span>Queue</span>
          </button>
          <button
            class="tab-button"
            :class="{ active: activeTab === 'cron' }"
            role="tab"
            :aria-selected="activeTab === 'cron'"
            data-tab="cron"
            @click="setTab('cron')"
          >
            <CalendarClock :size="15" />
            <span>Cron</span>
          </button>
        </div>
      </header>

      <section v-if="activeTab === 'queue'" class="view-panel" data-view="queue">
        <div v-if="queueFeedback" class="status-message" role="status">
          {{ queueFeedback }}
        </div>
        <div v-if="queueLoading" class="loading-state">
          <LoaderCircle :size="24" class="spin" />
        </div>
        <div v-else-if="queueError" class="error-state" role="alert">
          <AlertTriangle :size="20" />
          <span>{{ queueError }}</span>
          <button class="icon-button" title="重试" @click="refreshQueue">
            <RefreshCw :size="15" />
          </button>
        </div>
        <template v-else>
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
            <div class="stat-card">
              <div class="stat-value">{{ stats.cancelled_count }}</div>
              <div class="stat-label">已取消</div>
            </div>
          </div>

          <section v-if="running.length" class="task-section">
            <h2>$ queue --status=running</h2>
            <div class="task-list">
              <article v-for="task in running" :key="task.id" class="task-card running">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <span class="task-stage">{{ task.current_stage || '准备中...' }}</span>
                </div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></div>
                </div>
                <div class="task-footer">
                  <span class="task-detail">{{ task.stage_detail || task.generation?.topic }}</span>
                  <span class="task-progress-text">{{ task.progress || 0 }}%</span>
                  <button class="text-button danger" @click="cancelTask(task.id)">取消</button>
                </div>
              </article>
            </div>
          </section>

          <section v-if="queued.length" class="task-section">
            <h2>$ queue --status=waiting</h2>
            <div class="task-list">
              <article v-for="task in queued" :key="task.id" class="task-card queued">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <span class="task-badge queued-badge">排队 #{{ task.queue_position }}</span>
                </div>
                <div class="task-footer">
                  <span class="task-detail">{{ task.generation?.topic }}</span>
                  <button class="text-button danger" @click="cancelTask(task.id)">取消</button>
                </div>
              </article>
            </div>
          </section>

          <section v-if="history.length" class="task-section">
            <h2>$ queue --recent</h2>
            <div class="task-list">
              <article v-for="record in history" :key="record.task_id" class="task-card completed">
                <div class="task-header">
                  <span class="task-name">{{ record.task_name }}</span>
                  <span
                    class="task-badge"
                    :class="record.status === 'completed' ? 'success-badge' : 'fail-badge'"
                  >
                    {{ record.status === 'completed' ? '成功' : '失败' }}
                  </span>
                </div>
                <div class="task-footer">
                  <span class="task-detail">耗时 {{ formatDuration(record.duration_ms) }}</span>
                  <span class="task-time">{{ formatTime(record.completed_at) }}</span>
                </div>
              </article>
            </div>
          </section>

          <section v-if="failed.length" class="task-section">
            <h2>$ queue --status=failed</h2>
            <div class="task-list">
              <article v-for="task in failed" :key="task.id" class="task-card failed">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <span class="task-badge fail-badge">失败</span>
                </div>
                <div class="task-footer">
                  <span class="task-detail">{{ task.stage_detail || task.generation?.topic }}</span>
                  <span class="task-time">{{ formatTime(task.completed_at || task.created_at) }}</span>
                </div>
              </article>
            </div>
          </section>

          <section v-if="cancelled.length" class="task-section">
            <h2>$ queue --status=cancelled</h2>
            <div class="task-list">
              <article v-for="task in cancelled" :key="task.id" class="task-card cancelled">
                <div class="task-header">
                  <span class="task-name">{{ task.name }}</span>
                  <span class="task-badge cancelled-badge">已取消</span>
                </div>
                <div class="task-footer">
                  <span class="task-detail">{{ task.generation?.topic }}</span>
                  <span class="task-time">{{ formatTime(task.completed_at || task.created_at) }}</span>
                </div>
              </article>
            </div>
          </section>

          <div v-if="!hasQueueContent" class="empty-state">
            <ListTodo :size="36" />
            <p>// 当前没有排队或近期任务</p>
          </div>
        </template>
      </section>

      <section v-else class="view-panel" data-view="cron">
        <div class="cron-toolbar">
          <div class="cron-stats">
            <span><strong>{{ activeCount }}</strong> 运行中</span>
            <span><strong>{{ pausedCount }}</strong> 已暂停</span>
            <span class="error-count"><strong>{{ errorCount }}</strong> 异常</span>
          </div>
          <button class="primary-button" @click="openDrawer()">
            <Plus :size="15" />
            <span>new-task</span>
          </button>
        </div>

        <div v-if="cronFeedback" class="status-message" role="status">
          {{ cronFeedback }}
        </div>
        <div v-if="cronError" class="error-state" role="alert">
          <AlertTriangle :size="20" />
          <span>{{ cronError }}</span>
          <button class="icon-button" title="重试" @click="refreshCron">
            <RefreshCw :size="15" />
          </button>
        </div>
        <div v-if="cronLoading" class="loading-state">
          <LoaderCircle :size="24" class="spin" />
        </div>
        <div v-else-if="jobs.length" class="cron-job-list">
          <CronJobCard
            v-for="job in jobs"
            :key="job.id"
            :job="job"
            @toggle="toggleCron"
            @delete="handleDelete"
            @retry="(item) => retryCron(item.id)"
            @run="(item) => runCron(item.id)"
          />
        </div>
        <div v-else-if="!cronError" class="empty-state">
          <CalendarOff :size="36" />
          <p>// 暂无定时任务</p>
          <button class="primary-button" @click="openDrawer()">
            <Plus :size="15" />
            <span>创建第一个任务</span>
          </button>
        </div>

        <CronJobDrawer
          :visible="drawerVisible"
          @close="drawerVisible = false"
          @save="handleSave"
          @delete="handleDelete"
        />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  CalendarClock,
  CalendarOff,
  ListTodo,
  LoaderCircle,
  Plus,
  RefreshCw,
} from 'lucide-vue-next'
import AppNavbar from '../components/home/AppNavbar.vue'
import CronJobCard from '../components/cron/CronJobCard.vue'
import CronJobDrawer from '../components/cron/CronJobDrawer.vue'
import { useCronJobs } from '../composables/useCronJobs'
import type { CronJobView } from '../composables/useCronJobs'
import { useThemeStore } from '../stores/theme'

type DashboardTab = 'queue' | 'cron'

interface QueueTask {
  id: string
  name: string
  current_stage?: string
  stage_detail?: string
  progress?: number
  queue_position?: number
  created_at?: string
  completed_at?: string
  generation?: { topic?: string }
}

interface QueueHistoryRecord {
  task_id: string
  task_name: string
  status: string
  duration_ms: number
  completed_at: string
}

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const isDarkMode = computed(() => themeStore.isDark)
const activeTab = computed<DashboardTab>(() => route.query.tab === 'cron' ? 'cron' : 'queue')

const stats = reactive({
  running_count: 0,
  queued_count: 0,
  completed_today: 0,
  failed_count: 0,
  cancelled_count: 0,
})
const running = ref<QueueTask[]>([])
const queued = ref<QueueTask[]>([])
const failed = ref<QueueTask[]>([])
const cancelled = ref<QueueTask[]>([])
const history = ref<QueueHistoryRecord[]>([])
const queueLoading = ref(true)
const queueError = ref('')
const queueFeedback = ref('')
const hasQueueContent = computed(() =>
  running.value.length
  + queued.value.length
  + failed.value.length
  + cancelled.value.length
  + history.value.length > 0
)

const {
  jobs,
  loading: cronLoading,
  error: cronError,
  feedback: cronFeedback,
  activeCount,
  pausedCount,
  errorCount,
  refresh: refreshCron,
  create: createCron,
  remove: removeCron,
  toggle: toggleCron,
  retry: retryCron,
  run: runCron,
  clearFeedback: clearCronFeedback,
} = useCronJobs(5000)

const drawerVisible = ref(false)
let queuePollTimer: ReturnType<typeof setInterval> | null = null

function setTab(tab: DashboardTab) {
  if (tab === activeTab.value) return
  const query = { ...route.query }
  if (tab === 'cron') query.tab = 'cron'
  else delete query.tab
  router.replace({ path: '/dashboard', query })
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) throw new Error('HTTP ' + response.status)
  return response.json()
}

async function refreshQueue() {
  queueError.value = ''
  try {
    const [snapshot, recent] = await Promise.all([
      fetchJson<Record<string, any>>('/api/queue/tasks'),
      fetchJson<{ history?: QueueHistoryRecord[] } | QueueHistoryRecord[]>('/api/queue/history?limit=10'),
    ])
    Object.assign(stats, snapshot.stats || {})
    running.value = snapshot.running || []
    queued.value = snapshot.queued || []
    failed.value = snapshot.failed || []
    cancelled.value = snapshot.cancelled || []
    history.value = Array.isArray(recent) ? recent : recent.history || []
  } catch {
    queueError.value = '加载队列任务失败，请重试'
  } finally {
    queueLoading.value = false
  }
}

async function cancelTask(taskId: string) {
  queueError.value = ''
  queueFeedback.value = ''
  try {
    const response = await fetch('/api/queue/tasks/' + taskId, { method: 'DELETE' })
    if (!response.ok) throw new Error('HTTP ' + response.status)
    queueFeedback.value = '队列任务已取消'
    await refreshQueue()
  } catch {
    queueError.value = '取消队列任务失败，请重试'
  }
}

function openDrawer() {
  clearCronFeedback()
  drawerVisible.value = true
}

async function handleSave(payload: Record<string, any>) {
  if (await createCron(payload)) drawerVisible.value = false
}

async function handleDelete(job: CronJobView | null | undefined) {
  if (!job) return
  if (await removeCron(job.id)) drawerVisible.value = false
}

function formatDuration(ms: number) {
  if (!ms) return '-'
  if (ms < 1000) return ms + 'ms'
  const seconds = Math.round(ms / 1000)
  return seconds < 60
    ? seconds + 's'
    : Math.floor(seconds / 60) + 'm' + (seconds % 60) + 's'
}

function formatTime(value?: string) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  refreshQueue()
  queuePollTimer = setInterval(refreshQueue, 3000)
})

onUnmounted(() => {
  if (queuePollTimer) clearInterval(queuePollTimer)
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: var(--color-bg-base);
  color: var(--color-text-primary);
}

.dashboard-content {
  width: min(960px, calc(100% - 32px));
  margin: 0 auto;
  padding: 84px 0 48px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.page-path {
  margin: 0 0 6px;
  color: var(--color-syntax-comment);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

.dashboard-title {
  margin: 0;
  color: var(--color-foreground);
  font-family: var(--font-mono);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
}

.view-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(112px, 1fr));
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: var(--color-muted);
}

.tab-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.tab-button.active {
  background: var(--color-card);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.view-panel {
  min-height: 420px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 26px;
}

.stat-card {
  min-width: 0;
  padding: 14px 10px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-card);
  text-align: center;
}

.stat-value {
  color: var(--color-syntax-function);
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: var(--font-weight-bold);
}

.stat-label {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.task-section {
  margin-bottom: 26px;
}

.task-section h2 {
  margin: 0 0 10px;
  color: var(--color-foreground);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.task-list,
.cron-job-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-left-width: 3px;
  border-radius: 8px;
  background: var(--color-card);
}

.task-card.running { border-left-color: var(--color-syntax-function); }
.task-card.queued { border-left-color: var(--color-warning); }
.task-card.completed { border-left-color: var(--color-success); }
.task-card.failed { border-left-color: var(--color-error); }
.task-card.cancelled { border-left-color: var(--color-text-tertiary); }

.task-header,
.task-footer,
.cron-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-header {
  margin-bottom: 8px;
}

.task-name {
  min-width: 0;
  overflow: hidden;
  color: var(--color-foreground);
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-stage,
.task-footer,
.task-time {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.task-detail {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-progress-text {
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.task-badge {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.queued-badge { background: var(--color-warning-light); color: var(--color-warning); }
.success-badge { background: var(--color-success-light); color: var(--color-success); }
.fail-badge { background: var(--color-error-light); color: var(--color-error); }
.cancelled-badge { background: var(--color-muted); color: var(--color-text-secondary); }

.progress-bar {
  height: 6px;
  margin-bottom: 9px;
  overflow: hidden;
  border-radius: 3px;
  background: var(--color-muted);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--color-syntax-function);
}

.cron-toolbar {
  margin-bottom: 18px;
}

.cron-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

.cron-stats strong {
  color: var(--color-success);
  font-size: var(--font-size-lg);
}

.cron-stats .error-count strong {
  color: var(--color-error);
}

.primary-button,
.text-button,
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.primary-button {
  gap: 7px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: transparent;
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.primary-button:hover {
  border-style: solid;
  background: var(--color-primary-light);
}

.text-button {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
}

.text-button.danger:hover {
  border-color: var(--color-error);
  color: var(--color-error);
}

.icon-button {
  width: 30px;
  height: 30px;
  margin-left: auto;
  border: 1px solid currentColor;
  border-radius: 6px;
  background: transparent;
  color: inherit;
}

.loading-state,
.empty-state,
.error-state {
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-state {
  color: var(--color-text-tertiary);
}

.empty-state {
  flex-direction: column;
  gap: 12px;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

.error-state {
  min-height: 80px;
  gap: 10px;
  padding: 16px;
  border: 1px solid var(--color-error);
  border-radius: 8px;
  background: var(--color-error-light);
  color: var(--color-error);
}

.status-message {
  margin-bottom: 14px;
  padding: 9px 12px;
  border: 1px solid var(--color-success);
  border-radius: 8px;
  background: var(--color-success-light);
  color: var(--color-success);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 720px) {
  .dashboard-content {
    width: min(100% - 24px, 960px);
    padding-top: 72px;
  }

  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .view-tabs {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cron-toolbar,
  .task-footer {
    align-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>
