<template>
  <Teleport to="body">
    <div
      v-if="visible && citation && !isMobile"
      class="citation-tooltip"
      :style="{ top: position.top + 'px', left: position.left + 'px' }"
      @mouseenter="onTooltipEnter"
      @mouseleave="onTooltipLeave"
    >
      <div class="citation-header">
        <span class="citation-index">[{{ index }}]</span>
        <span class="citation-domain">{{ citation.domain }}</span>
      </div>
      <div class="citation-body">
        <div class="citation-title">{{ citation.title }}</div>
        <div class="citation-snippet">{{ citation.snippet }}</div>
        <div class="citation-footer">
          <span v-if="citation.relevance" class="citation-relevance">
            ⭐ {{ citation.relevance }}%
          </span>
          <a :href="citation.url" target="_blank" class="citation-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" x2="21" y1="14" y2="3"></line>
            </svg>
            打开原文
          </a>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Citation {
  url: string
  title: string
  domain: string
  snippet: string
  relevance?: number
}

interface Props {
  visible: boolean
  citation: Citation | null
  index: number
  position: { top: number; left: number }
}

defineProps<Props>()
const emit = defineEmits<{
  (e: 'keep-visible'): void
  (e: 'request-hide'): void
}>()

const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < 768)

function onResize() {
  windowWidth.value = window.innerWidth
}

onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

function onTooltipEnter() {
  emit('keep-visible')
}

function onTooltipLeave() {
  emit('request-hide')
}
</script>

<style scoped>
.citation-tooltip {
  position: fixed;
  z-index: 10000;
  width: 320px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  box-shadow: var(--shadow-lg);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  overflow: hidden;
  backdrop-filter: blur(12px);
}

.citation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

.citation-index {
  color: var(--color-text-muted);
  font-weight: var(--font-weight-bold);
}

.citation-domain {
  color: var(--color-syntax-string, #22c55e);
}

.citation-body {
  padding: 12px 14px;
}

.citation-title {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  margin-bottom: 6px;
  line-height: var(--line-height-normal);
}

.citation-snippet {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-relaxed);
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.citation-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}

.citation-relevance {
  color: var(--color-warning, #f59e0b);
  font-size: var(--font-size-xs);
}

.citation-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-syntax-function, #3b82f6);
  text-decoration: none;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  transition: color 0.2s ease;
}

.citation-link:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.citation-link svg {
  flex-shrink: 0;
}
</style>
