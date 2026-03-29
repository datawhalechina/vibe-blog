<template>
  <nav class="terminal-nav">
    <div class="terminal-nav-left">
      <div class="terminal-dots">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
      </div>
      <span class="terminal-title">$ cat ~/blog/{{ category || 'posts' }}/</span>
    </div>
    <div class="terminal-nav-right">
      <router-link to="/blog" class="nav-cmd">cd ~/blog-list</router-link>
      <router-link to="/" class="nav-cmd">cd ~/home</router-link>
      <FontSizeControl />
      <button class="theme-toggle" @click="themeStore.toggleTheme()" title="切换主题">
        <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <circle cx="12" cy="12" r="4"></circle>
          <path d="M12 2v2"></path>
          <path d="M12 20v2"></path>
          <path d="m4.93 4.93 1.41 1.41"></path>
          <path d="m17.66 17.66 1.41 1.41"></path>
          <path d="M2 12h2"></path>
          <path d="M20 12h2"></path>
          <path d="m6.34 17.66-1.41 1.41"></path>
          <path d="m19.07 4.93-1.41 1.41"></path>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
        </svg>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '../../stores/theme'
import FontSizeControl from '@/components/ui/FontSizeControl.vue'

interface Props {
  category?: string
}

defineProps<Props>()

const themeStore = useThemeStore()
const isDark = computed(() => themeStore.isDark)
</script>

<style scoped>
.terminal-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 28px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.terminal-nav-left, .terminal-nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.terminal-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
  transition: transform var(--transition);
}

.dot:hover { transform: scale(1.2); }
.dot.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.dot.yellow { background: linear-gradient(135deg, #eab308, #ca8a04); }
.dot.green { background: linear-gradient(135deg, #22c55e, #16a34a); }

.terminal-title {
  font-size: 13px;
  color: var(--text-secondary);
}

.nav-cmd {
  font-size: 13px;
  color: var(--function);
  text-decoration: none;
  padding: 8px 16px;
  background: var(--surface);
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all var(--transition);
}

.nav-cmd:hover {
  background: var(--surface-hover);
  border-color: var(--function);
  transform: translateY(-1px);
}

.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  padding: 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.theme-toggle:hover {
  background: var(--surface-hover);
  color: var(--primary);
  border-color: var(--primary);
  transform: scale(1.05);
}

.theme-toggle svg {
  transition: transform 0.2s ease;
}

.theme-toggle:hover svg {
  transform: rotate(15deg);
}

@media (max-width: 768px) {
  .terminal-nav {
    flex-direction: column;
    gap: 12px;
    padding: 12px 16px;
  }

  .terminal-nav-right {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
