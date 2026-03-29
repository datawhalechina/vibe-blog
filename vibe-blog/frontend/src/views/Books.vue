<template>
  <div class="books-container" :class="{ 'dark-mode': isDark }">
    <!-- 终端风格导航栏 -->
    <nav class="terminal-nav">
      <div class="terminal-nav-left">
        <div class="terminal-dots">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="terminal-title">$ ls ~/books/</span>
      </div>
      <div class="terminal-nav-right">
        <a href="https://github.com/datawhalechina/vibe-blog" target="_blank" rel="noopener noreferrer" class="nav-cmd" title="GitHub - vibe-blog">GitHub</a>
        <router-link to="/" class="nav-cmd">cd ~/blog</router-link>
        <button class="theme-toggle" @click="isDark = !isDark">{{ isDark ? '☀️' : '🌙' }}</button>
      </div>
    </nav>

    <div class="container">
      <!-- 页面标题 -->
      <div class="page-title">
        <h1>> 我的书架_</h1>
        <p class="code-comment">// total: <span class="code-number">{{ books.length }}</span> books</p>
      </div>

      <!-- 终端命令栏 -->
      <div class="terminal-cmd-bar">
        <div class="terminal-dots-sm">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="cmd-prompt">$</span>
        <span class="cmd-text">./scan_books.sh --regenerate</span>
        <button class="execute-btn" :disabled="isScanning" @click="scanBooks">> run</button>
      </div>

      <!-- 书籍网格 -->
      <div class="code-cards-grid">
        <!-- 加载中 -->
        <div v-if="isLoading" class="loading-state">
          <div class="code-line"><span class="code-prompt">$</span> loading...</div>
          <div class="spinner"></div>
        </div>

        <!-- 空状态 -->
        <div v-else-if="books.length === 0" class="empty-state">
          <div class="empty-terminal">
            <div class="code-line"><span class="code-prompt">$</span> ls ~/books/</div>
            <div class="code-line"><span class="code-comment">// directory is empty</span></div>
            <div class="code-line"><span class="code-prompt">$</span> <span class="cursor-blink">_</span></div>
          </div>
          <button class="cmd-btn primary" @click="scanBooks">> scan_books</button>
        </div>

        <!-- 书籍卡片 -->
        <template v-else>
          <div 
            v-for="book in books" 
            :key="book.id" 
            class="code-card"
            :data-theme="book.theme || 'general'"
            @click.stop="openBook(book.id)"
            role="button"
            :tabindex="0"
            @keydown.enter="openBook(book.id)"
          >
            <div class="code-card-header">
              <div class="card-folder">
                <span class="folder-icon">📁</span>
                <span class="folder-name">books/</span>
              </div>
              <span class="card-theme" :class="`theme-${book.theme || 'general'}`">{{ book.theme || 'general' }}</span>
            </div>
            <div class="code-card-body">
              <div class="code-line">
                <span class="line-num">1</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">title</span>
                <span class="code-operator">=</span>
                <span class="code-string">"{{ book.title }}"</span>
              </div>
              <div class="code-line">
                <span class="line-num">2</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">chapters</span>
                <span class="code-operator">=</span>
                <span class="code-number">{{ book.chapters_count || 0 }}</span>
              </div>
              <div class="code-line">
                <span class="line-num">3</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">words</span>
                <span class="code-operator">=</span>
                <span class="code-number">{{ book.total_word_count || 0 }}</span>
                <span class="code-comment">// {{ formatWordCount(book.total_word_count || 0) }}</span>
              </div>
              <div class="code-line command-line">
                <span class="code-prompt">$</span>
                <span class="code-cmd">cat README.md</span>
              </div>
            </div>
            <div class="code-card-footer">
              <div class="card-icon">{{ getThemeIcon(book.theme) }}</div>
              <span class="card-arrow">→</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 扫描进度弹窗 -->
    <div v-if="showScanProgress" class="progress-modal">
      <div class="terminal-panel">
        <div class="terminal-panel-header">
          <div class="terminal-dots-sm">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <span class="panel-title">$ ./scan_books.sh</span>
        </div>
        <div class="terminal-panel-body">
          <div class="code-line"><span class="code-comment">// {{ scanStatus }}</span></div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: scanProgress + '%' }"></div>
          </div>
          <div class="progress-percent">{{ scanProgress }}%</div>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast.show" class="toast" :class="toast.type">
      <span class="toast-icon">{{ toast.type === 'success' ? '✓' : toast.type === 'error' ? '✗' : 'ℹ' }}</span>
      {{ toast.message }}
    </div>

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Footer from '../components/Footer.vue'

