<template>
  <div class="blog-history-container">
    <!-- 标题栏 -->
    <div class="blog-list-header">
      <!-- 第一行：标题 + 统计 + 展开按钮 -->
      <div class="header-row-1">
        <button class="toggle-btn" @click="$emit('toggleList')">
          <ChevronDown :size="14" :class="{ 'rotate-up': showList }" />
        </button>
        <span class="header-title">$ ls ~/history</span>
        <span class="header-divider">|</span>
        <span class="header-count">count: {{ total || 0 }} blogs</span>
        <span class="header-divider">--sort</span>
        <Star :size="12" class="sort-icon" />
        <span class="sort-text">stars</span>
        <Clock :size="12" class="sort-icon" />
        <span class="sort-text">recent</span>
      </div>

      <!-- 第二行：Tab + 筛选 + 封面开关 -->
      <div class="header-row-2">
        <!-- Tab 切换 (博客/教程) -->
        <div class="header-tabs">
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'blogs' }"
            @click="$emit('switchTab', 'blogs')"
          >
            <FileText :size="12" />
            <span>博客</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'books' }"
            @click="$emit('switchTab', 'books')"
          >
            <Book :size="12" />
            <span>教程</span>
          </button>
        </div>

        <!-- 内容类型筛选 (全部/博客/小红书) -->
        <div v-if="currentTab === 'blogs'" class="filter-group">
          <button
            v-for="filter in contentTypeFilters"
            :key="filter.value"
            class="filter-btn"
            :class="{ active: contentType === filter.value }"
            @click="$emit('filterContentType', filter.value)"
          >
            {{ filter.label }}
          </button>
        </div>

        <!-- 封面预览开关 -->
        <div
          v-if="currentTab === 'blogs'"
          class="cover-toggle"
          :class="{ active: showCoverPreview }"
          @click="$emit('update:showCoverPreview', !showCoverPreview)"
        >
          <ImageIcon :size="12" />
          <div class="toggle-switch"></div>
        </div>
      </div>
    </div>

    <!-- 博客列表 -->
    <div v-show="showList && currentTab === 'blogs'" class="code-cards-grid">
      <div v-if="records.length === 0" class="history-empty">
        {{ contentType === 'xhs' ? '暂无小红书记录' : '// 暂无历史记录，生成博客后将自动保存' }}
      </div>
      <article
        v-for="(record, index) in records"
        :key="record.id"
        class="code-blog-card"
        :class="{
          'xhs-card': record.content_type === 'xhs',
          'with-cover': showCoverPreview && (record.cover_video || record.cover_image),
          'card-animate': animated
        }"
        :style="animated ? { animationDelay: `${0.3 + index * 0.12}s` } : {}"
        @click="$emit('loadDetail', record.id)"
      >
        <!-- 封面预览 -->
        <div v-if="showCoverPreview && (record.cover_video || record.cover_image)" class="card-cover-preview">
          <video
            v-if="record.cover_video"
            :src="record.cover_video"
            :poster="record.cover_image"
            autoplay
            loop
            muted
            playsinline
            class="cover-video"
          ></video>
          <img
            v-else-if="record.cover_image"
            :src="record.cover_image"
            :alt="record.topic"
            loading="lazy"
          />
          <div class="cover-overlay">
            <span class="cover-badge">{{ record.cover_video ? 'VIDEO' : 'COVER' }}</span>
          </div>
        </div>

        <!-- 卡片头部 -->
        <div class="code-card-header">
          <div class="code-card-folder">
            <svg class="code-card-folder-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <span class="code-card-folder-name">{{ record.content_type === 'xhs' ? 'xhs-posts' : 'blog-posts' }}</span>
          </div>
          <div class="code-card-status">
            <span class="code-card-status-dot"></span>
            <span class="code-card-status-text">module</span>
          </div>
        </div>

        <!-- 卡片主体 -->
        <div class="code-card-body">
          <div class="code-line">
            <span class="code-line-number">1</span>
            <div class="code-line-content">
              <span class="code-keyword">export</span>
              <span class="code-blog-title" :title="record.topic">{{ record.topic }}</span>
            </div>
          </div>
          <div class="code-line">
            <span class="code-line-number">2</span>
            <div class="code-line-content">
              <span class="code-variable">@</span>
              <span class="code-keyword">from</span>
              <span class="code-string">"{{ record.content_type === 'xhs' ? 'xhs/creator' : 'blog/generator' }}"</span>
            </div>
          </div>
          <div class="code-line">
            <span class="code-line-number">3</span>
            <div class="code-line-content">
              <span class="code-comment">// {{ record.content_type === 'xhs' ? '小红书图文内容' : '深度技术教程' }}</span>
            </div>
          </div>
          <div class="code-command-line">
            <span class="code-prompt">$$</span>
            <span class="code-command">cat {{ record.content_type === 'xhs' ? 'xhs-post' : 'blog' }}.md</span>
          </div>
        </div>

        <!-- 卡片底部 -->
        <div class="code-card-footer">
          <div class="code-card-tags">
            <template v-if="record.content_type === 'xhs'">
              <span class="code-tag tag-xhs">XHS</span>
              <span class="code-tag tag-info"><ImageIcon :size="10" /> {{ record.images_count || 0 }}</span>
            </template>
            <template v-else>
              <span class="code-tag tag-blog">BLOG</span>
              <span class="code-tag tag-info"><BookOpen :size="10" /> {{ record.sections_count || 0 }}</span>
              <span class="code-tag tag-info"><Code :size="10" /> {{ record.code_blocks_count || 0 }}</span>
            </template>
            <span v-if="record.cover_video" class="code-tag tag-video"><Video :size="10" /></span>
          </div>
          <span class="code-card-date">{{ formatRelativeTime(record.created_at) }}</span>
        </div>

        <!-- 悬停箭头 -->
        <div class="code-card-arrow">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </div>
      </article>
    </div>

    <!-- Show More -->
    <div v-show="showList && currentTab === 'blogs' && currentPage < totalPages" class="show-more-wrapper">
      <button class="show-more-btn" @click="$emit('loadMore')">
        <span>SHOW MORE</span>
        <span class="show-more-plus">+</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronDown, Star, Clock, FileText, Book, ImageIcon, BookOpen, Code, Video } from 'lucide-vue-next'

