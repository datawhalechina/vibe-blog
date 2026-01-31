<template>
  <div class="home-container" :class="{ 'dark-mode': isDarkMode }">
    <div class="bg-animation"></div>

    <!-- 导航栏 -->
    <nav class="navbar">
      <a href="https://github.com/datawhalechina/vibe-blog" target="_blank" rel="noopener noreferrer" class="logo" title="GitHub - vibe-blog">&lt;vibe-blog /&gt;</a>
      <div class="nav-actions">
        <router-link v-if="appConfig.features?.xhs_tab" to="/xhs" class="nav-link">
          <BookOpen :size="14" />
          <span>小红书创作</span>
        </router-link>
        <router-link v-if="appConfig.features?.reviewer" to="/reviewer" class="nav-link">
          <Search :size="14" />
          <span>教程评估</span>
        </router-link>
        <button class="theme-toggle" :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'" @click="toggleTheme">
          <Sun v-if="isDarkMode" :size="18" />
          <Moon v-else :size="18" />
        </button>
      </div>
    </nav>

    <!-- Hero 区域 -->
    <section class="hero">
      <h1>&gt; Browse Blog Posts<span class="cursor"></span></h1>
      <p>$ find ./blogs -type f -name "*.md" | wc -l</p>
    </section>

    <!-- 博客卡片容器 -->
    <div class="code-cards-container">
      <!-- 主输入框 - 终端风格搜索栏 -->
      <div class="code-input-card">
        <!-- Code Style 粒子背景 -->
        <div class="particles-bg">
          <!-- 代码符号粒子 -->
          <span class="code-particle cp1">&lt;/&gt;</span>
          <span class="code-particle cp2">{}</span>
          <span class="code-particle cp3">( )</span>
          <span class="code-particle cp4">[ ]</span>
          <span class="code-particle cp5">=&gt;</span>
          <span class="code-particle cp6">/**</span>
          <span class="code-particle cp7">$_</span>
          <span class="code-particle cp8">::</span>
        </div>
        <!-- 终端头部 -->
        <div class="code-input-header">
          <div class="terminal-dots">
            <span class="terminal-dot red"></span>
            <span class="terminal-dot yellow"></span>
            <span class="terminal-dot green"></span>
          </div>
          <span class="terminal-title">vibe-blog ~ generate</span>
        </div>

        <!-- 输入区域 -->
        <div class="code-input-body">
          <div class="code-input-prompt">
            <span class="code-prompt">$</span>
            <span class="code-command">find</span>
          </div>
          <textarea 
            v-model="topic" 
            class="code-input-textarea"
            placeholder="输入技术主题，如：LangGraph 入门教程、Redis 性能优化、Vue3 最佳实践..."
            @keydown.enter.ctrl="handleGenerate"
          ></textarea>
        </div>

        <!-- 已上传文档列表 -->
        <div v-if="uploadedDocuments.length > 0" class="code-input-docs">
          <div 
            v-for="doc in uploadedDocuments" 
            :key="doc.id" 
            class="code-doc-tag"
            :class="{ 'doc-error': doc.status === 'error', 'doc-ready': doc.status === 'ready' }"
          >
            <FileText :size="14" class="doc-icon" />
            <span class="doc-name">{{ truncateFilename(doc.filename) }}</span>
            <FileCheck v-if="doc.status === 'ready'" :size="14" class="doc-status" />
            <Loader v-else-if="isSpinningStatus(doc.status)" :size="14" class="doc-status loading" />
            <button class="doc-remove" @click="removeDocument(doc.id)"><X :size="12" /></button>
          </div>
        </div>

        <!-- 底部工具栏 -->
        <div class="code-input-footer">
          <div class="code-input-actions-left">
            <label class="code-action-btn" @mouseenter="showUploadTooltip = true" @mouseleave="showUploadTooltip = false">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
              </svg>
              <span>附件</span>
              <input type="file" accept=".pdf,.md,.txt,.markdown" multiple @change="handleFileUpload">
            </label>
            <div v-if="showUploadTooltip" class="upload-tooltip">
              PDF 文件不超过 15 页<br>
              支持 PDF、Markdown、TXT 格式
            </div>
            <button class="code-action-btn" :class="{ active: showAdvancedOptions }" @click="showAdvancedOptions = !showAdvancedOptions">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
              <span>高级选项</span>
            </button>
          </div>
          <div class="code-input-actions-right">
            <span class="code-input-hint">Ctrl + Enter</span>
            <button 
              class="code-generate-btn" 
              :disabled="isLoading || !topic.trim()"
              @click="handleGenerate"
              :title="isLoading ? '生成中...' : '生成博客'"
            >
              <span v-if="isLoading" class="loading-spinner"></span>
              <Rocket v-else :size="16" />
              <span class="btn-text">{{ isLoading ? '生成中' : 'execute' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 高级选项面板 -->
      <div v-if="showAdvancedOptions" class="advanced-options-panel">
        <div class="options-row">
          <!-- 文章类型 -->
          <div class="option-item">
            <span class="option-label"><FileText :size="14" /> 文章类型:</span>
            <select v-model="articleType">
              <option value="tutorial">教程型</option>
              <option value="problem-solution">问题解决</option>
              <option value="comparison">对比分析</option>
              <option value="storybook">科普绘本</option>
            </select>
          </div>

          <!-- 文章长度 -->
          <div class="option-item">
            <span class="option-label"><File :size="14" /> 文章长度:</span>
            <select v-model="targetLength">
              <option value="mini">快速 Mini</option>
              <option value="short">短文</option>
              <option value="medium">中等</option>
              <option value="long">长文</option>
              <option value="custom">自定义</option>
            </select>
          </div>

          <!-- 受众适配 -->
          <div class="option-item">
            <span class="option-label"><Users :size="14" /> 受众适配:</span>
            <select v-model="audienceAdaptation">
              <option value="default">默认风格</option>
              <option value="high-school">高中生版</option>
              <option value="children">儿童版</option>
              <option value="professional">职场版</option>
            </select>
          </div>

          <!-- 配图风格 -->
          <div class="option-item">
            <span class="option-label"><Palette :size="14" /> 配图风格:</span>
            <select v-model="imageStyle">
              <option v-for="style in imageStyles" :key="style.id" :value="style.id">
                {{ style.icon }} {{ style.name }}
              </option>
            </select>
          </div>

          <!-- 生成封面动画 -->
          <div v-if="appConfig.features?.cover_video" class="option-item checkbox-item">
            <label>
              <input type="checkbox" v-model="generateCoverVideo">
              <Video :size="14" />
              <span>生成封面动画</span>
            </label>
            <span class="option-hint" title="将封面图转换为循环播放的动画视频（约需 2-5 分钟）">ⓘ</span>
          </div>

          <!-- 视频尺寸 -->
          <div v-if="generateCoverVideo" class="option-item">
            <span class="option-label"><Monitor :size="14" /> 视频尺寸:</span>
            <select v-model="videoAspectRatio">
              <option value="16:9">横屏(16:9)</option>
              <option value="9:16">竖屏(9:16)</option>
            </select>
          </div>
        </div>

        <!-- 自定义配置面板 -->
        <div v-if="targetLength === 'custom'" class="custom-config-panel">
          <div class="custom-config-title"><Settings :size="14" /> 自定义配置</div>
          <div class="custom-config-row">
            <div class="custom-item">
              <label>章节数:</label>
              <input type="number" v-model.number="customConfig.sectionsCount" min="1" max="12">
            </div>
            <div class="custom-item">
              <label>配图数:</label>
              <input type="number" v-model.number="customConfig.imagesCount" min="0" max="20">
            </div>
            <div class="custom-item">
              <label>代码块:</label>
              <input type="number" v-model.number="customConfig.codeBlocksCount" min="0" max="10">
            </div>
            <div class="custom-item">
              <label>目标字数:</label>
              <input type="number" v-model.number="customConfig.targetWordCount" min="300" max="15000" step="500">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 进度面板 - 底部抽屉式，放在输入框容器内 -->
    <div v-if="showProgress" class="progress-drawer" :class="{ expanded: terminalExpanded }" :style="{ height: terminalExpanded ? (terminalHeight / 2) + 'px' : 'auto' }">
      <!-- 最小化状态栏 -->
      <div class="progress-bar-mini" @click="toggleTerminal">
        <div class="progress-bar-left">
          <span class="progress-indicator" :class="{ active: isLoading }"></span>
          <span class="progress-status">{{ statusBadge }}</span>
          <span class="progress-text">{{ progressText }}</span>
        </div>
        <div class="progress-bar-right">
          <span class="progress-logs">{{ progressItems.length }} logs</span>
          <button v-if="isLoading" class="progress-stop-btn" @click.stop="stopGeneration">
            <Square :size="10" /> 中断
          </button>
          <button class="progress-toggle-btn" @click.stop="toggleTerminal">
            <ChevronRight :size="14" :class="{ 'rotate-down': terminalExpanded }" />
          </button>
          <button class="progress-close-btn" @click.stop="closeProgress">
            <X :size="14" />
          </button>
        </div>
      </div>
      
      <!-- 展开的日志内容 -->
      <div class="progress-content" :style="{ height: terminalExpanded ? (terminalHeight / 2) + 'px' : '0' }">
        <!-- 顶部拖拽边框 -->
        <div class="progress-resize-handle" @mousedown="startResizeTerminal($event, 'top')"></div>
        
        <!-- 日志内容区 -->
        <div class="progress-logs-container" ref="progressBodyRef">
          <!-- 任务启动信息 -->
          <div class="progress-task-header">
            <span class="progress-prompt">❯</span>
            <span class="progress-command">generate</span>
            <span class="progress-arg">--type</span>
            <span class="progress-value">{{ articleType }}</span>
            <span class="progress-arg">--length</span>
            <span class="progress-value">{{ targetLength }}</span>
            <span v-if="currentTaskId" class="progress-task-id">{{ currentTaskId }}</span>
          </div>
          
          <!-- 进度日志 -->
          <div class="progress-log-list">
            <div 
              v-for="(item, index) in progressItems" 
              :key="index" 
              class="progress-log-item"
              :class="item.type"
            >
              <span class="progress-log-time">{{ item.time }}</span>
              <span class="progress-log-icon" :class="item.type">{{ getLogIcon(item.type) }}</span>
              <span class="progress-log-msg" v-html="item.message"></span>
              <div v-if="item.detail" class="progress-log-detail">
                <pre>{{ item.detail }}</pre>
              </div>
            </div>
            
            <!-- 加载动画 -->
            <div v-if="isLoading" class="progress-loading-line">
              <span class="progress-spinner"></span>
              <span class="progress-loading-text">{{ progressText }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- 博客列表容器 -->
    <div class="code-cards-container" :class="{ collapsed: !showBlogList }">
      <!-- 展开/折叠按钮 -->
      <button class="blog-list-toggle" @click="showBlogList = !showBlogList">
        <ChevronDown :size="14" :class="{ 'rotate-up': showBlogList }" />
        <span>$ count: {{ historyTotal || 0 }} blogs available --sort</span>
        <Star :size="12" />
        <span>stars</span>
        <Clock :size="12" />
        <span>recent</span>
      </button>
      
      <!-- 筛选工具栏 - 仅展开时显示 -->
      <div v-show="showBlogList" class="history-toolbar">
        <div class="toolbar-left">
          <div class="code-tabs">
            <button 
              class="code-tab-btn" 
              :class="{ active: currentHistoryTab === 'blogs' }"
              @click="switchHistoryTab('blogs')"
            ><FileText :size="12" /> 博客</button>
            <button 
              class="code-tab-btn" 
              :class="{ active: currentHistoryTab === 'books' }"
              @click="switchHistoryTab('books')"
            ><Book :size="12" /> 教程</button>
          </div>
          <div v-if="currentHistoryTab === 'blogs'" class="content-type-filter">
            <button 
              v-for="filter in contentTypeFilters" 
              :key="filter.value"
              class="filter-btn"
              :class="{ active: historyContentType === filter.value }"
              @click="filterByContentType(filter.value)"
            >
              {{ filter.label }}
            </button>
          </div>
        </div>
        <div class="toolbar-right">
          <button 
            v-if="currentHistoryTab === 'books' && appConfig.features?.book_scan" 
            class="scan-books-btn"
            :disabled="isScanning"
            @click="regenerateBooks"
          >
            <Loader v-if="isScanning" :size="12" class="spin" />
            <RefreshCw v-else :size="12" />
            {{ isScanning ? '扫描中...' : '扫描' }}
          </button>
          <div 
            v-if="currentHistoryTab === 'blogs'"
            class="cover-preview-toggle"
            :class="{ active: showCoverPreview }"
            @click="showCoverPreview = !showCoverPreview"
          >
            <ImageIcon :size="12" />
            <div class="toggle-switch"></div>
          </div>
        </div>
      </div>

      <!-- 博客列表 - 代码风格卡片 -->
      <div v-show="showBlogList && currentHistoryTab === 'blogs'" class="code-cards-grid">
        <div v-if="historyRecords.length === 0" class="history-empty">
          {{ historyContentType === 'xhs' ? '暂无小红书记录，前往小红书创作助手生成' : '// 暂无历史记录，生成博客后将自动保存' }}
        </div>
        <article 
          v-for="record in historyRecords" 
          :key="record.id" 
          class="code-blog-card"
          :class="{ 'xhs-card': record.content_type === 'xhs', 'with-cover': showCoverPreview && (record.cover_video || record.cover_image) }"
          @click="loadHistoryDetail(record.id)"
        >
          <!-- 封面预览（视频优先，否则显示图片） -->
          <div v-if="showCoverPreview && (record.cover_video || record.cover_image)" class="card-cover-preview">
            <!-- 封面视频 -->
            <video 
              v-if="record.cover_video"
              :src="getVideoSrc(record.cover_video)" 
              :poster="record.cover_image ? getImageSrc(record.cover_image) : ''"
              autoplay 
              loop 
              muted 
              playsinline
              preload="auto"
              class="cover-video"
              @error="handleVideoError($event, record)"
              @loadeddata="handleVideoLoaded($event)"
            ></video>
            <!-- 封面图片（视频回退或无视频时显示） -->
            <img 
              v-if="!record.cover_video || record._videoError" 
              :src="getImageSrc(record.cover_image)" 
              :alt="record.topic" 
              loading="lazy"
              :style="{ display: record.cover_video && !record._videoError ? 'none' : 'block' }"
            />
            <div class="cover-overlay">
              <span class="cover-badge" :class="{ video: record.cover_video && !record._videoError }">{{ record.cover_video && !record._videoError ? 'VIDEO' : 'COVER' }}</span>
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
          
          <!-- 卡片主体 - 代码风格 -->
          <div class="code-card-body">
            <div class="code-line">
              <span class="code-line-number">1</span>
              <div class="code-line-content">
                <span class="code-keyword">export</span>
                <span 
                  class="code-blog-title"
                  @click.stop
                  @dblclick.stop="copyToClipboard(record.topic)"
                  :title="'双击复制: ' + record.topic"
                >{{ record.topic }}</span>
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
                <span class="code-comment">// {{ record.content_type === 'xhs' ? '小红书图文内容，适合社交媒体分享' : '深度技术教程，包含完整代码示例' }}</span>
              </div>
            </div>
            <div class="code-line">
              <span class="code-line-number">4</span>
              <div class="code-line-content">
                <span class="code-comment">// {{ record.content_type === 'xhs' ? '支持一键发布到小红书平台' : '支持 Markdown 导出和平台发布' }}</span>
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
                <span v-if="record.review_score" class="code-tag tag-score"><Star :size="10" /> {{ record.review_score }}</span>
              </template>
              <!-- 视频图标 -->
              <span v-if="record.cover_video" class="code-tag tag-video" title="有封面视频"><Video :size="10" /></span>
              <span v-if="record.book_title" class="code-tag tag-book" @click.stop="openBook(record.book_id)"><Book :size="10" /></span>
            </div>
            <span class="code-card-date">{{ formatRelativeTime(record.created_at) }}</span>
          </div>
          
          <!-- 悬停箭头 -->
          <div class="code-card-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
          
          <!-- 删除按钮（隐藏）
          <button class="code-card-delete" @click.stop="deleteHistoryRecord(record.id)" title="删除"><X :size="12" /></button>
          -->
          
          <!-- 转小红书按钮 -->
          <button v-if="record.content_type !== 'xhs'" class="code-card-action" @click.stop="openToXhs(record)"><ChevronRight :size="12" /> XHS</button>
        </article>
      </div>

      <!-- 分页 -->
      <div v-show="showBlogList && currentHistoryTab === 'blogs' && historyTotalPages > 1" class="history-pagination">
        <button :disabled="historyCurrentPage <= 1" @click="loadHistory(historyCurrentPage - 1)">« 上一页</button>
        <template v-for="page in paginationPages" :key="page">
          <span v-if="page === '...'" class="page-info">...</span>
          <button v-else :class="{ active: page === historyCurrentPage }" @click="loadHistory(page)">{{ page }}</button>
        </template>
        <button :disabled="historyCurrentPage >= historyTotalPages" @click="loadHistory(historyCurrentPage + 1)">下一页 »</button>
        <span class="page-info">{{ historyCurrentPage }} / {{ historyTotalPages }} 页</span>
      </div>

      <!-- 书籍列表 -->
      <div v-show="showBlogList && currentHistoryTab === 'books'" class="books-grid">
        <div v-if="books.length === 0" class="history-empty">暂无教程书籍，点击「扫描聚合」自动生成</div>
        <div 
          v-for="book in books" 
          :key="book.id" 
          class="book-card"
          @click="openBook(book.id)"
        >
          <div class="book-cover">
            <img v-if="book.cover_image" :src="book.cover_image" :alt="book.title">
            <div v-else class="book-cover-default" :class="`theme-${book.theme || 'general'}`">
              <span class="book-icon">{{ getThemeIcon(book.theme) }}</span>
              <span class="book-title-inner">{{ book.title }}</span>
            </div>
          </div>
          <div class="book-title">{{ book.title }}</div>
          <div class="book-stats">
            <span>{{ book.chapters_count || 0 }}章</span>
            <span>{{ formatWordCount(book.total_word_count || 0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 发布弹窗 -->
    <div v-if="showPublishModal" class="publish-modal" @click.self="showPublishModal = false">
      <div class="publish-modal-content">
        <div class="publish-modal-header">
          <h2><Rocket :size="18" /> 发布到平台</h2>
          <button @click="showPublishModal = false"><X :size="16" /></button>
        </div>
        <div class="publish-form">
          <div class="form-item">
            <label>选择平台</label>
            <select v-model="publishPlatform">
              <option value="csdn">CSDN</option>
              <option value="zhihu">知乎</option>
              <option value="juejin">掘金</option>
            </select>
          </div>
          <div class="form-item">
            <label>Cookie <a href="javascript:void(0)" @click="showCookieHelp = !showCookieHelp">如何获取？</a></label>
            <textarea v-model="publishCookie" placeholder="直接粘贴浏览器复制的 Cookie，如：name=value; name2=value2; ..."></textarea>
            <div class="cookie-warning">
              ⚠️ <strong>安全提示：</strong>服务端不会存储您的 Cookie，仅用于本次发布。
            </div>
          </div>
          <div v-if="showCookieHelp" class="cookie-help">
            <strong>获取 Cookie 步骤：</strong><br>
            1. 在浏览器登录目标平台（如 CSDN）<br>
            2. 按 F12 打开开发者工具<br>
            3. 切换到 Application → Cookies<br>
            4. 选择对应域名，复制所有 Cookie
          </div>
          <button class="publish-submit-btn" :disabled="isPublishing" @click="doPublish">
            <Loader v-if="isPublishing" :size="14" class="spin" />
            <Rocket v-else :size="14" />
            {{ isPublishing ? '发布中...' : '立即发布' }}
          </button>
          <div v-if="publishStatus" class="publish-status" :class="publishStatusType">{{ publishStatus }}</div>
        </div>
      </div>
    </div>

    <!-- 底部备案信息 -->
    <Footer />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import hljs from 'highlight.js'
import * as api from '../services/api'
import { formatFileSize, formatWordCount, getStatusText, isSpinningStatus, getStageIcon, formatTime } from '../utils/helpers'
import { useThemeStore } from '../stores/theme'
import Footer from '../components/Footer.vue'
import {
  Sun, Moon, BookOpen, Search, FileText, File, Users, Palette, Video, Monitor,
  Camera, Download, Rocket, Code, Image as ImageIcon, Star, Clock, Book, RefreshCw, Loader,
  FileCheck, X, Square, ChevronRight, ChevronDown, Zap, Settings, Target, Briefcase, Baby
} from 'lucide-vue-next'

const router = useRouter()
const themeStore = useThemeStore()

// ========== 应用配置 ==========
const appConfig = reactive<{ features: Record<string, boolean> }>({ features: {} })

// ========== 输入状态 ==========
const topic = ref('')
const showUploadTooltip = ref(false)
const showAdvancedOptions = ref(false)
const searchQuery = ref('')
const sortBy = ref('recent')
const isDarkMode = computed(() => themeStore.isDark)

// 主题切换
const toggleTheme = () => {
  themeStore.toggleTheme()
}

// ========== 高级选项 ==========
const articleType = ref('tutorial')
const targetLength = ref('mini')
const audienceAdaptation = ref('default')
const imageStyle = ref('cartoon')
const generateCoverVideo = ref(false)
const videoAspectRatio = ref('16:9')
const imageStyles = ref<Array<{ id: string; name: string; icon: string }>>([{ id: '', name: '默认风格', icon: '🎨' }])
const customConfig = reactive({
  sectionsCount: 4,
  imagesCount: 4,
  codeBlocksCount: 2,
  targetWordCount: 3500
})

// ========== 文档上传 ==========
interface UploadedDocument {
  id: string
  filename: string
  status: string
  fileSize?: number
  wordCount?: number
  errorMessage?: string
}
const uploadedDocuments = ref<UploadedDocument[]>([])

// ========== 生成状态 ==========
const isLoading = ref(false)
const showProgress = ref(false)
const terminalExpanded = ref(true)

// 终端窗口大小调整
const TERMINAL_SIZE_KEY = 'vibe-blog-terminal-size'
const savedTerminalSize = JSON.parse(localStorage.getItem(TERMINAL_SIZE_KEY) || '{}')
const terminalWidth = ref(savedTerminalSize.width || 500)
const terminalHeight = ref(savedTerminalSize.height || 600)
const isResizingTerminal = ref(false)
let resizeDirection = ''
let resizeStartX = 0
let resizeStartY = 0
let resizeStartWidth = 0
let resizeStartHeight = 0

const startResizeTerminal = (e: MouseEvent, direction: string) => {
  e.preventDefault()
  isResizingTerminal.value = true
  resizeDirection = direction
  resizeStartX = e.clientX
  resizeStartY = e.clientY
  resizeStartWidth = terminalWidth.value
  resizeStartHeight = terminalHeight.value
  
  document.addEventListener('mousemove', onResizeTerminal)
  document.addEventListener('mouseup', stopResizeTerminal)
}

const onResizeTerminal = (e: MouseEvent) => {
  if (!isResizingTerminal.value) return
  
  const deltaX = resizeStartX - e.clientX
  const deltaY = e.clientY - resizeStartY
  
  // 根据拖拽方向调整大小
  if (resizeDirection.includes('left') || resizeDirection.includes('corner')) {
    const newWidth = Math.max(300, Math.min(1000, resizeStartWidth + deltaX))
    terminalWidth.value = newWidth
  }
  if (resizeDirection.includes('top') || resizeDirection === 'corner-top-left') {
    const newHeight = Math.max(300, Math.min(900, resizeStartHeight - deltaY))
    terminalHeight.value = newHeight
  }
  if (resizeDirection.includes('bottom') || resizeDirection === 'corner-bottom-left') {
    const newHeight = Math.max(300, Math.min(900, resizeStartHeight + deltaY))
    terminalHeight.value = newHeight
  }
}

const stopResizeTerminal = () => {
  isResizingTerminal.value = false
  document.removeEventListener('mousemove', onResizeTerminal)
  document.removeEventListener('mouseup', stopResizeTerminal)
  
  // 保存到 localStorage
  localStorage.setItem(TERMINAL_SIZE_KEY, JSON.stringify({
    width: terminalWidth.value,
    height: terminalHeight.value
  }))
}

const toggleTerminal = () => {
  console.log('Toggle terminal clicked, current state:', terminalExpanded.value)
  terminalExpanded.value = !terminalExpanded.value
}
const showResult = ref(false)
const currentTaskId = ref<string | null>(null)
let eventSource: EventSource | null = null

// ========== 进度面板 ==========
interface ProgressItem {
  time: string
  message: string
  type: string
  detail?: string
}
const progressItems = ref<ProgressItem[]>([])
const statusBadge = ref('准备中')
const progressText = ref('等待开始')
const progressBodyRef = ref<HTMLElement | null>(null)

// ========== 结果 ==========
interface BlogResult {
  markdown?: string
  outline?: { title?: string }
  sections_count?: number
  code_blocks_count?: number
  images_count?: number
  review_score?: number
  cover_video?: string
  cover_image?: string
  saved_path?: string
}
const currentResult = ref<BlogResult | null>(null)
const renderedMarkdown = ref('')
const markdownContentRef = ref<HTMLElement | null>(null)

// ========== 历史记录 ==========
const currentHistoryTab = ref('blogs')
const historyRecords = ref<api.HistoryRecord[]>([])
const historyCurrentPage = ref(1)
const historyPageSize = ref(9)
const historyTotalPages = ref(1)
const historyTotal = ref(0)
const historyContentType = ref('all')
const showCoverPreview = ref(false)
const showBlogList = ref(true) // 默认打开博客列表
const contentTypeFilters = [
  { value: 'all', label: '全部' },
  { value: 'blog', label: '📝 博客' },
  { value: 'xhs', label: '📕 小红书' }
]

// ========== 书籍列表 ==========
const books = ref<api.Book[]>([])
const isScanning = ref(false)

// ========== 发布弹窗 ==========
const showPublishModal = ref(false)
const publishPlatform = ref('csdn')
const publishCookie = ref('')
const showCookieHelp = ref(false)
const isPublishing = ref(false)
const publishStatus = ref('')
const publishStatusType = ref('')

// ========== 示例数据 ==========
const examples = [
  { icon: '🏪', title: 'Redis 入门', desc: '用便利店的比喻，让你秒懂 Redis 缓存原理', content: 'Redis 是一个开源的、基于内存的数据结构存储系统...' },
  { icon: '📦', title: '消息队列原理', desc: '快递驿站的故事，理解消息队列的异步魔法', content: '消息队列是一种应用程序间的通信方法...' },
  { icon: '🔒', title: '分布式锁详解', desc: '公共厕所的锁，秒懂分布式锁的精髓', content: '分布式锁是控制分布式系统之间同步访问共享资源的一种方式...' }
]

// ========== 主题图标 ==========
const themeIcons: Record<string, string> = {
  ai: '🤖', web: '🌐', data: '📊', devops: '⚙️', security: '🔐', general: '📖'
}

// ========== 计算属性 ==========
const paginationPages = computed(() => {
  const pages: (number | string)[] = []
  const maxVisible = 5
  let start = Math.max(1, historyCurrentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(historyTotalPages.value, start + maxVisible - 1)
  if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1)
  
  if (start > 1) { pages.push(1); if (start > 2) pages.push('...') }
  for (let i = start; i <= end; i++) pages.push(i)
  if (end < historyTotalPages.value) { if (end < historyTotalPages.value - 1) pages.push('...'); pages.push(historyTotalPages.value) }
  return pages
})

// ========== 工具函数 ==========
const truncateFilename = (name: string) => name.length > 20 ? name.substring(0, 18) + '...' : name
const getFileExt = (name: string) => name.split('.').pop()?.toUpperCase() || 'FILE'
const getThemeIcon = (theme?: string) => themeIcons[theme || 'general'] || '📖'

const getVideoSrc = (url: string) => {
  if (url.startsWith('http')) return url
  if (url.startsWith('/')) return url
  return `/outputs/videos/${url.split('/').pop()}`
}

const getImageSrc = (url: string) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `/outputs/images/${url.split('/').pop()}`
}

// 视频错误处理 - 回退到图片
const handleVideoError = (event: Event, record: api.HistoryRecord) => {
  const video = event.target as HTMLVideoElement
  video.style.display = 'none'
  // 标记视频加载失败，触发图片显示
  ;(record as any)._videoError = true
}

// 视频加载成功 - 尝试播放
const handleVideoLoaded = (event: Event) => {
  const video = event.target as HTMLVideoElement
  video.play().catch(() => {
    // 自动播放失败时静默处理
  })
}

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

// ========== 文档上传 ==========
const handleFileUpload = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  
  for (const file of Array.from(files)) {
    await uploadDocument(file)
  }
  input.value = ''
}

const uploadDocument = async (file: File) => {
  const tempId = 'temp_' + Date.now()
  uploadedDocuments.value.push({ id: tempId, filename: file.name, status: 'uploading', fileSize: file.size })
  
  try {
    const data = await api.uploadDocument(file)
    uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== tempId)
    
    if (data.success && data.document_id) {
      uploadedDocuments.value.push({
        id: data.document_id,
        filename: data.filename || file.name,
        status: data.status || 'pending',
        fileSize: file.size
      })
      pollDocumentStatus(data.document_id)
    } else {
      alert('上传失败: ' + (data.error || '未知错误'))
    }
  } catch (error: any) {
    uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== tempId)
    alert('上传失败: ' + error.message)
  }
}

const pollDocumentStatus = async (docId: string) => {
  let attempts = 0
  const maxAttempts = 60
  
  const poll = async () => {
    if (attempts >= maxAttempts) {
      updateDocStatus(docId, 'timeout')
      return
    }
    
    try {
      const data = await api.getDocumentStatus(docId)
      if (data.success) {
        updateDocStatus(docId, data.status || 'pending', data.markdown_length, data.error_message)
        if (data.status === 'ready' || data.status === 'error') return
      }
    } catch (e) {
      console.error('轮询文档状态失败:', e)
    }
    
    attempts++
    setTimeout(poll, 2000)
  }
  poll()
}

const updateDocStatus = (docId: string, status: string, wordCount?: number, errorMessage?: string) => {
  const doc = uploadedDocuments.value.find(d => d.id === docId)
  if (doc) {
    doc.status = status
    if (wordCount) doc.wordCount = wordCount
    if (errorMessage) doc.errorMessage = errorMessage
  }
}

const removeDocument = (docId: string) => {
  uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== docId)
}

const getReadyDocumentIds = () => uploadedDocuments.value.filter(d => d.status === 'ready').map(d => d.id)

// ========== 生成博客 ==========
const handleGenerate = async () => {
  if (!topic.value.trim() || isLoading.value) return
  
  isLoading.value = true
  showProgress.value = true
  showResult.value = false
  progressItems.value = []
  statusBadge.value = '准备中'
  
  const isStorybook = articleType.value === 'storybook'
  const isMini = targetLength.value === 'mini'
  const taskName = isStorybook ? '科普绘本' : (isMini ? 'Mini 博客' : '博客')
  progressText.value = `正在创建${taskName}生成任务...`
  
  try {
    let data: { success: boolean; task_id?: string; error?: string }
    
    if (isStorybook) {
      data = await api.createStorybookTask({
        content: topic.value,
        page_count: targetLength.value === 'short' ? 5 : (targetLength.value === 'medium' ? 8 : 12),
        target_audience: '技术小白',
        style: '可爱卡通风',
        generate_images: true
      })
    } else if (isMini) {
      data = await api.createMiniBlogTask({
        topic: topic.value,
        article_type: articleType.value,
        audience_adaptation: audienceAdaptation.value,
        image_style: imageStyle.value,
        generate_cover_video: generateCoverVideo.value,
        video_aspect_ratio: videoAspectRatio.value
      })
    } else {
      data = await api.createBlogTask({
        topic: topic.value,
        article_type: articleType.value,
        target_audience: 'intermediate',
        audience_adaptation: audienceAdaptation.value,
        target_length: targetLength.value,
        document_ids: getReadyDocumentIds(),
        image_style: imageStyle.value,
        generate_cover_video: generateCoverVideo.value,
        video_aspect_ratio: videoAspectRatio.value,
        custom_config: targetLength.value === 'custom' ? {
          sections_count: customConfig.sectionsCount,
          images_count: customConfig.imagesCount,
          code_blocks_count: customConfig.codeBlocksCount,
          target_word_count: customConfig.targetWordCount
        } : undefined
      })
    }
    
    if (!data.success || !data.task_id) {
      addProgressItem(`❌ 创建任务失败: ${data.error}`, 'error')
      isLoading.value = false
      return
    }
    
    currentTaskId.value = data.task_id
    addProgressItem(`✅ ${taskName}生成任务已创建: ${data.task_id}`)
    connectSSE(data.task_id, isStorybook)
    
  } catch (error: any) {
    addProgressItem(`❌ 请求失败: ${error.message}`, 'error')
    isLoading.value = false
  }
}

const connectSSE = (taskId: string, isStorybook: boolean) => {
  eventSource = api.createTaskStream(taskId)
  
  eventSource.addEventListener('connected', () => {
    addProgressItem('🔗 已连接到服务器')
    statusBadge.value = '运行中'
  })
  
  eventSource.addEventListener('progress', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    const icon = getStageIcon(d.stage)
    addProgressItem(`${icon} ${d.message}`, d.stage === 'error' ? 'error' : 'info')
    progressText.value = d.message
  })
  
  eventSource.addEventListener('log', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    let icon = '📝'
    const loggerIcons: Record<string, string> = {
      generator: '⚙️', researcher: '🔍', planner: '📋', writer: '✍️',
      questioner: '❓', coder: '💻', artist: '🎨', reviewer: '✅',
      assembler: '📦', search_service: '🌐', blog_service: '🖼️'
    }
    icon = loggerIcons[d.logger] || icon
    const isSuccess = d.message?.includes('完成') || d.message?.includes('成功')
    addProgressItem(`${icon} ${d.message}`, isSuccess ? 'success' : 'info')
    progressText.value = d.message
  })
  
  eventSource.addEventListener('stream', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    if (d.stage === 'outline') updateStreamItem(d.accumulated)
  })
  
  eventSource.addEventListener('result', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    if (d.type === 'researcher_complete') {
      const data = d.data
      if (data.document_count > 0 || data.web_count > 0) {
        addProgressItem(`📊 知识来源: 文档 ${data.document_count} 条, 网络 ${data.web_count} 条`, 'info')
      }
      if (data.key_concepts?.length > 0) {
        addProgressItem(`💡 核心概念: ${data.key_concepts.join(', ')}`, 'success')
      }
    }
  })
  
  eventSource.addEventListener('complete', (e: MessageEvent) => {
    const d = JSON.parse(e.data)
    addProgressItem(`🎉 生成完成！`, 'success')
    statusBadge.value = '已完成'
    progressText.value = '生成完成'
    isLoading.value = false
    
    loadHistory()
    eventSource?.close()
    eventSource = null
    
    // 延迟 1 秒后跳转到博客详情页
    setTimeout(() => {
      if (d.id) {
        router.push(`/blog/${d.id}`)
      } else if (d.book_id) {
        router.push(`/book/${d.book_id}`)
      }
    }, 1000)
  })
  
  eventSource.addEventListener('error', (e: MessageEvent) => {
    if (e.data) {
      const d = JSON.parse(e.data)
      addProgressItem(`❌ 错误: ${d.message}`, 'error')
    }
    statusBadge.value = '错误'
    isLoading.value = false
  })
  
  eventSource.onerror = () => {
    if (eventSource?.readyState === EventSource.CLOSED) {
      addProgressItem('🔌 连接已关闭')
      isLoading.value = false
    }
  }
}

const addProgressItem = (message: string, type = 'info', detail?: string) => {
  progressItems.value.push({ time: formatTime(), message, type, detail })
  nextTick(() => {
    if (progressBodyRef.value) progressBodyRef.value.scrollTop = progressBodyRef.value.scrollHeight
  })
}

// Claude 终端风格辅助函数
const getLogIcon = (type: string) => {
  const icons: Record<string, string> = {
    'info': '○',
    'success': '✓',
    'error': '✗',
    'stream': '◐',
    'warning': '⚠'
  }
  return icons[type] || '○'
}

const statusBadgeClass = computed(() => {
  if (statusBadge.value === '已完成') return 'success'
  if (statusBadge.value === '错误') return 'error'
  if (statusBadge.value === '运行中') return 'running'
  return 'pending'
})

const updateStreamItem = (content: string) => {
  const lastItem = progressItems.value[progressItems.value.length - 1]
  if (lastItem?.type === 'stream') {
    lastItem.detail = content
  } else {
    addProgressItem('📝 大纲生成中...', 'stream', content)
  }
}

const stopGeneration = async () => {
  if (currentTaskId.value) {
    try {
      const data = await api.cancelTask(currentTaskId.value)
      if (data.success) {
        addProgressItem('⏹️ 任务已取消', 'error')
      } else {
        addProgressItem(`⚠️ 取消失败: ${data.error}`, 'error')
      }
    } catch (e: any) {
      addProgressItem('⚠️ 取消请求失败', 'error')
    }
  }
  
  eventSource?.close()
  eventSource = null
  statusBadge.value = '已停止'
  isLoading.value = false
}

const closeProgress = () => {
  showProgress.value = false
  eventSource?.close()
  eventSource = null
}

// ========== 复制到粘贴板 ==========
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    // 显示复制成功提示
    const notification = document.createElement('div')
    notification.textContent = '✓ 已复制'
    notification.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(34, 197, 94, 0.9);
      color: white;
      padding: 12px 24px;
      border-radius: 6px;
      font-size: 14px;
      z-index: 9999;
      pointer-events: none;
      animation: fadeInOut 1.5s ease-in-out;
    `
    document.body.appendChild(notification)
    setTimeout(() => notification.remove(), 1500)
  } catch (err) {
    console.error('复制失败:', err)
  }
}

// ========== 显示结果 ==========
const displayBlogResult = (result: BlogResult) => {
  currentResult.value = result
  showResult.value = true
  
  if (result.markdown) {
    renderMarkdownContent(result.markdown)
  }
  
  if (result.saved_path) {
    addProgressItem(`📁 已自动保存到: ${result.saved_path}`, 'success')
  }
  
  nextTick(() => {
    document.querySelector('.result-section')?.scrollIntoView({ behavior: 'smooth' })
  })
}

const displayStorybookResult = (outputs: any) => {
  currentResult.value = {
    outline: { title: outputs.title || '技术科普绘本' },
    sections_count: outputs.total_pages || 0
  }
  showResult.value = true
}

const renderMarkdownContent = (markdown: string) => {
  let processed = markdown.replace(/\]\(\.\/images\//g, '](/outputs/images/')
  processed = processed.replace(/^(-{3,})$/gm, '\n$1\n')
  processed = processed.replace(/^(-{3,})([#])/gm, '$1\n\n$2')
  
  marked.setOptions({
    highlight: (code: string, lang: string) => {
      if (lang && hljs.getLanguage(lang)) {
        try { return hljs.highlight(code, { language: lang }).value } catch (e) {}
      }
      return code
    },
    breaks: true,
    gfm: true
  })
  
  renderedMarkdown.value = marked.parse(processed) as string
}

// ========== 下载和导出 ==========
const downloadCoverVideo = async () => {
  if (!currentResult.value?.cover_video) return
  const videoSrc = getVideoSrc(currentResult.value.cover_video)
  const title = currentResult.value?.outline?.title || 'cover'
  const safeTitle = title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').substring(0, 50)
  const filename = `${safeTitle}_封面动画_${new Date().toISOString().slice(0, 10)}.mp4`
  
  try {
    const response = await fetch(videoSrc)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    alert('下载视频失败: ' + error.message)
  }
}

const downloadMarkdown = async () => {
  if (!currentResult.value?.markdown) {
    alert('没有可下载的内容')
    return
  }
  
  const title = currentResult.value.outline?.title || 'blog'
  const safeTitle = title.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_').substring(0, 50)
  
  try {
    const response = await fetch('/api/export/markdown', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: currentResult.value.markdown, title })
    })
    
    if (!response.ok) {
        const errorData = await response.json()
      throw new Error(errorData.error || '导出失败')
    }
    
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${safeTitle}_${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    alert('下载失败: ' + error.message)
  }
}

const exportMarkdownAsImage = async () => {
  alert('导出图片功能需要安装 html2canvas 库')
}

const exportProgressAsImage = async () => {
  alert('导出进度图片功能需要安装 html2canvas 库')
}

// ========== 历史记录 ==========
const loadHistory = async (page = 1) => {
  try {
    const data = await api.getHistory({
      page,
      page_size: historyPageSize.value,
      content_type: historyContentType.value
    })
    
    if (data.success) {
      historyRecords.value = data.records
      historyCurrentPage.value = data.page
      historyTotalPages.value = data.total_pages
      historyTotal.value = data.total
    }
  } catch (error) {
    console.error('加载历史记录失败:', error)
  }
}

const loadHistoryDetail = async (historyId: string) => {
  try {
    const data = await api.getHistoryRecord(historyId)
    if (data.success && data.record) {
      const record = data.record
      
      if (record.content_type === 'xhs') {
        router.push(`/xhs?history_id=${historyId}`)
        return
      }
      
      // 跳转到博客详情页
      router.push(`/blog/${historyId}`)
    }
  } catch (error) {
    console.error('加载历史详情失败:', error)
    alert('加载历史记录失败')
  }
}

const deleteHistoryRecord = async (historyId: string) => {
  if (!confirm('确定要删除这条历史记录吗？')) return
  
  try {
    const data = await api.deleteHistory(historyId)
    if (data.success) {
      const currentRecords = historyRecords.value.length
      if (currentRecords <= 1 && historyCurrentPage.value > 1) {
        loadHistory(historyCurrentPage.value - 1)
      } else {
        loadHistory(historyCurrentPage.value)
      }
    } else {
      alert('删除失败: ' + data.error)
    }
  } catch (error) {
    console.error('删除历史记录失败:', error)
    alert('删除失败')
  }
}

const filterByContentType = (type: string) => {
  historyContentType.value = type
  historyCurrentPage.value = 1
  loadHistory(1)
}

const switchHistoryTab = (tab: string) => {
  currentHistoryTab.value = tab
  if (tab === 'books') loadBooks()
}

// ========== 书籍列表 ==========
const loadBooks = async () => {
  try {
    const data = await api.getBooks()
    if (data.success && data.books) {
      books.value = data.books
    }
  } catch (error) {
    console.error('加载书籍失败:', error)
  }
}

const regenerateBooks = async () => {
  isScanning.value = true
  try {
    const data = await api.regenerateBooks()
    if (data.success) {
      alert(`扫描完成！`)
      loadBooks()
    } else {
      alert('扫描失败: ' + (data.error || '未知错误'))
    }
  } catch (error: any) {
    alert('扫描失败: ' + error.message)
  } finally {
    isScanning.value = false
  }
}

const openBook = (bookId: string) => {
  router.push(`/book/${bookId}`)
}

const openToXhs = (record: api.HistoryRecord) => {
  router.push(`/xhs?topic=${encodeURIComponent(record.topic)}&source_id=${record.id}`)
}

// ========== 示例 ==========
const useExample = (example: { content: string }) => {
  topic.value = example.content
  document.querySelector('.main-card')?.scrollIntoView({ behavior: 'smooth' })
}

// ========== 发布 ==========
const doPublish = async () => {
  if (!publishCookie.value.trim()) {
    alert('请输入 Cookie')
    return
  }
  
  if (!currentResult.value?.markdown) {
    alert('没有可发布的内容')
    return
  }
  
  let cookies: Array<{ name: string; value: string; domain: string }>
  try {
    cookies = JSON.parse(publishCookie.value)
    if (!Array.isArray(cookies)) throw new Error('not array')
  } catch (e) {
    const domainMap: Record<string, string> = { csdn: '.csdn.net', zhihu: '.zhihu.com', juejin: '.juejin.cn' }
    const domain = domainMap[publishPlatform.value] || '.csdn.net'
    cookies = publishCookie.value.split(';').map(pair => {
      const [name, ...rest] = pair.trim().split('=')
      return { name: name?.trim() || '', value: rest.join('=')?.trim() || '', domain }
    }).filter(c => c.name)
  }
  
  if (cookies.length === 0) {
    alert('Cookie 格式错误')
    return
  }
  
  isPublishing.value = true
  publishStatus.value = '⏳ 正在发布，请稍候...'
  publishStatusType.value = ''
  
  try {
    const response = await fetch('/api/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: publishPlatform.value,
        cookies,
        title: currentResult.value.outline?.title || '未命名博客',
        content: currentResult.value.markdown
      })
    })
    
    const data = await response.json()
    
    if (data.success) {
      publishStatusType.value = 'success'
      publishStatus.value = data.url ? `✅ 发布成功！` : '✅ 发布成功！（请到平台查看）'
    } else {
      publishStatusType.value = 'error'
      publishStatus.value = '❌ ' + (data.message || '发布失败')
    }
  } catch (error: any) {
    publishStatusType.value = 'error'
    publishStatus.value = '❌ 发布失败: ' + error.message
  } finally {
    isPublishing.value = false
  }
}

// ========== 初始化 ==========
const loadAppConfig = async () => {
  try {
    const data = await api.getFrontendConfig()
    if (data.success && data.config) {
      Object.assign(appConfig, data.config)
    }
  } catch (e) {
    console.warn('加载配置失败:', e)
  }
}

const loadImageStyles = async () => {
  try {
    const data = await api.getImageStyles()
    if (data.success && data.styles) {
      imageStyles.value = data.styles.map(s => ({ id: (s as any).id || s.value, name: (s as any).name || s.label, icon: (s as any).icon || '🎨' }))
    }
  } catch (error) {
    console.error('加载图片风格列表失败:', error)
  }
}

onMounted(async () => {
  await loadAppConfig()
  loadHistory()
  loadImageStyles()
  
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('tab') === 'books') {
    switchHistoryTab('books')
  }
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS 变量 - 浅色主题 */
.home-container {
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
  --glass-bg: rgba(255, 255, 255, 0.85);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  font-family: 'JetBrains Mono', monospace;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: var(--code-text);
}

