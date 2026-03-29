<template>
  <div class="reader-container" :class="{ 'dark-mode': isDark }">
    <!-- 终端风格导航栏 -->
    <nav class="terminal-nav">
      <div class="terminal-nav-left">
        <div class="terminal-dots">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="terminal-title">$ cat {{ bookData?.title || 'book' }}/README.md</span>
      </div>
      <div class="terminal-nav-right">
        <a href="https://github.com/datawhalechina/vibe-blog" target="_blank" rel="noopener noreferrer" class="nav-cmd" title="GitHub - vibe-blog">GitHub</a>
        <router-link to="/books" class="nav-cmd">cd ~/books</router-link>
        <button class="theme-toggle" @click="isDark = !isDark">{{ isDark ? '☀️' : '🌙' }}</button>
      </div>
    </nav>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <div class="code-line"><span class="code-prompt">$</span> loading book...</div>
      <div class="spinner"></div>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="errorMsg" class="error-state">
      <div class="code-line"><span class="code-prompt">$</span> <span class="code-error">error:</span> {{ errorMsg }}</div>
      <router-link to="/books" class="cmd-btn">> cd ~/books</router-link>
    </div>
    
    <!-- 主内容 -->
    <div v-else class="reader-layout">
      <!-- 侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="terminal-dots-sm">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <span class="book-name">{{ bookData?.title }}</span>
        </div>
        <nav class="sidebar-nav">
          <div class="nav-item home" :class="{ active: !currentChapterId }" @click="goToHome">
            <span class="nav-icon">📁</span>
            <span class="nav-text">README.md</span>
          </div>
          <template v-for="(group, groupTitle) in chapterGroups" :key="groupTitle">
            <div class="nav-group-title">// {{ groupTitle }}</div>
            <div 
              v-for="section in group" 
              :key="section.id"
              class="nav-item"
              :class="{ active: currentChapterId === section.id }"
              @click="loadChapter(section.id)"
            >
              <span class="nav-icon">{{ section.blog_id ? '📄' : '📝' }}</span>
              <span class="nav-text">{{ section.section_title }}</span>
              <span v-if="section.blog_id" class="nav-status built">✓</span>
              <span v-else class="nav-status pending">...</span>
            </div>
          </template>
        </nav>
      </aside>
      
      <!-- 内容区域 -->
      <main class="content-area">
        <!-- 书籍首页 -->
        <div v-if="!currentChapterId" class="book-home">
          <div class="terminal-panel">
            <div class="terminal-panel-header">
              <div class="terminal-dots-sm">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
              </div>
              <span class="panel-title">{{ bookData?.title }}</span>
            </div>
            <div class="terminal-panel-body">
              <div class="code-block">
                <div class="code-line"><span class="code-keyword">const</span> <span class="code-variable">book</span> <span class="code-operator">=</span> {</div>
                <div class="code-line indent"><span class="code-key">title:</span> <span class="code-string">"{{ bookData?.title }}"</span>,</div>
                <div class="code-line indent"><span class="code-key">chapters:</span> <span class="code-number">{{ bookData?.chapters_count || 0 }}</span>,</div>
                <div class="code-line indent"><span class="code-key">words:</span> <span class="code-number">{{ bookData?.total_word_count || 0 }}</span>,</div>
                <div class="code-line indent"><span class="code-key">blogs:</span> <span class="code-number">{{ bookData?.blogs_count || 0 }}</span>,</div>
                <div class="code-line">}</div>
              </div>
              <p v-if="homepage?.slogan" class="book-slogan">{{ homepage.slogan }}</p>
              <p class="book-desc">{{ bookData?.description || '暂无简介' }}</p>
            </div>
          </div>
          
          <div v-if="homepage?.introduction" class="terminal-panel">
            <div class="terminal-panel-header"><span class="panel-title">> introduction</span></div>
            <div class="terminal-panel-body"><p>{{ homepage.introduction }}</p></div>
          </div>
          
          <div v-if="homepage?.highlights?.length" class="terminal-panel">
            <div class="terminal-panel-header"><span class="panel-title">> highlights</span></div>
            <div class="terminal-panel-body">
              <div v-for="(h, i) in homepage.highlights" :key="i" class="highlight-item">
                <span class="highlight-icon">{{ h.icon }}</span>
                <span class="highlight-title">{{ h.title }}</span>
                <span class="highlight-desc">{{ h.description }}</span>
              </div>
            </div>
          </div>
          
          <div class="terminal-panel">
            <div class="terminal-panel-header"><span class="panel-title">> tree ./chapters</span></div>
            <div class="terminal-panel-body outline-content" v-html="outlineHtml"></div>
          </div>
          
          <div v-if="homepage?.target_audience?.length" class="terminal-panel">
            <div class="terminal-panel-header"><span class="panel-title">> target_audience</span></div>
            <div class="terminal-panel-body">
              <div v-for="(a, i) in homepage.target_audience" :key="i" class="list-item">- {{ a }}</div>
            </div>
          </div>
          
          <div v-if="homepage?.prerequisites?.length" class="terminal-panel">
            <div class="terminal-panel-header"><span class="panel-title">> prerequisites</span></div>
            <div class="terminal-panel-body">
              <div v-for="(p, i) in homepage.prerequisites" :key="i" class="list-item">- {{ p }}</div>
            </div>
          </div>
        </div>
        
        <!-- 章节内容 -->
        <div v-else class="chapter-content">
          <div v-if="chapterLoading" class="loading-state" style="height: 300px;">
            <div class="code-line"><span class="code-prompt">$</span> loading chapter...</div>
            <div class="spinner"></div>
          </div>
          <div v-else-if="!chapterContent" class="pending-chapter">
            <div class="code-line"><span class="code-comment">// TODO: 该章节内容待完善</span></div>
            <div class="code-line"><span class="code-prompt">$</span> <span class="cursor-blink">_</span></div>
          </div>
          <div v-else class="markdown-body" v-html="renderedContent"></div>
        </div>
      </main>
    </div>

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import Footer from '../components/Footer.vue'