interface HistoryRecord {
  id: string
  topic: string
  content_type: string
  created_at: string
  cover_image?: string
  cover_video?: string
  sections_count?: number
  images_count?: number
  code_blocks_count?: number
}

interface ContentTypeFilter {
  label: string
  value: string
}

interface Props {
  showList: boolean
  currentTab: string
  contentType: string
  showCoverPreview: boolean
  records: HistoryRecord[]
  total: number
  currentPage: number
  totalPages: number
  contentTypeFilters: ContentTypeFilter[]
  animated?: boolean
}

interface Emits {
  (e: 'toggleList'): void
  (e: 'switchTab', tab: string): void
  (e: 'filterContentType', type: string): void
  (e: 'update:showCoverPreview', value: boolean): void
  (e: 'loadDetail', id: string): void
  (e: 'loadMore'): void
}

const props = defineProps<Props>()
defineEmits<Emits>()

const formatRelativeTime = (timeStr: string) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  return date.toLocaleDateString('zh-CN')
}

</script>

<style scoped>
.blog-history-container {
  width: 100%;
}

/* 统一的标题栏 - 两行布局 */
.blog-list-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-md);
  transition: var(--transition-all);
}

.blog-list-header:hover {
  border-color: var(--color-border-hover);
}

/* 第一行：标题 + 统计 + 排序 */
.header-row-1 {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-text-secondary);
}

.toggle-btn {
  display: flex;
  align-items: center;
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0;
  transition: var(--transition-colors);
}

.toggle-btn:hover {
  color: var(--color-primary);
}

.rotate-up {
  transform: rotate(180deg);
}

.header-title {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.header-divider {
  color: var(--color-muted-foreground);
  opacity: 0.5;
}

.header-count {
  color: var(--color-foreground);
  font-weight: var(--font-weight-medium);
}

.sort-icon {
  color: var(--color-primary);
}

.sort-text {
  font-size: var(--font-size-xs);
}

/* 第二行：Tab + 筛选 + 开关 */
.header-row-2 {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding-top: var(--space-sm);
  border-top: 1px solid var(--color-border);
}

/* Tab 切换 */
.header-tabs {
  display: flex;
  gap: var(--space-xs);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.tab-btn:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-hover);
}

.tab-btn.active {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* 内容类型筛选 */
.filter-group {
  display: flex;
  gap: var(--space-xs);
}

.filter-btn {
  padding: var(--space-xs) var(--space-sm);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.filter-btn:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-hover);
}

.filter-btn.active {
  background: var(--color-secondary);
  border-color: var(--color-border-hover);
  color: var(--color-foreground);
}

/* 封面预览开关 */
.cover-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs);
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-all);
  margin-left: auto;
}

.cover-toggle:hover {
  border-color: var(--color-border-hover);
}

.cover-toggle.active {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.toggle-switch {
  width: 24px;
  height: 12px;
  background: var(--color-border);
  border-radius: 12px;
  position: relative;
  transition: var(--transition-all);
}

.toggle-switch::after {
  content: '';
  position: absolute;
  width: 10px;
  height: 10px;
  background: var(--color-foreground);
  border-radius: 50%;
  top: 1px;
  left: 1px;
  transition: var(--transition-all);
}

.cover-toggle.active .toggle-switch {
  background: var(--color-primary);
}

.cover-toggle.active .toggle-switch::after {
  left: 13px;
  background: var(--color-primary-foreground);
}

/* 响应式 */
@media (max-width: 768px) {
  .header-row-1 {
    flex-wrap: wrap;
  }

  .header-row-2 {
    flex-wrap: wrap;
  }

  .cover-toggle {
    margin-left: 0;
  }
}

.code-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
  align-items: start; /* 确保卡片顶部对齐 */
}