/* 深色主题 */
.home-container.dark-mode {
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
  --code-comment: #64748b;
  --code-function: #60a5fa;
  --code-variable: #f472b6;
  --glass-bg: rgba(15, 23, 42, 0.9);
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}
.home-container.dark-mode .navbar {
  background: rgba(15, 23, 42, 0.9);
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

.bg-animation {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
}
.bg-animation::before {
  content: '';
  position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
  background: radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%);
  animation: bgMove 20s ease-in-out infinite;
}
@keyframes bgMove {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-1%, 3%); }
}

/* 导航栏 */
.navbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 40px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  position: sticky; 
  top: 0; 
  z-index: 1001;
}
.logo {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px; font-weight: 700;
  background: linear-gradient(135deg, #8b5cf6, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
.nav-actions { display: flex; align-items: center; gap: 12px; }
.nav-link {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 20px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  color: var(--code-text-secondary);
  text-decoration: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.nav-link:hover {
  background: var(--code-surface-hover);
  color: var(--code-text);
  border-color: var(--code-keyword);
}
.nav-link svg { flex-shrink: 0; }
.theme-toggle {
  width: 40px; height: 40px; border-radius: 10px;
  border: 1px solid var(--code-border);
  background: var(--code-surface);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--code-text-secondary);
  transition: all 0.2s;
}
.theme-toggle:hover { 
  background: var(--code-surface-hover); 
  color: var(--code-keyword);
  border-color: var(--code-keyword);
}

/* 终端导航栏 */
.nav-tabs { display: flex; gap: 8px; }
.tab {
  padding: 8px 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  color: var(--code-text-secondary);
  font-size: 12px; cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-fast);
}
.tab:hover {
  background: var(--code-surface-hover);
  border-color: var(--code-keyword);
  transform: translateY(-1px);
}
.tab.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: var(--code-keyword);
  color: var(--code-keyword);
}

