<template>
  <div class="content-card">
    <div class="content-card-header">
      <div class="header-left">
        <div class="terminal-dots-sm">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="file-name">README.md</span>
      </div>
      <span class="readonly-badge">readonly</span>
    </div>
    <div class="content-card-body">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="code-line"><span class="prompt">$</span> loading content...</div>
        <div class="spinner"></div>
      </div>
      <!-- 博客内容 -->
      <div v-else class="blog-content prose" v-html="content"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  content?: string
  isLoading?: boolean
}

defineProps<Props>()
</script>

<style scoped>
.content-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--glass-bg);
}

.content-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.terminal-dots-sm { display: flex; gap: 6px; }
.terminal-dots-sm .dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.dot.yellow { background: linear-gradient(135deg, #eab308, #ca8a04); }
.dot.green { background: linear-gradient(135deg, #22c55e, #16a34a); }

.file-name {
  font-size: 12px;
  color: var(--text-muted);
}

.readonly-badge {
  font-size: 12px;
  color: var(--text-muted);
}

.content-card-body {
  padding: 24px 32px;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 40px;
}

.code-line {
  margin-bottom: 16px;
  font-size: 14px;
}

.prompt { color: var(--string); font-weight: 600; }

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 博客内容样式 */
.blog-content {
  font-size: calc(15px * var(--font-scale, 1));
  line-height: 1.8;
  color: var(--text);
}

.blog-content :deep(h1),
.blog-content :deep(h2),
.blog-content :deep(h3) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  color: var(--text);
}

.blog-content :deep(h1) { font-size: 1.75rem; }
.blog-content :deep(h2) { font-size: 1.5rem; }
.blog-content :deep(h3) { font-size: 1.25rem; }

.blog-content :deep(p) {
  margin-bottom: 16px;
}

.blog-content :deep(code) {
  background: var(--surface);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  color: var(--variable);
}

.blog-content :deep(pre) {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
}

.blog-content :deep(pre code) {
  background: transparent;
  padding: 0;
}

.blog-content :deep(ul),
.blog-content :deep(ol) {
  margin-bottom: 16px;
  padding-left: 24px;
}

.blog-content :deep(li) {
  margin-bottom: 8px;
}

.blog-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
  display: block;
  object-fit: contain;
}

.blog-content :deep(a) {
  color: var(--function);
  text-decoration: none;
}

.blog-content :deep(a:hover) {
  text-decoration: underline;
}

/* 表格样式 */
.blog-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 0.95rem;
  background: var(--surface);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.blog-content :deep(th),
.blog-content :deep(td) {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.blog-content :deep(th) {
  background: var(--bg);
  font-weight: 600;
  color: var(--heading);
}

.blog-content :deep(tr:last-child td) {
  border-bottom: none;
}

.blog-content :deep(tr:hover td) {
  background: var(--bg);
}

/* Mermaid 图表样式 */
.blog-content :deep(.mermaid-container) {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px 24px;
  margin: 24px 0;
  text-align: center;
  overflow: visible;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition);
}

.blog-content :deep(.mermaid-container:hover) {
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}

.blog-content :deep(.mermaid-container svg) {
  max-width: 100%;
  height: auto;
  overflow: visible;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}

/* Mermaid 图表内部元素优化 */
.blog-content :deep(.mermaid-container .node rect),
.blog-content :deep(.mermaid-container .node circle),
.blog-content :deep(.mermaid-container .node ellipse),
.blog-content :deep(.mermaid-container .node polygon) {
  transition: all 0.2s ease;
}

.blog-content :deep(.mermaid-container .node:hover rect),
.blog-content :deep(.mermaid-container .node:hover circle),
.blog-content :deep(.mermaid-container .node:hover ellipse),
.blog-content :deep(.mermaid-container .node:hover polygon) {
  filter: brightness(1.1);
  stroke-width: 2.5px;
}

.blog-content :deep(.mermaid-container .edgePath path) {
  transition: stroke-width 0.2s ease;
}

.blog-content :deep(.mermaid-container .edgePath:hover path) {
  stroke-width: 2.5px;
}

/* Mermaid 错误提示样式 */
.blog-content :deep(.mermaid-error-container) {
  background: var(--color-error-light);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  margin: var(--space-lg) 0;
  font-family: var(--font-sans);
}

.blog-content :deep(.mermaid-error-header) {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  margin-bottom: var(--space-md);
}

.blog-content :deep(.mermaid-error-header svg) {
  flex-shrink: 0;
}

.blog-content :deep(.mermaid-error-message) {
  background: var(--color-bg-elevated);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  border-left: 3px solid var(--color-error);
}

.blog-content :deep(.mermaid-error-message strong) {
  color: var(--color-error);
}

.blog-content :deep(.mermaid-error-details) {
  margin: var(--space-md) 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.blog-content :deep(.mermaid-error-details summary) {
  background: var(--color-bg-input);
  padding: var(--space-sm) var(--space-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  user-select: none;
  transition: var(--transition-colors);
}

.blog-content :deep(.mermaid-error-details summary:hover) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.blog-content :deep(.mermaid-error-details pre) {
  margin: 0;
  padding: var(--space-md);
  background: var(--color-bg-base);
  overflow-x: auto;
}

.blog-content :deep(.mermaid-error-details code) {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: var(--line-height-relaxed);
}

.blog-content :deep(.mermaid-error-tips) {
  background: var(--color-info-light);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  font-size: var(--font-size-sm);
}

.blog-content :deep(.mermaid-error-tips strong) {
  color: var(--color-info);
  display: block;
  margin-bottom: var(--space-sm);
}

.blog-content :deep(.mermaid-error-tips ul) {
  margin: 0;
  padding-left: var(--space-lg);
  color: var(--color-text-secondary);
}

.blog-content :deep(.mermaid-error-tips li) {
  margin: var(--space-xs) 0;
  line-height: var(--line-height-relaxed);
}

@media (max-width: 768px) {
  .content-card-body {
    padding: 16px;
  }
}
</style>
