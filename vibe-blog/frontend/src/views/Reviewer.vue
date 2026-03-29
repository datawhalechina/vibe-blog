<template>
  <div class="reviewer-container" :class="{ 'dark-mode': isDark }">
    <!-- 终端风格导航栏 -->
    <nav class="terminal-nav">
      <div class="terminal-nav-left">
        <div class="terminal-dots">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="terminal-title">$ reviewer --mode=evaluate</span>
      </div>
      <div class="terminal-nav-right">
        <a href="https://github.com/datawhalechina/vibe-blog" target="_blank" rel="noopener noreferrer" class="nav-cmd" title="GitHub - vibe-blog">GitHub</a>
        <router-link to="/" class="nav-cmd">cd ~/vibe-blog</router-link>
        <button class="theme-toggle" @click="isDark = !isDark">{{ isDark ? '☀️' : '🌙' }}</button>
      </div>
    </nav>

    <div class="container">
      <!-- 页面标题 -->
      <div class="page-title">
        <h1>> 教程质量评估_</h1>
        <p class="code-comment">// 添加 Git 仓库，自动评估教程质量，发现问题并给出改进建议</p>
      </div>

      <!-- 列表页面 -->
      <div v-if="currentView === 'list'" class="list-page">
        <!-- 终端风格搜索栏 -->
        <div class="terminal-input-bar">
          <div class="terminal-dots-sm">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <span class="input-label">git clone</span>
          <input v-model="gitUrl" type="text" placeholder="https://github.com/user/tutorial.git" @keyup.enter="addTutorial">
          <button class="execute-btn" @click="addTutorial">> run</button>
        </div>

        <!-- 教程卡片网格 -->
        <div class="code-cards-grid">
          <div v-for="t in tutorials" :key="t.id" class="code-card" :data-theme="getThemeByScore(t.overall_score)" @click="showDetailPage(t.id)">
            <div class="code-card-header">
              <div class="card-folder">
                <span class="folder-icon">📁</span>
                <span class="folder-name">tutorials/</span>
              </div>
              <div class="card-status">
                <span class="status-dot" :class="t.status"></span>
                <span class="status-text">{{ getStatusText(t.status) }}</span>
              </div>
            </div>
            <div class="code-card-body">
              <div class="code-line">
                <span class="line-num">1</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">tutorial</span>
                <span class="code-operator">=</span>
                <span class="code-string">"{{ t.name }}"</span>
              </div>
              <div class="code-line">
                <span class="line-num">2</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">score</span>
                <span class="code-operator">=</span>
                <span class="code-number">{{ t.overall_score?.toFixed(0) || 0 }}</span>
              </div>
              <div class="code-line">
                <span class="line-num">3</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">chapters</span>
                <span class="code-operator">=</span>
                <span class="code-number">{{ t.total_chapters || 0 }}</span>
              </div>
              <div class="code-line">
                <span class="line-num">4</span>
                <span class="code-keyword">const</span>
                <span class="code-variable">issues</span>
                <span class="code-operator">=</span>
                <span class="code-number">{{ t.total_issues || 0 }}</span>
                <span class="code-comment">// {{ t.high_issues || 0 }} high, {{ t.medium_issues || 0 }} medium</span>
              </div>
              <div class="code-line command-line">
                <span class="code-prompt">$</span>
                <span class="code-cmd">git remote -v</span>
              </div>
            </div>
            <div class="code-card-footer">
              <div class="card-tags">
                <span v-if="t.high_issues > 0" class="code-tag tag-error">error: {{ t.high_issues }}</span>
                <span v-if="t.medium_issues > 0" class="code-tag tag-warn">warn: {{ t.medium_issues }}</span>
                <span v-if="t.low_issues > 0" class="code-tag tag-info">info: {{ t.low_issues }}</span>
              </div>
              <span class="card-arrow">→</span>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="tutorials.length === 0" class="empty-state">
          <div class="empty-terminal">
            <div class="code-line"><span class="code-prompt">$</span> ls tutorials/</div>
            <div class="code-line"><span class="code-comment">// 目录为空</span></div>
            <div class="code-line"><span class="code-prompt">$</span> <span class="cursor-blink">_</span></div>
          </div>
        </div>
      </div>

      <!-- 详情页面 -->
      <div v-else-if="currentView === 'detail'" class="detail-page">
        <div class="terminal-panel">
          <div class="terminal-panel-header">
            <div class="terminal-dots-sm">
              <span class="dot red"></span>
              <span class="dot yellow"></span>
              <span class="dot green"></span>
            </div>
            <span class="panel-title">{{ currentTutorial?.name }}</span>
            <button class="back-cmd" @click="showListPage">cd ..</button>
          </div>
          <div class="terminal-panel-body">
            <div class="code-line"><span class="code-keyword">export</span> <span class="code-variable">REPO</span><span class="code-operator">=</span><span class="code-string">"{{ currentTutorial?.git_url }}"</span></div>
            <div class="stats-grid">
              <div class="stat-card primary">
                <div class="stat-value">{{ currentTutorial?.overall_score?.toFixed(1) || '-' }}</div>
                <div class="stat-label">score</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ currentTutorial?.total_chapters || 0 }}</div>
                <div class="stat-label">chapters</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ currentTutorial?.total_issues || 0 }}</div>
                <div class="stat-label">issues</div>
              </div>
            </div>
            <div class="action-buttons">
              <button class="cmd-btn primary" @click="startEvaluation">> evaluate</button>
              <button class="cmd-btn" @click="exportReport">> export</button>
              <button class="cmd-btn danger" @click="deleteTutorial">> rm -rf</button>
            </div>
          </div>
        </div>

        <!-- 章节列表 -->
        <div class="terminal-panel">
          <div class="terminal-panel-header">
            <span class="panel-title">> ls chapters/</span>
          </div>
          <div class="terminal-panel-body">
            <div v-if="chapters.length === 0" class="code-comment">// 暂无章节数据，请先进行评估</div>
            <div v-for="(c, idx) in chapters" :key="c.id" class="file-row" @click="showChapterDetail(c.id)">
              <span class="line-num">{{ idx + 1 }}</span>
              <span class="file-icon">📄</span>
              <span class="file-name">{{ c.file_name }}</span>
              <span class="file-score" :class="getScoreClass(c.overall_score)">{{ c.overall_score || 0 }}</span>
              <span v-if="c.total_issues > 0" class="file-issues">{{ c.total_issues }} issues</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 章节详情页 - 三栏布局 -->
      <div v-else-if="currentView === 'chapter'" class="chapter-detail-page">
        <div class="chapter-nav">
          <button class="back-cmd" @click="backToTutorialDetail">cd ..</button>
          <span class="chapter-path">{{ currentChapter?.file_path }}</span>
        </div>
        <div class="three-column-view">
          <!-- 左栏: 文件列表 -->
          <div class="file-list-panel">
            <div class="panel-header">
              <span class="terminal-dots-sm"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></span>
              <span>files</span>
            </div>
            <div class="panel-body">
              <div v-for="ch in chapters" :key="ch.id" class="file-item" :class="{ active: currentChapterId === ch.id }" @click="switchChapter(ch.id)">
                <span class="file-icon">{{ currentChapterId === ch.id ? '▶' : '　' }}</span>
                <span class="file-name">{{ ch.file_name }}</span>
                <span class="file-score" :class="getScoreClass(ch.overall_score || 0)">{{ ch.overall_score || 0 }}</span>
              </div>
            </div>
          </div>
          <!-- 中栏: 内容 -->
          <div class="content-panel">
            <div class="panel-header">
              <span class="code-string">"{{ currentChapter?.file_path }}"</span>
              <span class="header-stats">score: <span :class="getScoreClass(currentChapter?.overall_score || 0)">{{ currentChapter?.overall_score || 0 }}</span></span>
            </div>
            <div class="panel-body content-body">
              <div class="markdown-content" v-html="renderedContent"></div>
            </div>
          </div>
          <!-- 右栏: 问题 -->
          <div class="issues-panel">
            <div class="panel-header">
              <span>issues</span>
              <span class="issue-count">{{ currentIssues.length }}</span>
            </div>
            <div class="panel-body">
              <div v-if="currentIssues.length === 0" class="no-issues">
                <span class="code-string">"No issues found"</span>
              </div>
              <div v-for="(issue, index) in currentIssues" :key="index" class="issue-card" :class="issue.severity">
                <div class="issue-header">
                  <span class="issue-badge" :class="issue.severity">{{ issue.severity }}</span>
                  <span class="issue-type">{{ issue.issue_type }}</span>
                </div>
                <div class="issue-desc">{{ issue.description }}</div>
                <div v-if="issue.suggestion" class="issue-suggestion">
                  <span class="code-comment">// {{ issue.suggestion }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 进度面板 -->
    <div v-if="showProgress" class="progress-panel">
      <div class="terminal-panel-header">
        <div class="terminal-dots-sm">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <span class="panel-title">$ evaluate --verbose</span>
        <button class="close-btn" @click="closeProgress">×</button>
      </div>
      <div class="progress-body">
        <div v-for="(item, index) in progressItems" :key="index" class="log-line" :class="item.type">
          <span class="log-time">[{{ String(index).padStart(2, '0') }}]</span>
          <span class="log-msg">{{ item.message }}</span>
        </div>
      </div>
    </div>

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import Footer from '../components/Footer.vue'