const router = useRouter()
const isDark = ref(false)

// ========== 书籍数据 ==========
interface Book {
  id: string
  title: string
  theme?: string
  cover_image?: string
  chapters_count?: number
  total_word_count?: number
}

const books = ref<Book[]>([])
const isLoading = ref(true)
const isScanning = ref(false)

// ========== Toast 通知 ==========
const toast = ref({ show: false, message: '', type: 'info' })

// ========== 扫描进度 ==========
const showScanProgress = ref(false)
const scanProgress = ref(0)
const scanStatus = ref('analyzing blog content...')

// ========== 主题图标映射 ==========
const themeIcons: Record<string, string> = {
  ai: '🤖',
  web: '🌐',
  data: '📊',
  devops: '⚙️',
  security: '🔐',
  general: '📖'
}

const getThemeIcon = (theme?: string) => {
  return themeIcons[theme || 'general'] || '📖'
}

// ========== 工具函数 ==========
const formatWordCount = (count: number) => {
  if (count >= 10000) {
    return (count / 10000).toFixed(1) + '万'
  }
  return count.toString()
}

const showToast = (message: string, type = 'info') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

const handleImageError = (event: Event, book: Book) => {
  const img = event.target as HTMLImageElement
  const parent = img.parentElement
  if (parent) {
    parent.innerHTML = `
      <div class="book-cover-default theme-${book.theme || 'general'}">
        <span class="book-icon">${getThemeIcon(book.theme)}</span>
        <span class="book-title-inner">${book.title}</span>
      </div>
    `
  }
}

// ========== API 调用 ==========
const loadBooks = async () => {
  isLoading.value = true
  try {
    const response = await fetch('/api/books')
    const result = await response.json()
    
    if (result.success) {
      books.value = result.books || []
    } else {
      showToast('加载失败: ' + result.error, 'error')
    }
  } catch (e: any) {
    showToast('加载失败: ' + e.message, 'error')
  } finally {
    isLoading.value = false
  }
}

