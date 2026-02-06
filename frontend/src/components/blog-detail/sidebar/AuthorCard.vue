<template>
  <div class="sidebar-card">
    <div class="sidebar-card-header">
      <span class="card-title">package.json</span>
      <div class="header-actions">
        <button class="action-btn" title="分享">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="18" cy="5" r="3"></circle>
            <circle cx="6" cy="12" r="3"></circle>
            <circle cx="18" cy="19" r="3"></circle>
            <line x1="8.59" x2="15.42" y1="13.51" y2="17.49"></line>
            <line x1="15.41" x2="8.59" y1="6.51" y2="10.49"></line>
          </svg>
        </button>
        <button
          class="action-btn favorite"
          :class="{ active: isFavorite }"
          @click="$emit('toggleFavorite')"
          title="收藏"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"></path>
          </svg>
        </button>
      </div>
    </div>
    <div class="sidebar-card-body">
      <div class="author-info">
        <img :src="authorAvatar" :alt="author" class="author-avatar">
        <div class="author-details">
          <div class="json-line">
            <span class="json-key">"author"</span>: <span class="json-value">"{{ author }}"</span>
          </div>
          <div class="json-line">
            <span class="json-key">"category"</span>: <span class="json-value">"{{ category }}"</span>
          </div>
        </div>
      </div>
      <a v-if="sourceUrl" :href="sourceUrl" target="_blank" class="source-link">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path>
          <path d="M9 18c-4.51 2-5-2-7-2"></path>
        </svg>
        <span class="prompt">$</span> gh browse
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  author?: string
  authorAvatar?: string
  category?: string
  sourceUrl?: string
  isFavorite?: boolean
}

defineProps<Props>()
defineEmits<{
  toggleFavorite: []
}>()
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

.header-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  background: transparent;
  border: none;
  padding: 6px;
  cursor: pointer;
  border-radius: 6px;
  color: var(--text-muted);
  transition: all var(--transition);
}

.action-btn:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.action-btn.favorite:hover,
.action-btn.favorite.active {
  color: #ef4444;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.sidebar-card-body {
  padding: 16px;
}

.author-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.author-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
}

.author-details {
  flex: 1;
  min-width: 0;
}

.json-line {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.json-key { color: var(--function); }
.json-value { color: var(--string); }

.source-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  transition: all var(--transition);
}

.source-link:hover {
  background: var(--surface-hover);
  border-color: var(--primary);
}

.source-link svg {
  width: 16px;
  height: 16px;
}

.prompt { color: var(--string); font-weight: 600; }
</style>