const isDark = ref(false)
const currentView = ref<'list' | 'detail' | 'chapter'>('list')
const gitUrl = ref('')
const showProgress = ref(false)
const progressItems = ref<Array<{ message: string; type: string }>>([])
let eventSource: EventSource | null = null

interface Tutorial {
  id: number; name: string; git_url: string; status: string
  overall_score: number; total_chapters: number; total_issues: number
  high_issues: number; medium_issues: number; low_issues: number
}
interface Chapter {
  id: number; title: string; file_name: string; file_path: string
  overall_score: number; total_issues: number; high_issues: number
  medium_issues: number; low_issues: number; raw_content?: string
}
interface Issue {
  id: number; severity: string; category: string; issue_type: string
  description: string; suggestion?: string; location?: string
}

const tutorials = ref<Tutorial[]>([])
const currentTutorialId = ref<number | null>(null)
const currentTutorial = ref<Tutorial | null>(null)
const chapters = ref<Chapter[]>([])
const currentChapterId = ref<number | null>(null)
const currentChapter = ref<Chapter | null>(null)
const currentIssues = ref<Issue[]>([])

const getScoreClass = (score: number) => score >= 80 ? 'score-high' : score >= 60 ? 'score-medium' : 'score-low'
const getThemeByScore = (score: number) => score >= 80 ? 'devops' : score >= 60 ? 'security' : 'tutorial'
const getStatusText = (status: string) => ({ pending: 'pending', cloning: 'cloning...', scanning: 'scanning...', evaluating: 'running...', completed: 'done ✓', failed: 'error ✗' }[status] || status)