/* Hero 区域 */
.hero { text-align: center; padding: 60px 20px 40px; }
.hero h1 {
  font-family: 'JetBrains Mono', monospace;
  font-size: 36px; font-weight: 700; margin-bottom: 12px;
  color: var(--code-text);
}
.hero h1 .cursor {
  display: inline-block;
  width: 3px; height: 36px;
  background: #8b5cf6;
  margin-left: 4px;
  animation: blink 1s infinite;
  vertical-align: middle;
}
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
.hero p {
  font-size: 16px;
  color: var(--code-text-secondary);
  font-family: 'JetBrains Mono', monospace;
}

/* 输入框卡片 */
.code-input-card {
  position: relative;
  width: 100%;
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
  box-sizing: border-box;
}

/* Code Style 粒子背景 */
.particles-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.code-particle {
  position: absolute;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  opacity: 0.08;
  animation: code-float 12s ease-in-out infinite;
}

.code-particle.cp1 {
  font-size: 28px;
  color: var(--code-keyword);
  top: 15%;
  right: 8%;
  animation-delay: 0s;
}

.code-particle.cp2 {
  font-size: 24px;
  color: var(--code-string);
  top: 55%;
  right: 12%;
  animation-delay: -2s;
}

.code-particle.cp3 {
  font-size: 20px;
  color: var(--code-function);
  top: 30%;
  right: 22%;
  animation-delay: -4s;
}

