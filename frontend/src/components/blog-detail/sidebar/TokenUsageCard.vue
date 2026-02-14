<template>
  <div v-if="tokenUsage" class="sidebar-card token-card">
    <div class="sidebar-card-header">
      <span class="card-title">$ token --usage</span>
      <span class="duration-badge" v-if="duration">{{ formatDuration(duration) }}</span>
    </div>
    <div class="sidebar-card-body">
      <div class="token-rows">
        <div class="token-row">
          <span class="token-label">input</span>
          <span class="token-value input">{{ formatNum(tokenUsage.total_input_tokens) }}</span>
        </div>
        <div class="token-row">
          <span class="token-label">output</span>
          <span class="token-value output">{{ formatNum(tokenUsage.total_output_tokens) }}</span>
        </div>
        <div class="token-row" v-if="tokenUsage.total_cache_read_tokens">
          <span class="token-label">cache</span>
          <span class="token-value cache">{{ formatNum(tokenUsage.total_cache_read_tokens) }}</span>
        </div>
        <div class="token-row total">
          <span class="token-label">total</span>
          <span class="token-value">{{ formatNum(tokenUsage.total_tokens) }}</span>
        </div>
        <div class="token-row">
          <span class="token-label">calls</span>
          <span class="token-value calls">{{ tokenUsage.total_calls }}</span>
        </div>
      </div>
      <!-- Agent breakdown -->
      <div v-if="agents.length" class="agent-breakdown">
        <div class="breakdown-label">agents:</div>
        <div v-for="a in agents" :key="a.name" class="agent-row">
          <span class="agent-name">{{ a.name }}</span>
          <span class="agent-tokens">{{ formatNum(a.tokens) }}</span>
          <span class="agent-calls">{{ a.calls }}x</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TokenUsage } from '../../../composables/useBlogDetail'

interface Props {
  tokenUsage?: TokenUsage | null
  duration?: number | null
}

const props = defineProps<Props>()

const agents = computed(() => {
  const bd = props.tokenUsage?.agent_breakdown
  if (!bd) return []
  return Object.entries(bd)
    .map(([name, s]) => ({ name, tokens: s.input + s.output, calls: s.calls }))
    .sort((a, b) => b.tokens - a.tokens)
})

const formatNum = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

const formatDuration = (s: number) => {
  if (s >= 60) return Math.floor(s / 60) + 'm ' + Math.round(s % 60) + 's'
  return s.toFixed(0) + 's'
}
</script>

<style scoped>
.sidebar-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--glass-bg);
}
.sidebar-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.card-title {
  font-size: 12px;
  color: var(--text-muted);
}
.duration-badge {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--string, #22c55e);
  background: rgba(34, 197, 94, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.sidebar-card-body {
  padding: 14px 16px;
}
.token-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.token-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
}
.token-row.total {
  border-top: 1px solid var(--border);
  padding-top: 6px;
  margin-top: 2px;
}
.token-label {
  color: var(--text-muted);
  font-weight: 500;
}
.token-value {
  font-weight: 600;
  color: var(--text);
}
.token-value.input { color: var(--function, #3b82f6); }
.token-value.output { color: var(--string, #22c55e); }
.token-value.cache { color: var(--number, #f59e0b); }
.token-value.calls { color: var(--variable, #ec4899); }
.agent-breakdown {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
.breakdown-label {
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}
.agent-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}
.agent-name {
  color: var(--keyword, #8b5cf6);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-tokens {
  color: var(--text);
  font-weight: 600;
  text-align: right;
  min-width: 48px;
}
.agent-calls {
  color: var(--text-muted);
  min-width: 24px;
  text-align: right;
}
</style>