const renderedContent = computed(() => {
  if (!currentChapter.value?.raw_content) return '<p>暂无内容</p>'
  try { return marked(currentChapter.value.raw_content) } catch { return `<pre>${currentChapter.value.raw_content}</pre>` }
})

const loadTutorials = async () => {
  try {
    const res = await fetch('/api/reviewer/tutorials')
    const data = await res.json()
    if (data.success) tutorials.value = data.tutorials
  } catch (e) { console.error('加载教程列表失败:', e) }
}

const addTutorial = async () => {
  if (!gitUrl.value.trim()) { alert('请输入 Git 仓库 URL'); return }
  try {
    const res = await fetch('/api/reviewer/tutorials', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ git_url: gitUrl.value }) })
    const data = await res.json()
    if (data.success) { gitUrl.value = ''; loadTutorials() } else { alert(data.error || '添加失败') }
  } catch (e: any) { alert('添加失败: ' + e.message) }
}

const showListPage = () => { currentView.value = 'list'; currentTutorialId.value = null; loadTutorials() }

const showDetailPage = async (tutorialId: number) => {
  currentTutorialId.value = tutorialId; currentView.value = 'detail'
  try {
    const [tRes, cRes] = await Promise.all([fetch(`/api/reviewer/tutorials/${tutorialId}`), fetch(`/api/reviewer/tutorials/${tutorialId}/chapters`)])
    const tData = await tRes.json(); const cData = await cRes.json()
    if (tData.success) currentTutorial.value = tData.tutorial
    if (cData.success) chapters.value = cData.chapters
  } catch (e) { console.error('加载详情失败:', e) }
}