const scanBooks = async () => {
  if (isScanning.value) return
  
  isScanning.value = true
  showScanProgress.value = true
  scanProgress.value = 0
  
  const steps = [
    { progress: 20, status: 'analyzing blog content...' },
    { progress: 40, status: 'detecting book themes...' },
    { progress: 60, status: 'generating outlines...' }
  ]
  
  for (const step of steps) {
    await new Promise(resolve => setTimeout(resolve, 500))
    scanProgress.value = step.progress
    scanStatus.value = step.status
  }
  
  try {
    const response = await fetch('/api/books/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    
    const result = await response.json()
    
    scanProgress.value = 80
    scanStatus.value = 'generating covers...'
    await new Promise(resolve => setTimeout(resolve, 500))
    
    scanProgress.value = 100
    scanStatus.value = 'done!'
    await new Promise(resolve => setTimeout(resolve, 500))
    
    if (result.success) {
      showToast(`扫描完成: 创建 ${result.books_created || 0} 本新书, 更新 ${result.books_updated || 0} 本`, 'success')
      loadBooks()
    } else {
      showToast('扫描失败: ' + (result.error || '未知错误'), 'error')
    }
  } catch (e: any) {
    showToast('扫描失败: ' + e.message, 'error')
  } finally {
    showScanProgress.value = false
    isScanning.value = false
  }
}

const openBook = (bookId: string) => {
  console.log('🔵 Opening book clicked:', bookId)
  if (!bookId) {
    console.error('❌ Book ID is empty')
    showToast('书籍 ID 无效', 'error')
    return
  }
  console.log('✅ Navigating to:', `/book/${bookId}`)
  router.push(`/book/${bookId}`).catch((err: any) => {
    console.error('❌ Navigation error:', err)
    showToast('导航失败: ' + err.message, 'error')
  })
}

// ========== 初始化 ==========
onMounted(() => {
  loadBooks()
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS 变量 */
.books-container {
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
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(255, 255, 255, 0.5);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, var(--code-surface) 0%, #f1f5f9 50%, #dbeafe 100%);
  color: var(--code-text);
}

/* 深色模式 */
.books-container.dark-mode {
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
  --glass-bg: rgba(15, 23, 42, 0.85);
  --glass-border: rgba(51, 65, 85, 0.5);
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #172554 100%);
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

/* 容器 */
.container { max-width: 1400px; margin: 0 auto; padding: 24px; }

/* 页面标题 */
.page-title { margin-bottom: 32px; }
.page-title h1 { 
  font-size: 32px; font-weight: 700; 
  background: linear-gradient(135deg, var(--code-text) 0%, var(--code-function) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}
.code-comment { color: var(--code-comment); font-style: italic; font-size: 14px; margin-top: 10px; opacity: 0.8; }
.code-number { color: var(--code-number); font-weight: 700; }

/* 终端命令栏 */
.terminal-cmd-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  margin-bottom: 28px;
  box-shadow: var(--shadow-md);
  transition: all var(--transition-normal);
}
.terminal-cmd-bar:hover {
  box-shadow: var(--shadow-lg);
}
.cmd-prompt { 
  color: var(--code-string); font-weight: 600; 
  padding: 6px 12px; background: rgba(34, 197, 94, 0.1); border-radius: 6px;
}
.cmd-text { color: var(--code-text-secondary); flex: 1; }
.execute-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border: none;
  border-radius: 10px;
  color: white;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}
.execute-btn:hover:not(:disabled) { 
  transform: translateY(-2px); 
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}
.execute-btn:active { transform: translateY(0); }
.execute-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

/* 代码卡片网格 */
.code-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 代码卡片 */
.code-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-md);
  position: relative;
  user-select: none;
  -webkit-user-select: none;
}
.code-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--code-function), var(--code-keyword));
  opacity: 0;
  transition: opacity var(--transition-normal);
}
.code-card:hover::before { opacity: 1; }
.code-card:hover {
  border-color: var(--code-function);
  box-shadow: var(--shadow-xl), 0 0 0 1px var(--code-function);
  transform: translateY(-6px) scale(1.01);
}

