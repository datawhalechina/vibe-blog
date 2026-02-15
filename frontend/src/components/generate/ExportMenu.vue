<template>
  <div class="export-wrapper" ref="wrapperRef">
    <button
      class="export-trigger"
      :class="{ downloading: isDownloading }"
      @click="toggleMenu"
    >
      <span v-if="isDownloading" class="export-spinner">◐</span>
      <span v-else>⬇️</span>
      <span>导出</span>
    </button>

    <div v-if="showMenu" class="export-menu">
      <div class="export-menu-header">$ export --format</div>
      <button
        v-for="(fmt, i) in formats"
        :key="fmt.id"
        class="export-item"
        @click="handleExport(fmt.id)"
      >
        <span class="export-item-num">[{{ i + 1 }}]</span>
        <span class="export-item-label">{{ fmt.label }}</span>
        <span class="export-item-ext">{{ fmt.ext }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Props {
  content: string
  filename: string
  isDownloading?: boolean
  menuOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isDownloading: false,
  menuOpen: false,
})

const emit = defineEmits<{
  (e: 'export', format: string): void
}>()

const showMenu = ref(props.menuOpen)
const wrapperRef = ref<HTMLElement | null>(null)

const onClickOutside = (e: MouseEvent) => {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    showMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside, true))
onUnmounted(() => document.removeEventListener('click', onClickOutside, true))

const formats = [
  { id: 'markdown', label: 'Markdown', ext: '.md' },
  { id: 'html', label: 'HTML', ext: '.html' },
  { id: 'text', label: '纯文本', ext: '.txt' },
  { id: 'pdf', label: 'PDF', ext: '.pdf' },
  { id: 'word', label: 'Word', ext: '.docx' },
]

const toggleMenu = () => {
  if (props.isDownloading || !props.content) return
  showMenu.value = !showMenu.value
}

const handleExport = (format: string) => {
  emit('export', format)
  showMenu.value = false
}
</script>

<style scoped>
.export-wrapper {
  position: relative;
  display: inline-block;
}

.export-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.export-trigger:hover:not(.downloading) {
  color: var(--color-text-primary);
  border-color: var(--color-primary);
}

.export-trigger.downloading {
  opacity: 0.6;
  cursor: not-allowed;
}

.export-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.export-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 100;
  min-width: 200px;
  padding: var(--space-sm);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  font-family: var(--font-mono);
}

.export-menu-header {
  padding: var(--space-xs) var(--space-sm);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-bottom: var(--space-xs);
}

.export-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
  text-align: left;
}

.export-item:hover {
  background: var(--color-bg-input);
  color: var(--color-terminal-keyword, var(--color-primary));
}

.export-item-num {
  color: var(--color-text-muted);
  min-width: 24px;
}

.export-item-label {
  flex: 1;
}

.export-item-ext {
  color: var(--color-text-muted);
}
</style>