const showChapterDetail = async (chapterId: number) => {
  currentChapterId.value = chapterId; currentView.value = 'chapter'
  try {
    const res = await fetch(`/api/reviewer/chapters/${chapterId}/issues`)
    const data = await res.json()
    if (data.success) {
      currentChapter.value = data.chapter
      const order: Record<string, number> = { high: 0, medium: 1, low: 2 }
      currentIssues.value = [...(data.issues || [])].sort((a, b) => order[a.severity] - order[b.severity])
      await nextTick(); highlightCode(); renderMermaid()
    }
  } catch (e) { console.error('加载章节详情失败:', e) }
}

const switchChapter = async (chapterId: number) => { if (chapterId !== currentChapterId.value) await showChapterDetail(chapterId) }
const backToTutorialDetail = () => { currentView.value = 'detail'; currentChapterId.value = null }

const startEvaluation = () => {
  if (!currentTutorialId.value) return
  const force = confirm('是否强制重新评估？')
  const input = prompt('请输入要评估的章节数 (最大 5):', '5')
  if (input === null) return
  let max = Math.min(parseInt(input) || 5, 5)
  showProgress.value = true; progressItems.value = [{ message: '🚀 开始评估...', type: '' }]
  if (eventSource) eventSource.close()
  eventSource = new EventSource(`/api/reviewer/tutorials/${currentTutorialId.value}/evaluate-stream?max_chapters=${max}&force=${force}`)
  eventSource.onmessage = (e) => { const d = JSON.parse(e.data); addProgressItem(d.message || JSON.stringify(d)) }
  eventSource.addEventListener('progress', (e) => { const d = JSON.parse((e as MessageEvent).data); addProgressItem(d.message || '处理中...') })
  eventSource.addEventListener('chapter_complete', (e) => { const d = JSON.parse((e as MessageEvent).data); addProgressItem(`✅ ${d.chapter_title || '章节'} 评估完成`, 'success') })
  eventSource.addEventListener('complete', () => { addProgressItem('🎉 评估完成！', 'success'); eventSource?.close(); eventSource = null; showDetailPage(currentTutorialId.value!) })
  eventSource.addEventListener('error', (e) => { if ((e as MessageEvent).data) { const d = JSON.parse((e as MessageEvent).data); addProgressItem(`❌ ${d.message || '评估失败'}`, 'error') }; eventSource?.close(); eventSource = null })
  eventSource.onerror = () => { if (eventSource?.readyState === EventSource.CLOSED) return; addProgressItem('❌ 连接断开', 'error'); eventSource?.close(); eventSource = null }
}