const route = useRoute()
const isDark = ref(false)

// ========== 状态 ==========
const isLoading = ref(true)
const errorMsg = ref('')
const bookId = ref('')

interface BookData {
  id: string
  title: string
  description?: string
  theme?: string
  cover_image?: string
  chapters_count?: number
  total_word_count?: number
  blogs_count?: number
  homepage_content?: string
  full_outline?: string
  chapters?: Array<{
    id: string
    chapter_title: string
    chapter_index: number
    section_title: string
    section_index: string
    blog_id?: string
  }>
}

const bookData = ref<BookData | null>(null)
const homepage = ref<any>(null)
const fullOutline = ref<any>(null)

// ========== 章节状态 ==========
const currentChapterId = ref<string | null>(null)
const chapterLoading = ref(false)
const chapterContent = ref('')

// ========== 主题图标 ==========
const themeIcons: Record<string, string> = {
  ai: '🤖',
  web: '🌐',
  data: '📊',
  devops: '⚙️',
  security: '🔐',
  general: '📖'
}

const getThemeIcon = (theme?: string) => themeIcons[theme || 'general'] || '📖'

const formatWordCount = (count: number) => {
  if (count >= 10000) return (count / 10000).toFixed(1) + ' 万字'
  return count + ' 字'
}

// ========== 章节分组 ==========
const chapterGroups = computed(() => {
  if (!bookData.value?.chapters) return {}
  
  const groups: Record<string, any[]> = {}
  for (const chapter of bookData.value.chapters) {
    const title = chapter.chapter_title || '未分类'
    if (!groups[title]) groups[title] = []
    groups[title].push(chapter)
  }
  return groups
})

// ========== 大纲 HTML ==========
const outlineHtml = computed(() => {
  if (fullOutline.value?.chapters) {
    return generateFullOutlineHtml(fullOutline.value)
  }
  return generateOutlineHtml()
})

