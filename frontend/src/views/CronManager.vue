<template>
  <div class="cron-manager">
    <AppNavbar :app-config="{ title: '定时任务' }" />

    <div class="cron-content">
      <!-- Stats bar -->
      <div class="stats-bar">
        <div class="stat-chip active">
          <span class="stat-num">{{ activeCount }}</span>
          <span class="stat-label">运行中</span>
        </div>
        <div class="stat-chip paused">
          <span class="stat-num">{{ pausedCount }}</span>
          <span class="stat-label">已暂停</span>
        </div>
        <div class="stat-chip error">
          <span class="stat-num">{{ errorCount }}</span>
          <span class="stat-label">异常</span>
        </div>
      </div>

      <!-- Action bar -->
      <div class="action-bar">
        <h1 class="page-title">
          <span class="title-prompt">$</span> crontab
        </h1>
        <button class="btn-new" @click="openDrawer()">
          <Plus :size="16" />
          <span>new-task</span>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <Loader :size="24" class="spin" />
      </div>

      <!-- Job list -->
      <div v-else-if="jobs.length" class="job-list">
        <CronJobCard
          v-for="job in jobs"
          :key="job.id"
          :job="job"
          @edit="openDrawer(job)"
          @toggle="toggle"
          @delete="handleDelete"
          @retry="(j) => retry(j.id)"
          @run="(j) => run(j.id)"
          @view-history="openHistory"
        />
      </div>
      <!-- Empty state -->
      <div v-else class="empty-state">
        <CalendarOff :size="40" />
        <p class="empty-text">// 暂无定时任务</p>
        <button class="btn-new" @click="openDrawer()">
          <Plus :size="16" />
          <span>创建第一个任务</span>
        </button>
      </div>

      <!-- Drawers -->
      <CronJobDrawer
        :visible="drawerVisible"
        :job="editingJob"
        @close="drawerVisible = false"
        @save="handleSave"
        @delete="handleDelete"
      />

      <CronExecutionHistory
        :visible="historyVisible"
        :job-id="historyJobId"
        :job-name="historyJobName"
        @close="historyVisible = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Loader, CalendarOff } from 'lucide-vue-next'
import AppNavbar from '../components/home/AppNavbar.vue'
import CronJobCard from '../components/cron/CronJobCard.vue'
import CronJobDrawer from '../components/cron/CronJobDrawer.vue'
import CronExecutionHistory from '../components/cron/CronExecutionHistory.vue'
import { useCronJobs } from '../composables/useCronJobs'
import type { CronJobView } from '../composables/useCronJobs'

const {
  jobs, loading, activeCount, pausedCount, errorCount,
  refresh, create, remove, toggle, retry, run,
} = useCronJobs(5000)

// Drawer state
const drawerVisible = ref(false)
const editingJob = ref<CronJobView | null>(null)

function openDrawer(job?: CronJobView) {
  editingJob.value = job || null
  drawerVisible.value = true
}

async function handleSave(payload: Record<string, any>) {
  await create(payload)
  drawerVisible.value = false
}

async function handleDelete(job: CronJobView | null | undefined) {
  if (!job) return
  await remove(job.id)
  drawerVisible.value = false
}

// History state
const historyVisible = ref(false)
const historyJobId = ref<string | null>(null)
const historyJobName = ref('')

function openHistory(job: CronJobView) {
  historyJobId.value = job.id
  historyJobName.value = job.name
  historyVisible.value = true
}
</script>

<style scoped>
.cron-manager {
  min-height: 100vh;
  background: var(--color-bg-base);
  color: var(--color-foreground);
}
.cron-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 80px 20px 40px;
}

/* Stats */
.stats-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--color-border);
  background: var(--color-card);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}
.stat-num {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-lg);
}
.stat-chip.active .stat-num { color: var(--color-success); }
.stat-chip.paused .stat-num { color: var(--color-warning); }
.stat-chip.error .stat-num { color: var(--color-error); }
.stat-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* Action bar */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-family: var(--font-mono);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}
.title-prompt {
  color: var(--color-success);
}
.btn-new {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md, 8px);
  background: transparent;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-new:hover {
  border-style: solid;
  background: var(--color-primary-light);
}

/* Job list */
.job-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Loading */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px 0;
  color: var(--color-text-tertiary);
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--color-text-tertiary);
}
.empty-text {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 640px) {
  .stats-bar { flex-wrap: wrap; }
  .action-bar { flex-direction: column; gap: 12px; align-items: flex-start; }
}
</style>
