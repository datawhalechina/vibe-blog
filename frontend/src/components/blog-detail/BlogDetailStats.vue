<template>
  <section class="stats-section">
    <div class="stats-header">
      <div class="terminal-dots-sm">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
      </div>
      <span class="stats-title">$ git log --oneline --stat</span>
    </div>
    <div class="stats-content">
      <div class="stat-item">
        <svg class="stat-icon star" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"></path>
        </svg>
        <span class="stat-label">stars:</span>
        <span class="stat-value">{{ stars || 0 }}</span>
      </div>
      <div class="stat-item">
        <svg class="stat-icon fork" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="18" r="3"></circle>
          <circle cx="6" cy="6" r="3"></circle>
          <circle cx="18" cy="6" r="3"></circle>
          <path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"></path>
          <path d="M12 12v3"></path>
        </svg>
        <span class="stat-label">forks:</span>
        <span class="stat-value">{{ forks || 0 }}</span>
      </div>
      <div class="stat-item">
        <svg class="stat-icon calendar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 2v4"></path>
          <path d="M16 2v4"></path>
          <rect width="18" height="18" x="3" y="4" rx="2"></rect>
          <path d="M3 10h18"></path>
        </svg>
        <span class="stat-label">updated:</span>
        <span class="stat-value">{{ formattedDate }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
interface Props {
  stars?: number
  forks?: number
  updatedAt?: string
  formatDate?: (date?: string) => string
}

const props = defineProps<Props>()

const formattedDate = props.formatDate ? props.formatDate(props.updatedAt) : props.updatedAt || 'N/A'
</script>

<style scoped>
.stats-section {
  margin-bottom: 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--glass-bg);
}

.stats-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-muted);
}

.terminal-dots-sm { display: flex; gap: 6px; }
.terminal-dots-sm .dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.dot.yellow { background: linear-gradient(135deg, #eab308, #ca8a04); }
.dot.green { background: linear-gradient(135deg, #22c55e, #16a34a); }

.stats-content {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.stat-icon {
  width: 14px;
  height: 14px;
}

.stat-icon.star { color: var(--star); }
.stat-icon.fork { color: var(--fork); }
.stat-icon.calendar { color: var(--calendar); }

.stat-label { color: var(--text-muted); }
.stat-value { color: var(--text); font-weight: 600; }

@media (max-width: 768px) {
  .stats-content {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