const generateOutlineHtml = () => {
  if (!bookData.value?.chapters?.length) return '<p>暂无大纲</p>'
  
  const groups: Record<number, { title: string; sections: any[] }> = {}
  for (const chapter of bookData.value.chapters) {
    const idx = chapter.chapter_index
    if (!groups[idx]) {
      groups[idx] = { title: chapter.chapter_title, sections: [] }
    }
    groups[idx].sections.push(chapter)
  }
  
  let html = ''
  for (const [idx, group] of Object.entries(groups)) {
    html += `<p><strong>第 ${idx} 章 ${group.title}</strong></p><ul>`
    for (const section of group.sections) {
      if (section.blog_id) {
        html += `<li><a href="javascript:void(0)" onclick="window.loadChapter('${section.id}')">${section.section_index} ${section.section_title}</a> 📄</li>`
      } else {
        html += `<li>${section.section_index} ${section.section_title} <em>(待完善)</em></li>`
      }
    }
    html += '</ul>'
  }
  return html
}

const generateFullOutlineHtml = (outline: any) => {
  if (!outline?.chapters?.length) return '<p>暂无大纲</p>'
  
  let html = ''
  for (const chapter of outline.chapters) {
    html += `<p><strong>第 ${chapter.index} 章 ${chapter.title}</strong></p><ul>`
    
    for (const section of chapter.sections || []) {
      if (section.type === 'series') {
        const statusIcon = section.status === 'built' ? '✅' : (section.status === 'partial' ? '🔄' : '📝')
        html += `<li>${statusIcon} <strong>${section.title}</strong> (${section.articles?.length || 0} 篇)<ul>`
        
        for (const article of section.articles || []) {
          const articleIcon = article.status === 'built' ? '✅' : '📝'
          if (article.status === 'built' && article.chapter_id) {
            html += `<li>${articleIcon} [${article.order}/${article.total}] <a href="javascript:void(0)" onclick="window.loadChapter('${article.chapter_id}')">${article.title}</a></li>`
          } else {
            html += `<li>${articleIcon} [${article.order}/${article.total}] ${article.title} <em>待建设</em></li>`
          }
        }
        html += '</ul></li>'
      } else {
        const statusIcon = section.status === 'built' ? '✅' : '📝'
        if (section.status === 'built' && section.chapter_id) {
          html += `<li>${statusIcon} <a href="javascript:void(0)" onclick="window.loadChapter('${section.chapter_id}')">${section.title}</a></li>`
        } else {
          html += `<li>${statusIcon} ${section.title} <em>待建设</em></li>`
        }
      }
    }
    html += '</ul>'
  }
  return html
}