.history-empty {
  grid-column: 1 / -1;
  padding: var(--space-3xl);
  text-align: center;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

/* 卡片打字机动画 */
.code-blog-card.card-animate {
  opacity: 0;
  transform: translateY(16px);
  animation: card-typewriter 0.4s ease forwards;
}

@keyframes card-typewriter {
  0% {
    opacity: 0;
    transform: translateY(16px);
  }
  60% {
    opacity: 0.8;
    transform: translateY(4px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.code-blog-card {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  cursor: pointer;
  transition: var(--transition-all);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%; /* 确保卡片填满网格单元 */
  min-height: 200px; /* 设置最小高度 */
}

.code-blog-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-primary-gradient);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.code-blog-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-lg), var(--shadow-primary);
  transform: translateY(-4px);
}

.code-blog-card:hover::before {
  transform: scaleX(1);
}

.card-cover-preview {
  position: relative;
  width: calc(100% + var(--space-md) * 2);
  height: 200px;
  margin: calc(var(--space-md) * -1) calc(var(--space-md) * -1) var(--space-md);
  overflow: hidden;
  background: var(--color-bg-base);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-cover-preview img,
.card-cover-preview video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
}

.cover-overlay {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
}

.cover-badge {
  padding: var(--space-xs) var(--space-sm);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  border-radius: var(--radius-sm);
  backdrop-filter: blur(4px);
}

.code-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
  min-height: 24px; /* 确保头部有最小高度 */
  flex-shrink: 0; /* 防止头部被压缩 */
}

.code-card-folder {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
  flex: 1;
  min-width: 0; /* 允许文件夹名称收缩 */
}

.code-card-folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.code-card-status {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  flex-shrink: 0; /* 防止状态被压缩 */
}

.code-card-status-dot {
  width: 6px;
  height: 6px;
  background: var(--color-success);
  border-radius: var(--radius-full);
}

.code-card-body {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  margin-bottom: var(--space-md);
  flex: 1; /* 让主体区域占据剩余空间 */
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许内容收缩 */
}

.code-line {
  display: flex;
  gap: var(--space-sm);
  line-height: var(--line-height-relaxed);
  min-height: 0; /* 允许内容收缩 */
}

.code-line-number {
  color: var(--color-text-muted);
  user-select: none;
  min-width: 20px;
  flex-shrink: 0; /* 防止行号被压缩 */
}

.code-line-content {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  flex: 1;
  min-width: 0; /* 允许内容收缩 */
  overflow: hidden; /* 隐藏溢出内容 */
}

.code-keyword {
  color: var(--color-terminal-keyword);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0; /* 关键字不压缩 */
}

.code-blog-title {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  flex: 1;
  min-width: 0; /* 允许标题收缩 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap; /* 单行显示 */
  display: block; /* 确保省略号生效 */
}

/* 如果需要多行显示，使用这个样式 */
.code-blog-title.multiline {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* 最多显示2行 */
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: var(--line-height-normal);
  max-height: calc(var(--line-height-normal) * 2em); /* 2行的高度 */
}

.code-variable {
  color: var(--color-terminal-variable);
}

.code-string {
  color: var(--color-terminal-string);
}

.code-comment {
  color: var(--color-terminal-comment);
  font-style: italic;
}

.code-command-line {
  display: flex;
  gap: var(--space-xs);
  margin-top: var(--space-xs);
  padding-top: var(--space-xs);
  border-top: 1px solid var(--color-border);
}

.code-prompt {
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

.code-command {
  color: var(--color-text-secondary);
}

.code-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-top: auto; /* 将底部推到卡片底部 */
  padding-top: var(--space-sm);
}

.code-card-tags {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  flex: 1;
  min-width: 0; /* 允许标签收缩 */
}

.code-tag {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 2px var(--space-xs);
  background: var(--color-bg-input);
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  flex-shrink: 0; /* 防止标签被压缩 */
}

.code-tag.tag-blog {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.code-tag.tag-xhs {
  background: var(--color-error-light);
  color: var(--color-error);
}

.code-card-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.code-card-arrow {
  position: absolute;
  right: var(--space-md);
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: var(--transition-all);
  color: var(--color-primary);
}

.code-blog-card:hover .code-card-arrow {
  opacity: 1;
  right: var(--space-sm);
}

/* Show More */
.show-more-wrapper {
  display: flex;
  justify-content: center;
  padding: var(--space-xl) 0 var(--space-md);
}

.show-more-btn {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-xl);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-text-secondary);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: var(--transition-all);
}

.show-more-btn:hover {
  color: var(--color-foreground);
  border-color: var(--color-foreground);
}

.show-more-plus {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-light);
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .code-cards-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }

  .history-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-sm);
  }

  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
  }

  .content-type-filter {
    flex-wrap: wrap;
  }

  .card-cover-preview {
    height: 120px;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .code-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