/* 卡片头部 */
.code-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}
.card-folder { display: flex; align-items: center; gap: 8px; }
.folder-icon { font-size: 14px; }
.folder-name { font-size: 12px; color: var(--code-text-muted); }
.card-theme { 
  font-size: 10px; padding: 4px 10px; border-radius: 6px; font-weight: 600; 
  letter-spacing: 0.3px;
  transition: all var(--transition-fast);
}
.code-card:hover .card-theme { transform: scale(1.05); }
.card-theme.theme-ai { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
.card-theme.theme-web { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.card-theme.theme-data { background: rgba(6, 182, 212, 0.15); color: #06b6d4; }
.card-theme.theme-devops { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.card-theme.theme-security { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.card-theme.theme-general { background: rgba(100, 116, 139, 0.15); color: #64748b; }

/* 卡片内容 */
.code-card-body { padding: 18px; font-size: 13px; line-height: 1.9; }
.code-line { 
  display: flex; align-items: flex-start; gap: 10px; margin-bottom: 6px;
  padding: 2px 0;
  transition: background var(--transition-fast);
  border-radius: 4px;
}
.code-card:hover .code-line:hover { background: rgba(59, 130, 246, 0.05); }
.line-num { 
  color: var(--code-text-muted); min-width: 20px; text-align: right; 
  font-size: 11px; opacity: 0.4; user-select: none;
  padding-top: 2px;
}
.code-keyword { color: var(--code-keyword); font-weight: 500; }
.code-variable { color: var(--code-variable); }
.code-operator { color: var(--code-operator); }
.code-string { color: var(--code-string); }
.command-line { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--code-border); opacity: 0.7; }
.code-prompt { color: var(--code-string); font-weight: 600; }
.code-cmd { color: var(--code-text-secondary); }

/* 卡片底部 */
.code-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: linear-gradient(0deg, var(--code-surface) 0%, transparent 100%);
  border-top: 1px solid var(--code-border);
}
.card-icon { font-size: 22px; transition: transform var(--transition-fast); }
.code-card:hover .card-icon { transform: scale(1.1); }
.card-arrow { 
  color: var(--code-function); opacity: 0; 
  transform: translateX(-8px); 
  transition: all var(--transition-normal);
  font-size: 18px;
}
.code-card:hover .card-arrow { opacity: 1; transform: translateX(0); }

/* 空状态 */
.empty-state { grid-column: 1 / -1; text-align: center; padding: 60px 20px; }
.empty-terminal { background: var(--code-bg); border: 1px solid var(--code-border); border-radius: 12px; padding: 24px; max-width: 400px; margin: 0 auto 24px; text-align: left; }
.cursor-blink { animation: blink 1s step-end infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* 加载状态 */
.loading-state { grid-column: 1 / -1; text-align: center; padding: 60px 20px; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--code-border); border-top-color: var(--code-keyword); border-radius: 50%; animation: spin 1s linear infinite; margin: 16px auto; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 命令按钮 */
.cmd-btn {
  padding: 10px 20px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--code-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}
.cmd-btn.primary { background: var(--code-keyword); color: white; border-color: var(--code-keyword); }
.cmd-btn:hover { transform: translateY(-1px); }

/* 进度弹窗 */
.progress-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.terminal-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  width: 420px;
  overflow: hidden;
  box-shadow: var(--shadow-xl);
  animation: scaleIn 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes scaleIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
.terminal-panel-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}
.panel-title { font-size: 13px; color: var(--code-text); font-weight: 600; }
.terminal-panel-body { padding: 24px; }
.progress-bar { 
  width: 100%; height: 8px; 
  background: var(--code-border); border-radius: 4px; 
  overflow: hidden; margin: 20px 0;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
}
.progress-fill { 
  height: 100%; 
  background: linear-gradient(90deg, var(--code-keyword), #7c3aed, var(--code-function));
  background-size: 200% 100%;
  border-radius: 4px; 
  transition: width 0.3s ease;
  animation: shimmer 2s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.progress-percent { text-align: center; font-size: 13px; color: var(--code-text-secondary); font-weight: 600; }

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 14px 24px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--code-text);
  z-index: 1001;
  box-shadow: var(--shadow-lg);
  animation: toastIn 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes toastIn {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.toast.success { 
  background: rgba(34, 197, 94, 0.15); 
  border-color: rgba(34, 197, 94, 0.3); 
  color: #16a34a;
  box-shadow: var(--shadow-lg), 0 0 20px rgba(34, 197, 94, 0.2);
}
.toast.error { 
  background: rgba(239, 68, 68, 0.15); 
  border-color: rgba(239, 68, 68, 0.3); 
  color: #dc2626;
  box-shadow: var(--shadow-lg), 0 0 20px rgba(239, 68, 68, 0.2);
}
.toast-icon { margin-right: 10px; }

/* 响应式 */
@media (max-width: 768px) {
  .container { padding: 16px; }
  .code-cards-grid { grid-template-columns: 1fr; }
  .terminal-cmd-bar { flex-wrap: wrap; }
  .terminal-panel { width: calc(100% - 32px); }
}
</style>
