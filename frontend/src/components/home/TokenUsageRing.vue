<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TokenUsageSummary } from '@/types/token'

const props = withDefaults(defineProps<{
  tokenUsage: TokenUsageSummary | null
  budget?: number
  size?: number
}>(), {
  budget: 500000,
  size: 24,
})

const showTooltip = ref(false)

const strokeWidth = computed(() => Math.max(2, props.size * 0.15))
const radius = computed(() => (props.size - strokeWidth.value) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const center = computed(() => props.size / 2)

const percentage = computed(() => {
  if (!props.tokenUsage) return 0
  return Math.min(100, (props.tokenUsage.total_tokens / props.budget) * 100)
})

const dashOffset = computed(() => {
  return circumference.value * (1 - percentage.value / 100)
})

const strokeColor = computed(() => {
  if (percentage.value > 90) return 'var(--color-error, #ef4444)'
  if (percentage.value > 70) return 'var(--color-warning, #f59e0b)'
  return 'var(--color-primary, #8b5cf6)'
})

const strokeColorClass = computed(() => {
  if (percentage.value > 90) return 'error'
  if (percentage.value > 70) return 'warning'
  return 'primary'
})

function formatTokenCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`
  return String(count)
}

function estimateCost(usage: TokenUsageSummary): string {
  const inputCost = (usage.total_input_tokens / 1_000_000) * 3
  const outputCost = (usage.total_output_tokens / 1_000_000) * 15
  return `$${(inputCost + outputCost).toFixed(2)}`
}

const sortedAgents = computed(() => {
  if (!props.tokenUsage?.agent_breakdown) return []
  return Object.entries(props.tokenUsage.agent_breakdown)
    .map(([name, data]) => ({
      name,
      total: data.input + data.output + data.cache_read + data.cache_write,
      ...data,
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
})
</script>

<template>
  <div v-if="tokenUsage" class="token-usage-ring" @mouseenter="showTooltip = true" @mouseleave="showTooltip = false">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke-width="strokeWidth"
        stroke="var(--color-border, #e2e8f0)"
        class="ring-bg"
      />
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        :stroke-width="strokeWidth"
        :stroke="strokeColor"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        :class="['ring-progress', strokeColorClass]"
      />
    </svg>
    <div v-if="showTooltip" class="token-tooltip">
      <div class="tooltip-header">
        <span class="tooltip-pct">{{ percentage.toFixed(1) }}%</span>
        <span class="tooltip-cost">{{ estimateCost(tokenUsage!) }}</span>
      </div>
      <div class="tooltip-usage">
        {{ formatTokenCount(tokenUsage!.total_tokens) }} / {{ formatTokenCount(budget) }}
      </div>
      <div v-if="sortedAgents.length" class="tooltip-agents">
        <div v-for="agent in sortedAgents" :key="agent.name" class="agent-item">
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-tokens">{{ formatTokenCount(agent.total) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.token-usage-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.token-usage-ring svg {
  transform: rotate(-90deg);
}

.ring-progress {
  transition: stroke-dashoffset var(--transition-base), stroke var(--transition-base);
}

.token-tooltip {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: var(--z-tooltip, 1600);
  min-width: 200px;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-elevated, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  white-space: nowrap;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xs);
  font-weight: var(--font-weight-semibold);
}

.tooltip-cost {
  color: var(--color-text-secondary);
}

.tooltip-usage {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.tooltip-agents {
  border-top: 1px solid var(--color-border-light, #f1f5f9);
  padding-top: var(--space-xs);
}

.agent-item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
  padding: 2px 0;
}

.agent-name {
  color: var(--color-syntax-function, #3b82f6);
}

.agent-tokens {
  color: var(--color-text-secondary);
}
</style>