.code-particle.cp4 {
  font-size: 18px;
  color: var(--code-number);
  top: 70%;
  right: 5%;
  animation-delay: -6s;
}

.code-particle.cp5 {
  font-size: 22px;
  color: var(--code-keyword);
  top: 45%;
  right: 28%;
  animation-delay: -8s;
}

.code-particle.cp6 {
  font-size: 16px;
  color: var(--code-comment);
  top: 20%;
  right: 35%;
  animation-delay: -3s;
}

.code-particle.cp7 {
  font-size: 20px;
  color: var(--code-string);
  top: 75%;
  right: 20%;
  animation-delay: -5s;
}

.code-particle.cp8 {
  font-size: 18px;
  color: var(--code-function);
  top: 10%;
  right: 18%;
  animation-delay: -7s;
}

@keyframes code-float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.06;
  }
  50% {
    transform: translateY(-8px) rotate(3deg);
    opacity: 0.12;
  }
}

.code-input-header,
.code-input-body,
.code-input-footer,
.code-input-docs {
  position: relative;
  z-index: 1;
}
.code-input-header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);
}
.code-input-body {
  padding: 16px 20px;
}
.code-input-prompt {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
}
.code-prompt { color: var(--code-string); font-weight: 600; }
.code-command { color: var(--code-keyword); }
.code-input-textarea {
  width: 100%; min-height: 80px;
  padding: 12px 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px; line-height: 1.6;
  color: var(--code-text);
  resize: none; outline: none;
  transition: all 0.2s;
}
.code-input-textarea:focus {
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}
.code-input-textarea::placeholder { color: var(--code-text-muted); }
.code-input-docs {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 12px 20px 0;
}
.code-doc-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 6px;
  font-size: 12px; color: var(--code-text-secondary);
}
.code-doc-tag.doc-ready { border-color: var(--code-string); }
.code-doc-tag.doc-error { border-color: #ef4444; }
.code-doc-tag .doc-remove {
  background: none; border: none; color: var(--code-text-muted);
  cursor: pointer; font-size: 14px; padding: 0 2px;
}
.code-doc-tag .doc-remove:hover { color: #ef4444; }
.code-input-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px;
  background: var(--code-surface);
  border-top: 1px solid var(--code-border);
}
.code-input-actions-left {
  display: flex; align-items: center; gap: 8px;
  position: relative;
}
.code-action-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--code-border);
  border-radius: 6px;
  color: var(--code-text-secondary);
  font-size: 12px; cursor: pointer;
  transition: all 0.2s;
}
.code-action-btn:hover {
  border-color: var(--code-keyword);
  color: var(--code-keyword);
}
.code-action-btn.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: var(--code-keyword);
  color: var(--code-keyword);
}
.code-action-btn input[type="file"] { display: none; }
.code-input-actions-right {
  display: flex; align-items: center; gap: 12px;
}
.code-input-hint {
  font-size: 11px;
  color: var(--code-text-muted);
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}
.code-generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--code-border);
  border-radius: 6px;
  color: var(--code-text-secondary);
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.code-generate-btn:hover:not(:disabled) {
  border-color: var(--code-keyword);
  color: var(--code-keyword);
  background: rgba(139, 92, 246, 0.05);
}
.code-generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.code-generate-btn .btn-text {
  font-weight: 500;
}
.code-generate-btn svg {
  flex-shrink: 0;
  color: var(--code-keyword);
}
.loading-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 终端通用样式 */
.terminal-dots { display: flex; gap: 6px; }
.terminal-dot { width: 12px; height: 12px; border-radius: 50%; }
.terminal-dot.red { background: #ef4444; }
.terminal-dot.yellow { background: #eab308; }
.terminal-dot.green { background: #22c55e; }
.terminal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: var(--code-text-secondary);
}

/* 终端主体 */
.terminal-body {
  padding: 20px;
  background: var(--code-bg);
}
.terminal-input-area {
  position: relative;
}
.terminal-prompt-line {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
}
.terminal-prompt {
  color: var(--code-string); font-weight: 600;
}
.terminal-command {
  color: var(--code-keyword);
}
.terminal-textarea {
  width: 100%; min-height: 100px;
  padding: 12px 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px; line-height: 1.6;
  color: var(--code-text);
  resize: none; outline: none;
  transition: all var(--transition-fast);
}
.terminal-textarea:focus {
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}
.terminal-textarea::placeholder {
  color: var(--code-text-muted);
}

/* 已上传文档 */
.terminal-docs {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin-top: 12px;
}
.terminal-doc-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 6px;
  font-size: 12px; color: var(--code-text-secondary);
}
.terminal-doc-tag.doc-ready { border-color: var(--code-string); }
.terminal-doc-tag.doc-error { border-color: #ef4444; }
.terminal-doc-tag .doc-icon { font-size: 14px; }
.terminal-doc-tag .doc-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.terminal-doc-tag .doc-status { color: var(--code-string); }
.terminal-doc-tag .doc-status.loading { animation: pulse 1s infinite; }
.terminal-doc-tag .doc-remove {
  background: none; border: none; color: var(--code-text-muted);
  cursor: pointer; font-size: 14px; line-height: 1;
  padding: 0 2px; margin-left: 4px;
}
.terminal-doc-tag .doc-remove:hover { color: #ef4444; }

/* 终端底部工具栏 */
.terminal-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px;
  background: var(--code-surface);
  border-top: 1px solid var(--code-border);
}
.terminal-actions-left {
  display: flex; align-items: center; gap: 8px;
  position: relative;
}
.terminal-action-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--code-border);
  border-radius: 6px;
  color: var(--code-text-secondary);
  font-size: 12px; cursor: pointer;
  transition: all var(--transition-fast);
}
.terminal-action-btn:hover {
  border-color: var(--code-keyword);
  color: var(--code-keyword);
}
.terminal-action-btn.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: var(--code-keyword);
  color: var(--code-keyword);
}
.terminal-action-btn input[type="file"] { display: none; }
.terminal-actions-right {
  display: flex; align-items: center; gap: 12px;
}
.terminal-hint {
  font-size: 11px; color: var(--code-text-muted);
  font-family: 'JetBrains Mono', monospace;
}
.terminal-generate-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border: none; border-radius: 8px;
  color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.terminal-generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.4);
}
.terminal-generate-btn:disabled {
  opacity: 0.5; cursor: not-allowed;
}
.loading-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* 主卡片 - 终端风格 */
.main-card {
  max-width: 75vw; margin: 30px auto; padding: 0;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid var(--code-border);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  transition: all var(--transition-normal);
}
.main-card:hover { box-shadow: var(--shadow-xl); }

