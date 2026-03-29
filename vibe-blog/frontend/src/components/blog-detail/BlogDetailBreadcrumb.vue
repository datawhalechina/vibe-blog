<template>
  <div class="breadcrumb-bar">
    <div class="breadcrumb-inner">
      <span class="prompt">$</span>
      <span class="muted">pwd:</span>
      <nav class="breadcrumb">
        <router-link to="/" class="crumb-link">~</router-link>
        <span class="separator">/</span>
        <router-link to="/blog" class="crumb-link">blog</router-link>
        <span class="separator">/</span>
        <span class="crumb-current">{{ title || 'loading...' }}</span>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string
}

defineProps<Props>()
</script>

<style scoped>
.breadcrumb-bar {
  margin-bottom: 24px;
}

.breadcrumb-inner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--glass-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
}

.prompt { color: var(--string); font-weight: 600; }
.muted { color: var(--text-muted); }

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 4px;
}

.crumb-link {
  color: var(--function);
  text-decoration: none;
  transition: color var(--transition);
}

.crumb-link:hover { color: var(--primary); }
.separator { color: var(--text-muted); }
.crumb-current { color: var(--text); font-weight: 500; }
</style>
