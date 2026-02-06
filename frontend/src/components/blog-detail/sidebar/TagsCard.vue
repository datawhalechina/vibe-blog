<template>
  <div class="sidebar-card">
    <div class="sidebar-card-header">
      <span class="card-title">$ tags --list</span>
    </div>
    <div class="sidebar-card-body">
      <div class="tags-list">
        <span v-for="tag in tags" :key="tag" class="tag-item">
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  tags?: string[]
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

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 4px 10px;
  background: var(--primary-light);
  border-radius: 6px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
}
</style>