/* 终端头部 */
.main-card::before {
  content: '';
  display: block;
  padding: 12px 16px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}

/* 文档上传列表 */
.uploaded-docs-list { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 20px 12px; }
.doc-tag {
  display: flex; flex-direction: column; gap: 6px;
  padding: 12px 16px; background: var(--code-surface);
  border: 1px solid var(--code-border); border-radius: 10px;
  font-size: 12px; color: var(--code-text); min-width: 200px; max-width: 280px;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}
.doc-tag:hover { border-color: var(--code-keyword); }
.doc-tag.doc-error { border-color: #fecaca; background: #fef2f2; }
.doc-tag.doc-ready { border-color: var(--code-string); background: rgba(34, 197, 94, 0.05); }
.doc-tag-header { display: flex; align-items: center; gap: 10px; }
.doc-icon { flex-shrink: 0; }
.doc-name { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.doc-remove-btn { background: none; border: none; color: var(--code-text-muted); cursor: pointer; font-size: 18px; padding: 0; line-height: 1; transition: color var(--transition-fast); }
.doc-remove-btn:hover { color: #ef4444; }
.doc-progress-row { display: flex; align-items: center; gap: 6px; font-size: 11px; padding-left: 38px; }
.doc-status-loading { color: var(--code-number); }
.doc-status-error { color: #ef4444; }
.doc-ext { color: var(--code-function); font-weight: 500; }
.doc-meta { color: var(--code-text-muted); }

/* 输入框 - 终端命令行风格 */
.input-wrapper {
  position: relative;
  background: var(--code-bg);
  margin: 0 20px 20px;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--code-border);
  transition: all var(--transition-fast);
}
.input-wrapper:focus-within {
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}
.input-wrapper::before {
  content: '$ generate --topic';
  display: block;
  font-size: 11px;
  color: var(--code-string);
  margin-bottom: 8px;
  font-weight: 500;
}
.text-input {
  width: 100%; background: transparent; border: none;
  color: var(--code-text); font-size: 13px; resize: none;
  min-height: 60px; outline: none; font-family: 'JetBrains Mono', monospace;
  padding-bottom: 50px;
}
.text-input::placeholder { color: var(--code-text-muted); }
.input-toolbar {
  position: absolute; bottom: 12px; left: 16px; right: 16px;
  display: flex; align-items: center; justify-content: space-between;
}
.toolbar-left { display: flex; align-items: center; gap: 8px; }

/* 上传按钮 */
.upload-btn-wrapper { position: relative; display: inline-block; }
.upload-btn {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--code-border); background: var(--code-surface);
  cursor: pointer; transition: all var(--transition-fast);
}
.upload-btn:hover { border-color: var(--code-keyword); background: var(--code-surface-hover); }
.upload-btn input { display: none; }
.upload-tooltip {
  display: block; position: absolute; left: 0; bottom: 100%; margin-bottom: 8px;
  background: var(--code-text); color: var(--code-bg); padding: 10px 14px;
  border-radius: 8px; font-size: 11px; line-height: 1.6;
  white-space: nowrap; z-index: 100; box-shadow: var(--shadow-lg);
}

/* 生成按钮 */
.generate-btn {
  width: 36px; height: 36px; border-radius: 8px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast); 
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}
.generate-btn:hover:not(:disabled) { 
  transform: translateY(-2px); 
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}
.generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.generate-btn .spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* 高级选项 */
.advanced-options-toggle { margin: 0 20px 16px; }
.option-tag {
  padding: 6px 14px; font-size: 11px; border-radius: 6px;
  display: inline-flex; align-items: center; gap: 4px; cursor: pointer;
  background: var(--code-surface); border: 1px solid var(--code-border); color: var(--code-text-secondary);
  transition: all var(--transition-fast);
}
.option-tag:hover { border-color: var(--code-keyword); }
.option-tag.active {
  background: rgba(139, 92, 246, 0.1); border-color: var(--code-keyword); color: var(--code-keyword);
}
.advanced-options-panel {
  width: 100%;
  margin: 0 0 16px 0;
  padding: 14px 16px;
  background: var(--code-surface);
  border-radius: 10px;
  border: 1px solid var(--code-border);
  box-sizing: border-box;
}
.options-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.option-item { display: flex; align-items: center; gap: 8px; }
.option-label { font-size: 12px; color: var(--code-text-secondary); }
.option-item select, .option-item input[type="number"] {
  padding: 6px 12px; border: 1px solid var(--code-border); border-radius: 6px;
  font-size: 12px; background: var(--code-bg); color: var(--code-text);
  cursor: pointer; outline: none; min-width: 100px;
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}
.option-item select:focus, .option-item input[type="number"]:focus {
  border-color: var(--code-keyword);
}
.checkbox-item label { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; }
.checkbox-item input[type="checkbox"] { width: 16px; height: 16px; cursor: pointer; accent-color: var(--code-keyword); }
.option-hint { font-size: 10px; color: var(--code-text-muted); cursor: help; }

/* 自定义配置 */
.custom-config-panel {
  margin-top: 12px; padding: 12px; background: var(--code-bg); border-radius: 8px; border: 1px solid var(--code-border);
}
.custom-config-title { font-size: 11px; color: var(--code-comment); margin-bottom: 10px; font-style: italic; }
.custom-config-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.custom-item { display: flex; align-items: center; gap: 6px; }
.custom-item label { font-size: 11px; color: var(--code-text-secondary); }
.custom-item input {
  width: 60px; padding: 4px 6px; border: 1px solid var(--code-border);
  border-radius: 6px; font-size: 11px; text-align: center;
  font-family: 'JetBrains Mono', monospace;
  background: var(--code-surface); color: var(--code-text);
}

/* 底部抽屉式进度面板 */
.progress-drawer {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 48px);
  max-width: 1200px;
  z-index: 1000;
  font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

@media (min-width: 1440px) {
  .progress-drawer {
    max-width: 1352px;
  }
}

/* 最小化状态栏 */
.progress-bar-mini {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.2s ease;
  height: 40px;
  min-height: 40px;
  max-height: 40px;
  overflow: hidden;
}

.progress-bar-mini:hover {
  background: var(--code-surface-hover);
}

.progress-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.progress-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--code-border);
}