// ========== 渲染内容 ==========
const renderedContent = computed(() => {
  if (!chapterContent.value) return ''
  
  // 转换图片路径
  let content = chapterContent.value
  content = content.replace(/\(\.\//g, '(/outputs/')
  content = content.replace(/\(images\//g, '(/outputs/images/')
  content = content.replace(/src="\.\/images\//g, 'src="/outputs/images/')
  
  // 使用 marked 渲染 Markdown
  return marked(content)
})

// ========== API 调用 ==========
const loadBook = async () => {
  if (!bookId.value) {
    errorMsg.value = '缺少书籍 ID 参数'
    isLoading.value = false
    return
  }
  
  try {
    const response = await fetch(`/api/books/${bookId.value}`)
    const result = await response.json()
    
    if (result.success) {
      bookData.value = result.book
      document.title = result.book.title + ' - vibe-blog'
      
      // 解析首页内容
      if (result.book.homepage_content) {
        try {
          homepage.value = typeof result.book.homepage_content === 'string'
            ? JSON.parse(result.book.homepage_content)
            : result.book.homepage_content
        } catch (e) { console.warn('解析首页内容失败:', e) }
      }
      
      // 解析完整大纲
      if (result.book.full_outline) {
        try {
          fullOutline.value = typeof result.book.full_outline === 'string'
            ? JSON.parse(result.book.full_outline)
            : result.book.full_outline
        } catch (e) { console.warn('解析完整大纲失败:', e) }
      }
    } else {
      errorMsg.value = result.error || '无法获取书籍信息'
    }
  } catch (e: any) {
    errorMsg.value = e.message
  } finally {
    isLoading.value = false
  }
}

const loadChapter = async (chapterId: string) => {
  currentChapterId.value = chapterId
  chapterLoading.value = true
  chapterContent.value = ''
  
  try {
    const response = await fetch(`/api/books/${bookId.value}/chapters/${chapterId}`)
    const result = await response.json()
    
    if (result.success && result.has_content && result.markdown_content) {
      chapterContent.value = result.markdown_content
      
      // 渲染后高亮代码
      await nextTick()
      highlightCode()
      renderMermaid()
    }
  } catch (e: any) {
    console.error('加载章节失败:', e)
  } finally {
    chapterLoading.value = false
  }
}

const goToHome = () => {
  currentChapterId.value = null
  chapterContent.value = ''
}

// ========== 代码高亮和 Mermaid ==========
const highlightCode = () => {
  if ((window as any).hljs) {
    document.querySelectorAll('pre code').forEach((block) => {
      (window as any).hljs.highlightElement(block)
    })
  }
}

const renderMermaid = () => {
  if ((window as any).mermaid) {
    document.querySelectorAll('pre code.language-mermaid, pre code.lang-mermaid').forEach((block) => {
      const pre = block.parentElement
      if (pre) {
        const div = document.createElement('div')
        div.className = 'mermaid'
        let code = block.textContent || ''
        code = code.replace(/(\bsubgraph\s+\w+)\[""\]/g, '$1[" "]')
        code = code.replace(/(\w+)\[""\]/g, '$1[" "]')
        div.textContent = code
        pre.parentNode?.replaceChild(div, pre)
      }
    })
    ;(window as any).mermaid.run({ nodes: document.querySelectorAll('.mermaid') })
  }
}

// ========== 初始化 ==========
onMounted(() => {
  bookId.value = route.params.id as string
  loadBook()
  
  // 暴露全局函数供大纲链接使用
  ;(window as any).loadChapter = loadChapter
})

watch(() => route.params.id, (newId) => {
  if (newId && newId !== bookId.value) {
    bookId.value = newId as string
    currentChapterId.value = null
    chapterContent.value = ''
    isLoading.value = true
    loadBook()
  }
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS 变量 */
.reader-container {
  --code-bg: #ffffff;
  --code-surface: #f8fafc;
  --code-surface-hover: #f1f5f9;
  --code-border: #e2e8f0;
  --code-text: #1e293b;
  --code-text-secondary: #64748b;
  --code-text-muted: #94a3b8;
  --code-keyword: #8b5cf6;
  --code-string: #22c55e;
  --code-number: #f59e0b;
  --code-comment: #64748b;
  --code-function: #3b82f6;
  --code-variable: #ec4899;
  --code-operator: #6b7280;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
  --glass-bg: rgba(255, 255, 255, 0.85);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, var(--code-surface) 0%, #f1f5f9 50%, #faf5ff 100%);
  color: var(--code-text);
}

/* 深色模式 */
.reader-container.dark-mode {
  --code-bg: #0f172a;
  --code-surface: #1e293b;
  --code-surface-hover: #334155;
  --code-border: #334155;
  --code-text: #f1f5f9;
  --code-text-secondary: #94a3b8;
  --code-text-muted: #64748b;
  --code-keyword: #a78bfa;
  --code-string: #4ade80;
  --code-number: #fbbf24;
  --code-function: #60a5fa;
  --code-variable: #f472b6;
  --glass-bg: rgba(15, 23, 42, 0.9);
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #2e1065 100%);
}

/* 终端导航栏 */
.terminal-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 28px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--code-border);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all var(--transition-normal);
}
.terminal-nav-left, .terminal-nav-right { display: flex; align-items: center; gap: 16px; }
.terminal-dots { display: flex; gap: 8px; }
.dot { 
  width: 12px; height: 12px; border-radius: 50%; 
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  cursor: pointer;
}
.dot:hover { transform: scale(1.2); }
.dot.red { background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
.dot.yellow { background: linear-gradient(135deg, #eab308, #ca8a04); box-shadow: 0 0 8px rgba(234, 179, 8, 0.4); }
.dot.green { background: linear-gradient(135deg, #22c55e, #16a34a); box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
.terminal-dots-sm { display: flex; gap: 6px; }
.terminal-dots-sm .dot { width: 10px; height: 10px; }
.terminal-title { font-size: 13px; color: var(--code-text-secondary); letter-spacing: 0.3px; }
.nav-cmd { 
  font-size: 13px; color: var(--code-function); text-decoration: none; 
  padding: 8px 16px; background: var(--code-surface); border-radius: 8px;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}
.nav-cmd:hover { 
  background: var(--code-surface-hover); 
  border-color: var(--code-function);
  transform: translateY(-1px);
}
.theme-toggle { 
  background: var(--code-surface); border: 1px solid var(--code-border); 
  font-size: 16px; cursor: pointer; padding: 8px; border-radius: 8px;
  transition: all var(--transition-fast);
}
.theme-toggle:hover { 
  background: var(--code-surface-hover); 
  transform: rotate(15deg) scale(1.1);
}

/* 加载和错误状态 */
.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 60px);
  gap: 16px;
}
.spinner { width: 32px; height: 32px; border: 3px solid var(--code-border); border-top-color: var(--code-keyword); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.code-error { color: #ef4444; }
.cmd-btn {
  padding: 10px 20px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--code-function);
  text-decoration: none;
}
.cmd-btn:hover { background: var(--code-surface-hover); }

/* 布局 */
.reader-layout { display: flex; min-height: calc(100vh - 60px); }

/* 侧边栏 */
.sidebar {
  width: 280px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-right: 1px solid var(--code-border);
  position: fixed;
  left: 0;
  top: 49px;
  bottom: 0;
  overflow-y: auto;
  z-index: 50;
  transition: all var(--transition-normal);
}
.sidebar-header {
  padding: 14px 18px;
  border-bottom: 1px solid var(--code-border);
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
}
.book-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--code-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar-nav { padding: 10px 0; }
.nav-item {
  padding: 10px 18px;
  cursor: pointer;
  font-size: 12px;
  color: var(--code-text-secondary);
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all var(--transition-fast);
  border-left: 3px solid transparent;
  margin: 2px 0;
}
.nav-item:hover { 
  background: var(--code-surface-hover); 
  padding-left: 22px;
}
.nav-item.active {
  background: rgba(139, 92, 246, 0.12);
  color: var(--code-keyword);
  border-left-color: var(--code-keyword);
  font-weight: 500;
}
.nav-item.home { font-weight: 600; }
.nav-icon { font-size: 14px; transition: transform var(--transition-fast); }
.nav-item:hover .nav-icon { transform: scale(1.1); }
.nav-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nav-status { 
  font-size: 10px; padding: 2px 6px; border-radius: 4px; 
  transition: all var(--transition-fast);
}
.nav-status.built { color: var(--code-string); background: rgba(34, 197, 94, 0.1); }
.nav-status.pending { color: var(--code-text-muted); background: var(--code-surface); }
.nav-group-title {
  padding: 14px 18px 8px;
  font-size: 11px;
  color: var(--code-comment);
  font-style: italic;
  letter-spacing: 0.5px;
}

/* 内容区域 */
.content-area {
  flex: 1;
  margin-left: 280px;
  padding: 24px;
  max-width: 900px;
}

/* 终端面板 */
.terminal-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  margin-bottom: 20px;
  overflow: hidden;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-normal);
}
.terminal-panel:hover { box-shadow: var(--shadow-lg); }
.terminal-panel-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 18px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}
.panel-title { font-size: 13px; color: var(--code-text); font-weight: 600; letter-spacing: 0.3px; }
.terminal-panel-body { padding: 20px; }

/* 代码块 */
.code-block { font-size: 13px; line-height: 1.8; }
.code-line { display: flex; gap: 8px; }
.code-line.indent { padding-left: 24px; }
.code-keyword { color: var(--code-keyword); }
.code-variable { color: var(--code-variable); }
.code-operator { color: var(--code-operator); }
.code-string { color: var(--code-string); }
.code-number { color: var(--code-number); }
.code-key { color: var(--code-function); }
.code-comment { color: var(--code-comment); font-style: italic; }
.code-prompt { color: var(--code-string); font-weight: 600; }

/* 书籍信息 */
.book-slogan { font-size: 14px; color: var(--code-text-secondary); margin: 16px 0 8px; font-style: italic; }
.book-desc { font-size: 13px; color: var(--code-text-muted); line-height: 1.6; }

/* 亮点 */
.highlight-item { display: flex; align-items: flex-start; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--code-border); }
.highlight-item:last-child { border-bottom: none; }
.highlight-icon { font-size: 18px; }
.highlight-title { color: var(--code-keyword); font-weight: 500; min-width: 100px; }
.highlight-desc { color: var(--code-text-secondary); flex: 1; }

/* 列表项 */
.list-item { padding: 6px 0; color: var(--code-text-secondary); font-size: 13px; }

/* 大纲 */
.outline-content { font-size: 13px; }
.outline-content :deep(p) { margin: 0 0 8px 0; color: var(--code-text); }
.outline-content :deep(strong) { color: var(--code-keyword); }
.outline-content :deep(ul) { margin: 0 0 16px 0; padding-left: 20px; }
.outline-content :deep(li) { margin-bottom: 6px; color: var(--code-text-secondary); }
.outline-content :deep(a) { color: var(--code-function); text-decoration: none; }
.outline-content :deep(a:hover) { text-decoration: underline; }
.outline-content :deep(em) { color: var(--code-text-muted); font-style: normal; }

/* 章节内容 */
.chapter-content {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  padding: 36px;
  min-height: 400px;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-normal);
}
.chapter-content:hover { box-shadow: var(--shadow-lg); }

.pending-chapter {
  padding: 80px;
  text-align: center;
}
.cursor-blink { animation: blink 1s step-end infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* Markdown 渲染 */
.markdown-body { font-size: 15px; line-height: 1.9; color: var(--code-text); }
.markdown-body :deep(h1) { 
  font-size: 26px; margin: 0 0 28px; font-weight: 700; 
  background: linear-gradient(135deg, var(--code-text) 0%, var(--code-keyword) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.markdown-body :deep(h2) { 
  font-size: 20px; margin: 36px 0 18px; color: var(--code-text); 
  border-bottom: 2px solid var(--code-border); padding-bottom: 10px;
  position: relative;
}
.markdown-body :deep(h2)::after {
  content: ''; position: absolute; bottom: -2px; left: 0;
  width: 60px; height: 2px; background: var(--code-keyword);
}
.markdown-body :deep(h3) { font-size: 17px; margin: 28px 0 14px; color: var(--code-text); font-weight: 600; }
.markdown-body :deep(p) { margin: 0 0 18px; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 0 0 18px; padding-left: 28px; }
.markdown-body :deep(li) { margin-bottom: 10px; }
.markdown-body :deep(pre) {
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  padding: 20px;
  overflow-x: auto;
  margin: 24px 0;
  box-shadow: var(--shadow-sm);
}
.markdown-body :deep(code) { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.markdown-body :deep(pre code) { color: var(--code-text); }
.markdown-body :deep(:not(pre) > code) {
  background: rgba(139, 92, 246, 0.1);
  padding: 3px 8px;
  border-radius: 6px;
  color: var(--code-keyword);
  font-weight: 500;
}
.markdown-body :deep(img) { 
  max-width: 100%; border-radius: 12px; margin: 20px 0; 
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
}
.markdown-body :deep(img:hover) { transform: scale(1.02); box-shadow: var(--shadow-lg); }
.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--code-keyword);
  margin: 20px 0;
  padding: 16px 24px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(139, 92, 246, 0.02) 100%);
  border-radius: 0 12px 12px 0;
  color: var(--code-text-secondary);
}
.markdown-body :deep(a) { 
  color: var(--code-function); text-decoration: none; 
  border-bottom: 1px dashed var(--code-function);
  transition: all var(--transition-fast);
}
.markdown-body :deep(a:hover) { border-bottom-style: solid; }
.markdown-body :deep(table) { width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 12px; overflow: hidden; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--code-border); padding: 12px 16px; text-align: left; }
.markdown-body :deep(th) { background: var(--code-surface); font-weight: 600; }
.markdown-body :deep(tr:hover td) { background: rgba(139, 92, 246, 0.03); }
.markdown-body :deep(.mermaid) { text-align: center; margin: 24px 0; }

/* 响应式 */
@media (max-width: 768px) {
  .sidebar { width: 100%; position: relative; top: 0; border-right: none; border-bottom: 1px solid var(--code-border); }
  .content-area { margin-left: 0; padding: 16px; }
  .terminal-nav { padding: 12px 16px; }
  .terminal-title { display: none; }
}
</style>
