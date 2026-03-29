<template>
  <div class="sidebar-card stats-card">
    <div class="sidebar-card-header">
      <span class="card-title">$ stat --format blog.md</span>
    </div>
    <div class="sidebar-card-body">
      <div class="stat-tags-row">
        <span class="stat-tag type">
          <span class="stat-tag-key">type</span>
          <span class="stat-tag-value">{{ articleType }}</span>
        </span>
        <span class="stat-tag sections">
          <span class="stat-tag-key">sections</span>
          <span class="stat-tag-value">{{ sectionsCount }}</span>
        </span>
        <span class="stat-tag images">
          <span class="stat-tag-key">images</span>
          <span class="stat-tag-value">{{ imagesCount }}</span>
        </span>
        <span class="stat-tag code">
          <span class="stat-tag-key">code</span>
          <span class="stat-tag-value">{{ codeBlocksCount }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  articleType?: string
  sectionsCount?: number
  imagesCount?: number
  codeBlocksCount?: number
}

defineProps<Props>()
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

.sidebar-card-body {
  padding: 16px;
}

.stat-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  transition: all 0.15s ease;
  cursor: default;
}

.stat-tag:hover {
  border-color: var(--primary);
  background: var(--surface-hover);
}

.stat-tag-key {
  color: var(--function);
  font-weight: 500;
}

.stat-tag-value {
  color: var(--text);
  font-weight: 600;
}

.stat-tag.type .stat-tag-value {
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 6px;
  border-radius: 4px;
}

.stat-tag.sections .stat-tag-key { color: var(--string); }
.stat-tag.images .stat-tag-key { color: var(--number); }
.stat-tag.code .stat-tag-key { color: var(--function); }
</style>