.progress-indicator.active {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
  animation: pulse 1.5s ease-in-out infinite;
}

.progress-status {
  font-size: 12px;
  font-weight: 600;
  color: var(--code-keyword);
  padding: 2px 8px;
  background: rgba(139, 92, 246, 0.1);
  border-radius: 4px;
}

.progress-text {
  font-size: 12px;
  color: var(--code-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.progress-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-logs {
  font-size: 11px;
  color: var(--code-text-muted);
}

.progress-stop-btn,
.progress-toggle-btn,
.progress-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--code-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 11px;
}

.progress-stop-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.progress-toggle-btn:hover,
.progress-close-btn:hover {
  background: var(--code-surface-hover);
  color: var(--code-text);
}

.progress-toggle-btn svg {
  transition: transform 0.2s ease;
  transform: rotate(-90deg);
}

.progress-toggle-btn svg.rotate-down {
  transform: rotate(90deg);
}

/* 展开的日志内容 */
.progress-content {
  overflow: hidden;
  transition: height 0.3s ease;
  background: var(--code-bg);
  border-top: 1px solid var(--code-border);
}

.progress-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  cursor: ns-resize;
  background: transparent;
}

.progress-resize-handle:hover {
  background: var(--code-keyword);
  opacity: 0.3;
}

.progress-logs-container {
  height: 100%;
  overflow-y: auto;
  padding: 12px 16px;
}

.progress-task-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--code-surface);
  border-radius: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.progress-prompt {
  color: #22c55e;
  font-weight: bold;
}

.progress-command {
  color: var(--code-keyword);
  font-weight: 600;
}

.progress-arg {
  color: var(--code-text-muted);
}

.progress-value {
  color: var(--code-string);
}

.progress-task-id {
  font-size: 10px;
  color: var(--code-text-muted);
  margin-left: auto;
}

/* 进度日志列表 */
.progress-log-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-log-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  transition: background 0.2s ease;
}

.progress-log-item:hover {
  background: var(--code-surface);
}

.progress-log-time {
  color: var(--code-text-muted);
  font-size: 10px;
  min-width: 60px;
}

.progress-log-icon {
  font-size: 12px;
  min-width: 16px;
}