const addProgressItem = (message: string, type = '') => { progressItems.value.push({ message, type }) }
const closeProgress = () => { showProgress.value = false; if (eventSource) { eventSource.close(); eventSource = null } }
const exportReport = () => { if (currentTutorialId.value) window.open(`/api/reviewer/tutorials/${currentTutorialId.value}/export`, '_blank') }
const deleteTutorial = async () => {
  if (!currentTutorialId.value || !confirm('确定要删除这个教程吗？')) return
  try {
    const res = await fetch(`/api/reviewer/tutorials/${currentTutorialId.value}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) showListPage(); else alert(data.error || '删除失败')
  } catch (e: any) { alert('删除失败: ' + e.message) }
}

const highlightCode = () => { if ((window as any).hljs) document.querySelectorAll('pre code').forEach((b) => (window as any).hljs.highlightElement(b)) }
const renderMermaid = () => {
  if ((window as any).mermaid) {
    document.querySelectorAll('pre code.language-mermaid').forEach((b) => {
      const pre = b.parentElement; if (pre) { const div = document.createElement('div'); div.className = 'mermaid'; div.textContent = b.textContent || ''; pre.parentNode?.replaceChild(div, pre) }
    })
    ;(window as any).mermaid.run({ nodes: document.querySelectorAll('.mermaid') })
  }
}

onMounted(() => { loadTutorials() })
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS 变量 */
.reviewer-container {
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
  --transition-slow: 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, var(--code-surface) 0%, #f1f5f9 50%, #ede9fe 100%);
  color: var(--code-text);
}

/* 深色模式 */
.reviewer-container.dark-mode {
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
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #1e1b4b 100%);
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
  background: linear-gradient(135deg, var(--code-text) 0%, var(--code-keyword) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}
.page-title h1::after { 
  content: ''; display: inline-block; width: 3px; height: 28px; 
  background: var(--code-keyword); margin-left: 4px; 
  animation: cursor-blink 1s step-end infinite; vertical-align: text-bottom;
}
@keyframes cursor-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.code-comment { color: var(--code-comment); font-style: italic; font-size: 14px; margin-top: 10px; opacity: 0.8; }

/* 终端输入栏 */
.terminal-input-bar {
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
.terminal-input-bar:focus-within {
  border-color: var(--code-keyword);
  box-shadow: var(--shadow-lg), 0 0 0 4px rgba(139, 92, 246, 0.1);
}
.input-label { 
  font-size: 13px; color: var(--code-keyword); font-weight: 600; 
  padding: 6px 12px; background: rgba(139, 92, 246, 0.1); border-radius: 6px;
}
.terminal-input-bar input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--code-text);
}
.terminal-input-bar input::placeholder { color: var(--code-text-muted); }
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
.execute-btn:hover { 
  transform: translateY(-2px); 
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}
.execute-btn:active { transform: translateY(0); }

/* 代码卡片网格 */
.code-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
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
}
.code-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--theme-color, var(--code-keyword)), transparent);
  opacity: 0;
  transition: opacity var(--transition-normal);
}
.code-card:hover::before { opacity: 1; }
.code-card:hover {
  border-color: var(--theme-color, var(--code-keyword));
  box-shadow: var(--shadow-xl), 0 0 0 1px var(--theme-color, var(--code-keyword));
  transform: translateY(-6px) scale(1.01);
}
.code-card[data-theme="devops"] { --theme-color: #22c55e; }
.code-card[data-theme="security"] { --theme-color: #f59e0b; }
.code-card[data-theme="tutorial"] { --theme-color: #ec4899; }

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
.card-status { display: flex; align-items: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--code-text-muted); }
.status-dot.completed { background: #22c55e; }
.status-dot.evaluating, .status-dot.scanning, .status-dot.cloning { background: #3b82f6; animation: pulse 1.5s infinite; }
.status-dot.failed { background: #ef4444; }
.status-dot.pending { background: #f59e0b; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.status-text { font-size: 11px; color: var(--code-text-muted); }

/* 卡片内容 */
.code-card-body { padding: 18px; font-size: 13px; line-height: 1.9; }
.code-line { 
  display: flex; align-items: flex-start; gap: 10px; margin-bottom: 6px; 
  padding: 2px 0;
  transition: background var(--transition-fast);
  border-radius: 4px;
}
.code-card:hover .code-line:hover { background: rgba(139, 92, 246, 0.05); }
.line-num { 
  color: var(--code-text-muted); min-width: 20px; text-align: right; 
  font-size: 11px; opacity: 0.4; user-select: none; 
  padding-top: 2px;
}
.code-keyword { color: var(--code-keyword); font-weight: 500; }
.code-variable { color: var(--code-variable); }
.code-operator { color: var(--code-operator); }
.code-string { color: var(--code-string); }
.code-number { color: var(--code-number); font-weight: 700; }
.code-comment { color: var(--code-comment); font-style: italic; opacity: 0.8; }
.command-line { 
  margin-top: 10px; padding-top: 10px; 
  border-top: 1px dashed var(--code-border); 
  opacity: 0.7;
}
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
.card-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.code-tag {
  padding: 4px 10px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid;
  letter-spacing: 0.3px;
  transition: all var(--transition-fast);
}
.code-tag:hover { transform: scale(1.05); }
.tag-error { background: rgba(239, 68, 68, 0.12); color: #ef4444; border-color: rgba(239, 68, 68, 0.25); }
.tag-warn { background: rgba(245, 158, 11, 0.12); color: #d97706; border-color: rgba(245, 158, 11, 0.25); }
.tag-info { background: rgba(34, 197, 94, 0.12); color: #16a34a; border-color: rgba(34, 197, 94, 0.25); }
.card-arrow { 
  color: var(--code-keyword); opacity: 0; 
  transform: translateX(-8px); 
  transition: all var(--transition-normal);
  font-size: 18px;
}
.code-card:hover .card-arrow { opacity: 1; transform: translateX(0); }

/* 空状态 */
.empty-state { padding: 60px 20px; }
.empty-terminal { background: var(--code-bg); border: 1px solid var(--code-border); border-radius: 12px; padding: 24px; max-width: 400px; margin: 0 auto; }
.cursor-blink { animation: blink 1s step-end infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

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
  padding: 14px 18px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}
.panel-title { font-size: 13px; color: var(--code-text); font-weight: 600; flex: 1; letter-spacing: 0.3px; }
.back-cmd {
  font-size: 12px;
  color: var(--code-function);
  background: var(--code-surface-hover);
  border: 1px solid var(--code-border);
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}
.back-cmd:hover { 
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed); 
  color: white; border-color: var(--code-keyword); 
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}
.terminal-panel-body { padding: 20px; }

/* 统计网格 */
.stats-grid { display: flex; gap: 16px; margin: 20px 0; }
.stat-card {
  flex: 1;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(139, 92, 246, 0.03) 100%);
  opacity: 0;
  transition: opacity var(--transition-normal);
}
.stat-card:hover::before { opacity: 1; }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-card.primary { 
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed); 
  border-color: transparent;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);
}
.stat-card.primary .stat-value, .stat-card.primary .stat-label { color: white; }
.stat-value { font-size: 32px; font-weight: 800; color: var(--code-number); letter-spacing: -1px; }
.stat-label { font-size: 11px; color: var(--code-text-muted); margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }

/* 命令按钮 */
.action-buttons { display: flex; gap: 14px; margin-top: 20px; }
.cmd-btn {
  flex: 1;
  padding: 12px 18px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  color: var(--code-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}
.cmd-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  transition: left 0.5s;
}
.cmd-btn:hover::before { left: 100%; }
.cmd-btn:hover { background: var(--code-surface-hover); transform: translateY(-2px); box-shadow: var(--shadow-sm); }
.cmd-btn.primary { 
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed); 
  color: white; border-color: transparent;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.35);
}
.cmd-btn.primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.45); }
.cmd-btn.danger { color: #ef4444; }
.cmd-btn.danger:hover { background: rgba(239, 68, 68, 0.1); border-color: #ef4444; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.2); }

/* 文件行 */
.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--code-border);
  cursor: pointer;
  transition: background 0.2s;
}
.file-row:hover { background: var(--code-surface); margin: 0 -16px; padding: 8px 16px; }
.file-row:last-child { border-bottom: none; }
.file-icon { font-size: 14px; }
.file-name { flex: 1; color: var(--code-text); }
.file-score { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.file-issues { font-size: 11px; color: #ef4444; }

/* 分数样式 */
.score-high { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.score-medium { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
.score-low { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

/* 章节导航 */
.chapter-nav {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.chapter-path { font-size: 13px; color: var(--code-string); }

/* 三栏布局 */
.three-column-view {
  display: grid;
  grid-template-columns: 200px 1fr 280px;
  gap: 0;
  height: calc(100vh - 200px);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--code-bg);
}
.file-list-panel, .content-panel, .issues-panel { display: flex; flex-direction: column; overflow: hidden; }
.file-list-panel { background: var(--code-surface); border-right: 1px solid var(--code-border); }
.issues-panel { background: var(--code-surface); border-left: 1px solid var(--code-border); }
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);
  font-size: 12px;
  color: var(--code-text-secondary);
}
.header-stats { margin-left: auto; font-size: 11px; }
.panel-body { flex: 1; overflow-y: auto; padding: 8px; }
.content-body { padding: 20px; }

/* 文件项 */
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}
.file-item:hover { background: var(--code-surface-hover); }
.file-item.active { background: rgba(139, 92, 246, 0.1); color: var(--code-keyword); }
.file-item .file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-item .file-score { font-size: 10px; padding: 1px 6px; }

/* Markdown 内容 */
.markdown-content { font-size: 14px; line-height: 1.8; color: var(--code-text); }
.markdown-content :deep(h1) { font-size: 24px; font-weight: 700; margin: 24px 0 12px; color: var(--code-keyword); }
.markdown-content :deep(h2) { font-size: 20px; font-weight: 600; margin: 20px 0 10px; }
.markdown-content :deep(h3) { font-size: 16px; font-weight: 600; margin: 16px 0 8px; }
.markdown-content :deep(p) { margin: 12px 0; }
.markdown-content :deep(pre) { background: var(--code-surface); padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; border: 1px solid var(--code-border); }
.markdown-content :deep(code) { background: var(--code-surface); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.markdown-content :deep(pre code) { background: none; padding: 0; }

/* 问题卡片 */
.issue-count { font-size: 11px; background: rgba(239, 68, 68, 0.1); color: #ef4444; padding: 2px 8px; border-radius: 10px; margin-left: auto; }
.no-issues { text-align: center; padding: 40px 20px; }
.issue-card {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  border-left: 3px solid;
}
.issue-card.high { border-left-color: #ef4444; }
.issue-card.medium { border-left-color: #f59e0b; }
.issue-card.low { border-left-color: #22c55e; }
.issue-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.issue-badge { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
.issue-badge.high { background: #ef4444; color: white; }
.issue-badge.medium { background: #f59e0b; color: white; }
.issue-badge.low { background: #22c55e; color: white; }
.issue-type { font-size: 11px; color: var(--code-text-muted); }
.issue-desc { font-size: 12px; color: var(--code-text); line-height: 1.6; }
.issue-suggestion { margin-top: 8px; font-size: 11px; }

/* 进度面板 */
.progress-panel {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 440px;
  max-height: 520px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--code-border);
  border-radius: 16px;
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.close-btn { 
  background: var(--code-surface); border: none; 
  width: 28px; height: 28px; border-radius: 8px;
  font-size: 16px; cursor: pointer; color: var(--code-text-muted); margin-left: auto;
  transition: all var(--transition-fast);
}
.close-btn:hover { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.progress-body { flex: 1; overflow-y: auto; padding: 14px 18px; max-height: 420px; font-size: 12px; }
.log-line { 
  display: flex; gap: 10px; padding: 6px 8px; 
  border-bottom: 1px solid var(--code-border); 
  border-radius: 6px;
  transition: background var(--transition-fast);
}
.log-line:hover { background: var(--code-surface); }
.log-line:last-child { border-bottom: none; }
.log-time { color: var(--code-text-muted); min-width: 36px; font-weight: 500; }
.log-msg { color: var(--code-text-secondary); }
.log-line.error .log-msg { color: #ef4444; font-weight: 500; }
.log-line.success .log-msg { color: #22c55e; font-weight: 500; }

/* 响应式 */
@media (max-width: 1200px) {
  .three-column-view { grid-template-columns: 1fr; height: auto; }
  .file-list-panel { display: none; }
  .issues-panel { border-left: none; border-top: 1px solid var(--code-border); max-height: 400px; }
}
@media (max-width: 768px) {
  .container { padding: 16px; }
  .code-cards-grid { grid-template-columns: 1fr; }
  .terminal-input-bar { flex-wrap: wrap; }
  .progress-panel { width: calc(100% - 32px); left: 16px; right: 16px; }
  .stats-grid { flex-direction: column; }
}
</style>