.progress-log-icon.success { color: #22c55e; }
.progress-log-icon.error { color: #ef4444; }
.progress-log-icon.warning { color: #f59e0b; }
.progress-log-icon.info { color: var(--code-text-secondary); }
.progress-log-icon.stream { color: var(--code-keyword); }

.progress-log-msg {
  color: var(--code-text);
  flex: 1;
  word-break: break-word;
}

.progress-log-detail {
  margin-top: 4px;
  padding: 8px;
  background: var(--code-surface);
  border-radius: 4px;
  overflow-x: auto;
}

.progress-log-detail pre {
  margin: 0;
  font-size: 11px;
  color: var(--code-text-secondary);
  white-space: pre-wrap;
}

/* 加载动画 */
.progress-loading-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  color: var(--code-text-secondary);
}

.progress-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--code-border);
  border-top-color: var(--code-keyword);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.progress-loading-text {
  font-size: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.terminal-resize-handle.corner-top-left {
  top: 0;
  left: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
}
.terminal-resize-handle.corner-bottom-left {
  bottom: 0;
  left: 0;
  width: 20px;
  height: 20px;
  cursor: nesw-resize;
}
.terminal-resize-handle:hover {
  background: rgba(139, 92, 246, 0.3);
}
.terminal-sidebar.resizing {
  user-select: none;
}
.terminal-sidebar.resizing .terminal-content {
  transition: none;
}

/* 终端标题栏 - 跟随主题 */
.claude-terminal-header {
  display: flex; 
  justify-content: space-between; 
  align-items: center;
  padding: 10px 14px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);
}
.claude-terminal-left { 
  display: flex; 
  align-items: center; 
  gap: 12px; 
}
.claude-terminal-title {
  font-size: 11px; 
  color: var(--code-text-muted); 
  font-weight: 500;
  letter-spacing: 0.3px;
}
.claude-terminal-right { 
  display: flex; 
  gap: 6px; 
}
.claude-action-btn {
  width: 22px; 
  height: 22px;
  background: var(--code-bg); 
  border: 1px solid var(--code-border);
  border-radius: 6px;
  color: var(--code-text-muted); 
  cursor: pointer;
  display: flex; 
  align-items: center; 
  justify-content: center;
  transition: all 0.15s ease;
}
.claude-action-btn:hover { 
  background: var(--code-surface-hover); 
  color: var(--code-text);
  border-color: var(--code-border-hover);
}
.claude-action-btn.close:hover { 
  background: rgba(248, 81, 73, 0.15); 
  color: #f85149;
  border-color: rgba(248, 81, 73, 0.3);
}

/* 终端内容区 - 跟随主题 */
.claude-terminal-body {
  flex: 1;
  max-height: 400px; 
  overflow-y: auto;
  padding: 16px 18px;
  background: var(--code-bg);
}
.claude-terminal-body::-webkit-scrollbar { width: 6px; }
.claude-terminal-body::-webkit-scrollbar-track { background: var(--code-surface); }
.claude-terminal-body::-webkit-scrollbar-thumb { 
  background: var(--code-border); 
  border-radius: 3px;
}
.claude-terminal-body::-webkit-scrollbar-thumb:hover { background: var(--code-text-muted); }

/* 任务头部 - 跟随主题 */
.claude-task-header {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--code-border);
}
.claude-task-line {
  display: flex; 
  align-items: center; 
  gap: 8px;
  font-size: 13px; 
  margin-bottom: 8px;
  padding: 8px 12px;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 6px;
  border-left: 3px solid var(--code-keyword);
}
.claude-prompt { 
  color: var(--code-number); 
  font-weight: 700; 
  font-size: 14px;
}
.claude-command { 
  color: var(--code-function); 
  font-weight: 600; 
}
.claude-arg { 
  color: var(--code-keyword); 
}
.claude-value { 
  color: var(--code-string); 
  background: rgba(34, 197, 94, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
}
.claude-task-id { 
  font-size: 10px; 
  color: var(--code-text-muted);
  padding-left: 12px;
}
.claude-muted { color: var(--code-text-muted); }

/* 日志列表 */
.claude-logs { 
  display: flex; 
  flex-direction: column; 
  gap: 4px; 
}
.claude-log-item {
  display: flex; 
  align-items: flex-start; 
  gap: 10px;
  padding: 6px 10px;
  background: transparent;
  border-radius: 4px;
  border-left: 2px solid var(--code-border);
  animation: claudeSlideIn 0.2s ease;
  transition: all 0.15s ease;
}
.claude-log-item:hover { background: var(--code-surface-hover); }
@keyframes claudeSlideIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

.claude-log-time {
  font-size: 10px; 
  color: var(--code-text-muted);
  min-width: 55px; 
  flex-shrink: 0;
}
.claude-log-icon {
  font-size: 11px; 
  width: 16px; 
  text-align: center; 
  flex-shrink: 0;
  color: var(--code-text-muted);
}
.claude-log-icon.success { color: #3fb950; }
.claude-log-icon.error { color: #f85149; }
.claude-log-icon.stream { color: #d29922; animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.claude-log-msg {
  font-size: 11px; 
  color: var(--code-text);
  flex: 1; 
  line-height: 1.5;
}
.claude-log-item.success { border-left-color: #3fb950; }
.claude-log-item.error { border-left-color: #f85149; }
.claude-log-item.stream { border-left-color: #d29922; }

.claude-log-detail {
  margin-top: 6px; 
  margin-left: 71px;
}
.claude-log-detail pre {
  font-size: 10px; 
  color: var(--code-text-secondary);
  background: var(--code-surface); 
  padding: 8px 10px;
  border-radius: 4px; 
  border: 1px solid var(--code-border);
  max-height: 100px; 
  overflow-y: auto;
  white-space: pre-wrap; 
  word-break: break-word;
  margin: 0;
}

/* 加载动画 - 跟随主题 */
.claude-loading-line {
  display: flex; 
  align-items: center; 
  gap: 10px;
  padding: 8px 10px;
  color: var(--code-keyword);
  font-size: 11px;
  border-left: 2px solid var(--code-keyword);
  margin-top: 4px;
}
.claude-spinner {
  width: 12px; 
  height: 12px;
  border: 2px solid var(--code-border);
  border-top-color: var(--code-keyword);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.claude-loading-text { color: var(--code-text-muted); }

/* 底部状态栏 - 跟随主题 */
.claude-terminal-footer {
  display: flex; 
  justify-content: space-between; 
  align-items: center;
  padding: 8px 14px;
  background: var(--code-surface);
  border-top: 1px solid var(--code-border);
  font-size: 10px;
}
.claude-status-left { 
  display: flex; 
  align-items: center; 
  gap: 10px; 
}
.claude-status-indicator {
  width: 6px; 
  height: 6px; 
  border-radius: 50%;
  background: var(--code-border);
}
.claude-status-indicator.active {
  background: #3fb950;
  box-shadow: 0 0 6px rgba(63, 185, 80, 0.5);
  animation: glow 1.5s ease-in-out infinite;
}
@keyframes glow { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

.claude-status-badge {
  padding: 2px 8px;
  background: var(--code-surface);
  border-radius: 4px;
  color: var(--code-text-muted);
  font-weight: 500;
  border: 1px solid var(--code-border);
}
.claude-status-badge.running { 
  background: rgba(163, 113, 247, 0.15); 
  color: #a371f7; 
  border-color: rgba(163, 113, 247, 0.3);
}
.claude-status-badge.success { 
  background: rgba(63, 185, 80, 0.15); 
  color: #3fb950; 
  border-color: rgba(63, 185, 80, 0.3);
}
.claude-status-badge.error { 
  background: rgba(248, 81, 73, 0.15); 
  color: #f85149; 
  border-color: rgba(248, 81, 73, 0.3);
}

.claude-status-text { 
  color: var(--code-text-muted); 
  max-width: 200px; 
  overflow: hidden; 
  text-overflow: ellipsis; 
  white-space: nowrap; 
}

.claude-status-right { 
  display: flex; 
  align-items: center; 
  gap: 10px; 
}
.claude-stats { color: var(--code-text-muted); }
.claude-stop-btn {
  display: flex; 
  align-items: center; 
  gap: 4px;
  padding: 4px 10px;
  background: rgba(248, 81, 73, 0.15);
  border: 1px solid rgba(248, 81, 73, 0.3);
  border-radius: 6px;
  color: #f85149;
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.claude-stop-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.5);
}

/* 结果区域 - 终端风格 */
.result-section { 
  max-width: 1200px;
  margin: 30px auto;
  padding: 0 24px;
  box-sizing: border-box;
}
.result-section.show { display: block; }
.result-card {
  background: var(--glass-bg); 
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 16px; border: 1px solid var(--code-border);
  overflow: hidden; box-shadow: var(--shadow-lg);
}
.result-header {
  padding: 16px 20px; 
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%); 
  border-bottom: 1px solid var(--code-border);
}
.result-title { font-size: 16px; font-weight: 600; color: var(--code-text); }
.result-meta { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.meta-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;
}
.meta-tag.sections { background: rgba(139, 92, 246, 0.1); color: var(--code-keyword); }
.meta-tag.code { background: rgba(59, 130, 246, 0.1); color: var(--code-function); }
.meta-tag.images { background: rgba(236, 72, 153, 0.1); color: var(--code-variable); }
.meta-tag.score { background: rgba(34, 197, 94, 0.1); color: var(--code-string); }
.result-pages { padding: 20px; }
.page-item {
  background: var(--code-surface); border-radius: 12px; padding: 16px; margin-bottom: 16px;
  border: 1px solid var(--code-border);
  transition: all var(--transition-fast);
}
.page-item:hover { border-color: var(--code-keyword); }
.page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.page-number {
  width: 28px; height: 28px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border-radius: 6px; display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 12px; color: #fff;
}
.page-title { font-size: 14px; font-weight: 600; color: var(--code-text); flex: 1; }
.page-actions { display: flex; gap: 8px; }
.page-actions button {
  padding: 6px 12px; border: none; border-radius: 6px; color: #fff; font-size: 11px; cursor: pointer;
  transition: all var(--transition-fast);
}
.page-actions button:hover { transform: translateY(-1px); }
.download-video-btn { background: linear-gradient(135deg, var(--code-keyword), #7c3aed); }
.export-image-btn { background: linear-gradient(135deg, var(--code-variable), #db2777); }
.download-markdown-btn { background: linear-gradient(135deg, var(--code-string), #16a34a); }
.publish-btn { background: linear-gradient(135deg, var(--code-function), #2563eb); }
.video-container {
  display: flex; justify-content: center; padding: 16px; background: var(--code-bg); border-radius: 10px;
  border: 1px solid var(--code-border);
}
.video-container video {
  max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: var(--shadow-md);
}

/* Markdown 渲染 */
.markdown-body {
  max-height: 700px; overflow-y: auto; padding: 16px; background: transparent;
  font-size: 14px; line-height: 1.8;
}
.markdown-body::-webkit-scrollbar { width: 6px; }
.markdown-body::-webkit-scrollbar-track { background: var(--code-surface); border-radius: 3px; }
.markdown-body::-webkit-scrollbar-thumb { background: var(--code-border); border-radius: 3px; }

/* 示例区域 - 代码卡片风格 */
.examples-section { max-width: 75vw; margin: 40px auto; padding: 0 20px; }
.section-title { 
  font-size: 16px; font-weight: 600; margin-bottom: 20px; color: var(--code-text);
  display: flex; align-items: center; gap: 8px;
}
.section-title::before { content: '//'; color: var(--code-comment); }
.examples-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.example-card {
  background: var(--glass-bg); 
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 12px; overflow: hidden;
  border: 1px solid var(--code-border); cursor: pointer; 
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}
.example-card:hover {
  transform: translateY(-4px); border-color: var(--code-keyword);
  box-shadow: var(--shadow-lg);
}
.example-card:hover::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--code-keyword), var(--code-function), var(--code-variable));
}
.example-image {
  height: 120px; background: linear-gradient(135deg, var(--code-surface), var(--code-surface-hover));
  display: flex; align-items: center; justify-content: center; font-size: 36px;
  position: relative;
}
.example-content { padding: 14px; }
.example-title { font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--code-text); }
.example-desc { font-size: 11px; color: var(--code-comment); font-style: italic; }

/* 代码风格容器 - 统一宽度 */
.code-cards-container {
  max-width: 1248px;
  margin: 0 auto;
  padding: 24px;
}

/* 博客列表折叠按钮 - 简约设计 */
.blog-list-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 12px 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  color: var(--code-text);
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.2s ease;
  margin-bottom: 12px;
  box-sizing: border-box;
  text-align: left;
}

.blog-list-toggle:hover {
  background: var(--code-surface-hover);
  color: var(--code-text);
}

.blog-list-toggle > svg {
  transition: transform 0.2s ease;
  flex-shrink: 0;
  color: var(--code-text-muted);
}

.blog-list-toggle > svg.rotate-up {
  transform: rotate(180deg);
}

.toggle-label {
  color: var(--code-text-secondary);
}

.toggle-count {
  background: var(--code-surface);
  color: var(--code-text-muted);
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 10px;
}

.toggle-stats {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  color: var(--code-text-secondary);
  font-size: 11px;
  flex: 1;
  overflow: visible;
}

.stats-cmd {
  color: var(--code-keyword);
  font-weight: bold;
}

.stats-label {
  color: var(--code-text-secondary);
}

.stats-value {
  color: var(--code-number);
  font-weight: bold;
}

.stats-text {
  color: var(--code-text-secondary);
}

.stats-sep {
  color: var(--code-text-muted);
  margin: 0 2px;
}

.sort-icon {
  color: var(--code-text-muted);
  display: inline;
}

.sort-label {
  color: var(--code-text-secondary);
}

/* 历史记录工具栏 */
.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--code-border);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 终端风格头部 */
.code-cards-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; margin-bottom: 24px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  font-family: 'JetBrains Mono', monospace;
}
.code-cards-header-left {
  display: flex; align-items: center; gap: 12px;
}
.terminal-dots {
  display: flex; gap: 6px;
}
.terminal-dot {
  width: 12px; height: 12px; border-radius: 50%;
}
.terminal-dot.red { background: #ff5f56; }
.terminal-dot.yellow { background: #ffbd2e; }
.terminal-dot.green { background: #27ca40; }
.terminal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px; color: var(--code-text-secondary);
}
.terminal-status {
  padding: 4px 12px;
  background: rgba(34, 197, 94, 0.15);
  color: var(--code-string);
  border-radius: 12px;
  font-size: 11px; font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
}

/* 搜索栏 */
.code-search-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; margin-bottom: 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
}
.search-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: var(--code-keyword);
  white-space: nowrap;
}
.search-input-wrapper {
  flex: 1; display: flex; align-items: center; gap: 8px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  padding: 8px 12px;
  transition: all var(--transition-fast);
}
.search-input-wrapper:focus-within {
  border-color: var(--code-keyword);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}
.search-prompt {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: var(--code-string);
  font-weight: 600;
}
.search-input-wrapper input {
  flex: 1; border: none; background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: var(--code-text);
  outline: none;
}
.search-input-wrapper input::placeholder {
  color: var(--code-text-muted);
}
.search-hint {
  font-size: 11px; color: var(--code-text-muted);
  white-space: nowrap;
}
.search-hint kbd {
  padding: 2px 6px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}
.execute-btn {
  padding: 6px 14px;
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border: none; border-radius: 6px;
  color: #fff; font-size: 11px; font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.execute-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}

/* 统计信息和筛选 */
.code-cards-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  margin: 0 0 16px 0;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
}
.stats-left {
  display: flex; align-items: center; gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}
.stats-command { color: var(--code-text-secondary); }
.stats-count { color: var(--code-keyword); font-weight: 600; }
.stats-label { color: var(--code-text-muted); }
.stats-separator { color: var(--code-text-muted); margin-left: 8px; }
.code-sort-buttons {
  display: inline-flex; gap: 4px; margin-left: 8px;
}
.code-sort-btn {
  padding: 4px 10px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  font-size: 11px; color: var(--code-text-secondary);
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.code-sort-btn:hover { background: var(--code-surface-hover); }
.code-sort-btn.active {
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  color: #fff; border-color: var(--code-keyword);
}
.stats-right {
  display: flex; align-items: center; gap: 12px;
  flex-wrap: wrap;
}
.code-tabs {
  display: flex; gap: 6px;
}
.code-tab-btn {
  padding: 6px 14px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  font-size: 11px; color: var(--code-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.code-tab-btn:hover { background: var(--code-surface-hover); border-color: var(--code-keyword); }
.code-tab-btn.active {
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  color: #fff; border-color: var(--code-keyword);
}

/* 历史记录区域 - 终端风格 */
.history-section { max-width: 75vw; margin: 40px auto; padding: 0 20px; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.history-tabs-wrapper { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.history-tabs { display: flex; gap: 8px; }
.history-tab {
  padding: 8px 16px; border: 1px solid var(--code-border); background: var(--code-surface);
  border-radius: 8px; cursor: pointer; font-size: 12px; color: var(--code-text-secondary); 
  transition: all var(--transition-fast);
}
.history-tab:hover { background: var(--code-surface-hover); border-color: var(--code-keyword); }
.history-tab.active {
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed); color: white; border-color: var(--code-keyword);
}
.history-total, .books-total { font-size: 11px; opacity: 0.8; }
.content-type-filter { display: flex; gap: 6px; }
.filter-btn {
  padding: 4px 12px; border: 1px solid var(--code-border); background: var(--code-surface);
  border-radius: 6px; cursor: pointer; font-size: 11px; color: var(--code-text-secondary); 
  transition: all var(--transition-fast);
}
.filter-btn:hover { background: var(--code-surface-hover); }
.filter-btn.active {
  background: rgba(139, 92, 246, 0.15); color: var(--code-keyword); border-color: var(--code-keyword);
}
.scan-books-btn {
  padding: 6px 14px; border: 1px solid var(--code-keyword);
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  color: white; border-radius: 6px; cursor: pointer; font-size: 11px; 
  transition: all var(--transition-fast);
}
.scan-books-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4); }
.scan-books-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

/* 代码风格卡片网格 - 每行三个 */
.code-cards-grid { 
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 0;
  margin: 0;
  width: 100%;
  box-sizing: border-box;
}
.history-empty { 
  text-align: center; padding: 60px 40px; 
  color: var(--code-comment); font-size: 13px; 
  font-family: 'JetBrains Mono', monospace;
  grid-column: 1 / -1;
}

/* 代码风格博客卡片 */
.code-blog-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--code-border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
  position: relative;
}
.code-blog-card:hover {
  transform: translateY(-4px);
  border-color: var(--code-keyword);
  box-shadow: var(--shadow-lg);
}
.code-blog-card:hover::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--code-keyword), var(--code-function), var(--code-variable));
}
.code-blog-card.xhs-card { border-color: rgba(236, 72, 153, 0.2); }
.code-blog-card.xhs-card:hover { border-color: var(--code-variable); }
.code-blog-card.xhs-card:hover::before {
  background: linear-gradient(90deg, var(--code-variable), #db2777, var(--code-number));
}

/* 卡片头部 */
.code-card-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px;
  background: linear-gradient(180deg, var(--code-surface) 0%, transparent 100%);
  border-bottom: 1px solid var(--code-border);
}
.code-card-folder {
  display: flex; align-items: center; gap: 8px;
  color: var(--code-text-secondary); font-size: 12px;
}
.code-card-folder-icon { color: var(--code-number); }
.code-card-folder-name { font-family: 'JetBrains Mono', monospace; }
.code-card-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--code-text-muted);
}
.code-card-status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--code-string);
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}

/* 卡片主体 - 代码风格 */
.code-card-body { padding: 16px 0; }
.code-line {
  display: flex; align-items: flex-start;
  padding: 4px 20px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px; line-height: 1.7;
  transition: background var(--transition-fast);
}
.code-line:hover { background: var(--code-surface); }
.code-line-number {
  width: 24px; flex-shrink: 0;
  color: var(--code-text-muted);
  text-align: right; margin-right: 16px;
  user-select: none;
}
.code-line-content { flex: 1; min-width: 0; }
.code-keyword { color: var(--code-keyword); margin-right: 8px; font-weight: 500; }
.code-blog-title {
  color: var(--code-text); font-weight: 700; font-size: 14px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  display: inline-block; max-width: 280px; vertical-align: bottom;
}
.code-variable { color: var(--code-variable); }
.code-string { color: var(--code-string); font-size: 12px; }
.code-comment { color: var(--code-comment); font-style: italic; font-size: 12px; }
.code-command-line {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px; margin-top: 8px;
  background: var(--code-surface);
  border-top: 1px solid var(--code-border);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
.code-prompt { color: var(--code-string); font-weight: 600; }
.code-command { color: var(--code-text-secondary); }

/* 卡片底部 */
.code-card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px;
  border-top: 1px solid var(--code-border);
  background: var(--code-surface);
}
.code-card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.code-tag {
  padding: 3px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  transition: all var(--transition-fast);
}
.code-tag.tag-blog { background: rgba(139, 92, 246, 0.15); color: var(--code-keyword); }
.code-tag.tag-xhs { background: rgba(236, 72, 153, 0.15); color: var(--code-variable); }
.code-tag.tag-info { background: rgba(100, 116, 139, 0.15); color: var(--code-text-secondary); }
.code-tag.tag-score { background: rgba(251, 191, 36, 0.15); color: #f59e0b; }
.code-tag.tag-video { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.code-tag.tag-book { 
  background: rgba(59, 130, 246, 0.15); color: var(--code-function); 
  cursor: pointer;
}
.code-tag.tag-book:hover { background: rgba(59, 130, 246, 0.25); }
.code-card-date {
  font-size: 11px; color: var(--code-text-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* 悬停箭头 */
.code-card-arrow {
  position: absolute; right: 16px; top: 50%;
  transform: translateY(-50%) translateX(10px);
  opacity: 0;
  color: var(--code-keyword);
  transition: all var(--transition-fast);
}
.code-blog-card:hover .code-card-arrow {
  opacity: 1; transform: translateY(-50%) translateX(0);
}

/* 删除按钮 */
.code-card-delete {
  position: absolute; top: 10px; right: 10px;
  width: 22px; height: 22px;
  background: rgba(239, 68, 68, 0.9);
  border: none; border-radius: 6px;
  color: #fff; font-size: 14px; line-height: 1;
  cursor: pointer; opacity: 0;
  transition: all var(--transition-fast);
  z-index: 10;
}
.code-blog-card:hover .code-card-delete { opacity: 1; }
.code-card-delete:hover { background: #ef4444; transform: scale(1.1); }

/* 转小红书按钮 */
.code-card-action {
  position: absolute; bottom: 10px; right: 10px;
  padding: 4px 10px;
  background: linear-gradient(135deg, var(--code-variable), #db2777);
  border: none; border-radius: 6px;
  color: #fff; font-size: 10px; font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  cursor: pointer; opacity: 0;
  transition: all var(--transition-fast);
  z-index: 10;
}
.code-blog-card:hover .code-card-action { opacity: 1; }
.code-card-action:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(236, 72, 153, 0.4); }
.history-card:hover .delete-btn { opacity: 1; }

/* 封面预览开关 - iOS 风格滑动开关 */
.cover-preview-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: var(--code-surface);
  border: 1px solid var(--code-border);
  border-radius: 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--code-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}
.cover-preview-toggle:hover {
  background: var(--code-surface-hover);
  border-color: var(--code-border-hover);
}
.toggle-label-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toggle-switch {
  position: relative;
  width: 40px;
  height: 22px;
  background: var(--code-border);
  border-radius: 11px;
  transition: all var(--transition-fast);
}
.toggle-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: all var(--transition-fast);
}
.cover-preview-toggle.active .toggle-switch {
  background: var(--code-keyword);
}
.cover-preview-toggle.active .toggle-switch::after {
  left: 20px;
}
.cover-preview-toggle.active {
  color: var(--code-text);
}

/* 封面图预览 */
.card-cover-preview {
  position: relative;
  width: 100%;
  height: 140px;
  overflow: hidden;
  border-radius: 12px 12px 0 0;
  background: linear-gradient(135deg, var(--code-surface), var(--code-bg));
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-cover-preview img,
.card-cover-preview video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform 0.3s ease;
  background: var(--code-bg);
}
.code-blog-card:hover .card-cover-preview img,
.code-blog-card:hover .card-cover-preview video {
  transform: scale(1.02);
}
.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.6) 100%);
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.code-blog-card:hover .cover-overlay {
  opacity: 1;
}
.cover-badge {
  background: rgba(139, 92, 246, 0.9);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.5px;
}
.cover-badge.video {
  background: rgba(245, 158, 11, 0.9);
}

/* 带封面的卡片样式调整 */
.code-blog-card.with-cover {
  border-radius: 12px;
}
.code-blog-card.with-cover .code-card-header {
  border-radius: 0;
}
.xhs-badge {
  position: absolute; top: 8px; left: 8px;
  background: linear-gradient(135deg, var(--code-variable), #db2777);
  color: white; padding: 2px 8px; border-radius: 6px; font-size: 9px; font-weight: 600; z-index: 2;
}
.book-tag {
  position: absolute; top: 8px; left: 8px;
  background: rgba(139, 92, 246, 0.9); color: #fff;
  padding: 3px 8px; border-radius: 6px; font-size: 10px;
  cursor: pointer; z-index: 10; max-width: 120px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.to-xhs-btn {
  position: absolute; bottom: 8px; right: 8px;
  background: linear-gradient(135deg, var(--code-variable), #db2777);
  color: white; border: none; padding: 4px 10px; border-radius: 6px;
  font-size: 10px; font-weight: 500; cursor: pointer; z-index: 3;
  opacity: 0; transition: all var(--transition-fast);
}
.history-card:hover .to-xhs-btn { opacity: 1; }
.history-cover {
  height: 110px; background: linear-gradient(135deg, var(--code-keyword), var(--code-function));
  display: flex; align-items: center; justify-content: center; font-size: 32px; overflow: hidden;
}
.history-cover img, .history-cover video { width: 100%; height: 100%; object-fit: cover; }
.history-content { padding: 12px; }
.history-topic {
  font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--code-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.history-meta { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.history-meta span {
  font-size: 10px; padding: 2px 6px; border-radius: 4px;
  background: var(--code-surface); color: var(--code-text-secondary);
}
.history-time { font-size: 10px; color: var(--code-text-muted); }

/* 分页 - 终端风格 */
.history-pagination {
  display: flex; justify-content: center; align-items: center;
  gap: 6px; padding: 20px; flex-wrap: wrap;
}
.history-pagination button {
  padding: 6px 14px; border: 1px solid var(--code-border); background: var(--code-surface);
  border-radius: 6px; cursor: pointer; font-size: 11px; color: var(--code-text-secondary); 
  transition: all var(--transition-fast);
  font-family: 'JetBrains Mono', monospace;
}
.history-pagination button:hover:not(:disabled) { background: var(--code-keyword); color: white; border-color: var(--code-keyword); }
.history-pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.history-pagination button.active { background: var(--code-keyword); color: white; border-color: var(--code-keyword); }
.page-info { font-size: 11px; color: var(--code-text-muted); padding: 0 8px; }

/* 书籍网格 - 代码风格 */
.books-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 20px; justify-items: center;
  padding: 20px;
}
.book-card {
  display: flex; flex-direction: column; align-items: center;
  cursor: pointer; transition: all var(--transition-normal);
}
.book-card:hover { transform: translateY(-6px); }
.book-cover {
  width: 100px; height: 140px; border-radius: 4px 10px 10px 4px;
  overflow: hidden; position: relative;
  box-shadow: var(--shadow-md), -2px 0 8px rgba(0, 0, 0, 0.1);
  transition: all var(--transition-normal);
}
.book-card:hover .book-cover { box-shadow: var(--shadow-xl), -2px 0 8px rgba(0, 0, 0, 0.1); }
.book-cover img { width: 100%; height: 100%; object-fit: cover; }
.book-cover::before {
  content: ''; position: absolute; left: 0; top: 0; width: 6px; height: 100%;
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.25) 0%, transparent 100%);
}
.book-cover-default {
  width: 100%; height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 10px; text-align: center;
}
.book-cover-default .book-icon { font-size: 28px; margin-bottom: 6px; }
.book-cover-default .book-title-inner {
  font-size: 10px; font-weight: 600; color: #fff; line-height: 1.3;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
}
.theme-ai { background: linear-gradient(135deg, var(--code-keyword) 0%, #7c3aed 100%); }
.theme-web { background: linear-gradient(135deg, var(--code-variable) 0%, #db2777 100%); }
.theme-data { background: linear-gradient(135deg, var(--code-function) 0%, #0ea5e9 100%); }
.theme-devops { background: linear-gradient(135deg, var(--code-string) 0%, #10b981 100%); }
.theme-security { background: linear-gradient(135deg, var(--code-number) 0%, #f59e0b 100%); }
.theme-general { background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%); }
.book-title {
  margin-top: 10px; font-size: 11px; font-weight: 600; color: var(--code-text);
  text-align: center; max-width: 110px; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.book-stats { margin-top: 4px; font-size: 9px; color: var(--code-text-muted); display: flex; gap: 6px; }

/* 发布弹窗 - 终端风格 */
.publish-modal {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6); z-index: 1000;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(4px);
}
.publish-modal-content {
  background: var(--glass-bg); 
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px; padding: 24px;
  max-width: 500px; width: 90%; 
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--code-border);
}
.publish-modal-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
}
.publish-modal-header h2 { margin: 0; font-size: 16px; color: var(--code-text); }
.publish-modal-header button {
  background: var(--code-surface); border: 1px solid var(--code-border); 
  width: 28px; height: 28px; border-radius: 6px;
  font-size: 18px; cursor: pointer; color: var(--code-text-secondary);
  transition: all var(--transition-fast);
}
.publish-modal-header button:hover { background: var(--code-surface-hover); color: #ef4444; }
.publish-form .form-item { margin-bottom: 16px; }
.publish-form label { display: block; font-size: 12px; color: var(--code-text-secondary); margin-bottom: 6px; }
.publish-form label a { color: var(--code-function); margin-left: 8px; }
.publish-form select, .publish-form textarea {
  width: 100%; padding: 10px 12px; border: 1px solid var(--code-border); border-radius: 8px;
  font-size: 12px; background: var(--code-surface); color: var(--code-text);
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}
.publish-form select:focus, .publish-form textarea:focus {
  outline: none; border-color: var(--code-keyword);
}
.publish-form textarea { height: 120px; resize: vertical; }
.cookie-warning {
  margin-top: 8px; padding: 10px 12px; background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; font-size: 11px; color: var(--code-number);
}
.cookie-help {
  background: var(--code-surface); border: 1px solid var(--code-border);
  border-radius: 8px; padding: 12px; margin-bottom: 16px;
  font-size: 11px; color: var(--code-text-secondary); line-height: 1.6;
}
.publish-submit-btn {
  width: 100%; padding: 12px; 
  background: linear-gradient(135deg, var(--code-keyword), #7c3aed);
  border: none; border-radius: 8px; color: white; font-size: 13px; cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  transition: all var(--transition-fast);
}
.publish-submit-btn:hover:not(:disabled) { 
  transform: translateY(-1px); 
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4); 
}
.publish-submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.publish-status { margin-top: 12px; font-size: 12px; text-align: center; }
.publish-status.success { color: var(--code-string); }
.publish-status.error { color: #ef4444; }

/* Lucide 图标通用样式 */
.option-label { display: inline-flex; align-items: center; gap: 6px; }
.option-label svg { flex-shrink: 0; color: var(--code-keyword); }
.meta-tag { display: inline-flex; align-items: center; gap: 4px; }
.meta-tag svg { flex-shrink: 0; }
.code-tag { display: inline-flex; align-items: center; gap: 4px; }
.code-tag svg { flex-shrink: 0; }
.code-sort-btn { display: inline-flex; align-items: center; gap: 4px; }
.code-sort-btn svg { flex-shrink: 0; }
.code-tab-btn { display: inline-flex; align-items: center; gap: 6px; }
.code-tab-btn svg { flex-shrink: 0; }
.scan-books-btn { display: inline-flex; align-items: center; gap: 6px; }
.scan-books-btn svg { flex-shrink: 0; }
.stop-btn { display: inline-flex; align-items: center; gap: 6px; }
.stop-btn svg { flex-shrink: 0; }
.page-actions button { display: inline-flex; align-items: center; gap: 6px; }
.page-actions button svg { flex-shrink: 0; }
.progress-title { display: flex; align-items: center; gap: 8px; }
.progress-title svg { color: var(--code-keyword); }
.custom-config-title { display: flex; align-items: center; gap: 6px; }
.custom-config-title svg { color: var(--code-comment); }
.checkbox-item label { display: flex; align-items: center; gap: 6px; }
.checkbox-item label svg { flex-shrink: 0; color: var(--code-keyword); }
.publish-modal-header h2 { display: flex; align-items: center; gap: 8px; }
.publish-modal-header h2 svg { color: var(--code-keyword); }
.publish-modal-header button { display: flex; align-items: center; justify-content: center; }
.publish-submit-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
.code-card-delete { display: flex; align-items: center; justify-content: center; }
.code-card-action { display: inline-flex; align-items: center; gap: 4px; }
.doc-icon { flex-shrink: 0; color: var(--code-function); }
.doc-status { flex-shrink: 0; color: var(--code-string); }
.doc-status.loading { animation: spin 1s linear infinite; }
.doc-remove { display: flex; align-items: center; justify-content: center; padding: 2px; }

/* 旋转动画 */
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 淡入淡出动画 */
@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
  10% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  90% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
}

/* 响应式 */
@media (max-width: 1200px) {
  .code-cards-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .navbar { padding: 12px 16px; }
  .nav-link span { display: none; }
  .nav-tabs { display: none; }
  .hero h1 { font-size: 24px; }
  .main-card { margin: 16px; }
  .input-wrapper { margin: 0 16px 16px; }
  .advanced-options-toggle { margin: 0 16px 12px; }
  .advanced-options-panel { margin: 0 16px 12px; }
  .options-row { flex-direction: column; }
  .code-cards-grid { grid-template-columns: 1fr; }
  .terminal-search-bar { flex-wrap: wrap; }
  .terminal-search-hint { display: none; }
}
@media (max-width: 375px) {
  .hero h1 { font-size: 20px; }
  .code-cards-container { padding: 12px; }
  .options-row { gap: 8px; }
  .option-item { width: 100%; }
}
@media (min-width: 1440px) {
  .code-cards-container { max-width: 1400px; }
  .code-cards-grid { grid-template-columns: repeat(3, 1fr); }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .bg-animation::before { animation: none; }
  .cursor { animation: none; opacity: 1; }
}
</style>
