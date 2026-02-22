<template>
  <div class="code-input-card" v-bind="dragHandlers" @paste="onPaste">
    <!-- Code Style 粒子背景 -->
    <div class="particles-bg">
      <!-- 代码符号粒子 - 移动端减少数量 -->
      <span class="code-particle cp1">&lt;/&gt;</span>
      <span class="code-particle cp2">{}</span>
      <span class="code-particle cp3">( )</span>
      <span class="code-particle cp4 hide-mobile">[ ]</span>
      <span class="code-particle cp5 hide-mobile">=&gt;</span>
      <span class="code-particle cp6 hide-mobile">/**</span>
      <span class="code-particle cp7 hide-mobile">$_</span>
      <span class="code-particle cp8 hide-mobile">::</span>
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
      <TipTapEditor
        v-model="localTopic"
        class="code-input-textarea"
        placeholder="输入技术主题，如：LangGraph 入门教程、Redis 性能优化、Vue3 最佳实践..."
        :disabled="isLoading"
        @submit="handleGenerate"
      />
      <button
        class="enhance-btn"
        :class="{ enhancing: isEnhancing }"
        :disabled="isEnhancing || !localTopic.trim() || isLoading"
        @click="$emit('enhanceTopic')"
        title="优化主题"
      >
        <Wand2 v-if="!isEnhancing" :size="16" />
        <Loader v-else :size="16" class="enhance-spinner" />
      </button>
      <button
        class="code-generate-btn"
        :disabled="isLoading || !localTopic.trim()"
        @click="handleGenerate"
        :title="isLoading ? '生成中...' : '生成博客'"
      >
        <span v-if="isLoading" class="loading-spinner"></span>
        <Rocket v-else :size="16" />
        <span class="btn-text">{{ isLoading ? '生成中' : 'execute' }}</span>
      </button>
    </div>

    <!-- 拖拽上传 overlay -->
    <Transition name="drag-fade">
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-overlay-content">
          <Upload :size="32" class="drag-icon" />
          <span class="drag-text">释放文件以上传</span>
          <span class="drag-hint">支持 PDF、Markdown、TXT 格式</span>
        </div>
      </div>
    </Transition>

    <!-- Prompt 增强动画（对齐 DeerFlow input-box.tsx:156-200） -->
    <Transition name="enhance-fade">
      <div v-if="isEnhancing" class="enhance-overlay">
        <div class="enhance-glow"></div>
        <span v-for="i in 6" :key="i" class="enhance-particle" :style="`--delay: ${i * 0.2}s; --left: ${20 + i * 12}%`"></span>
      </div>
    </Transition>

    <!-- 已上传文档列表 -->
    <div v-if="uploadedDocuments.length > 0" class="code-input-docs">
      <div
        v-for="doc in uploadedDocuments"
        :key="doc.id"
        class="code-doc-tag"
        :class="{
          'doc-error': doc.status === 'error',
          'doc-ready': doc.status === 'ready'
        }"
      >
        <FileText :size="14" class="doc-icon" />
        <span class="doc-name">{{ truncateFilename(doc.filename) }}</span>
        <FileCheck v-if="doc.status === 'ready'" :size="14" class="doc-status" />
        <Loader v-else-if="isSpinningStatus(doc.status)" :size="14" class="doc-status loading" />
        <button class="doc-remove" @click="$emit('removeDocument', doc.id)">
          <X :size="12" />
        </button>
      </div>
    </div>

    <!-- 底部工具栏 -->
    <div class="code-input-footer">
      <div class="code-input-actions-left">
        <label
          class="code-action-btn"
          @mouseenter="showUploadTooltip = true"
          @mouseleave="showUploadTooltip = false"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
          <span>附件</span>
          <input
            type="file"
            accept=".pdf,.md,.txt,.markdown"
            multiple
            @change="handleFileUpload"
          >
        </label>
        <div v-if="showUploadTooltip" class="upload-tooltip">
          PDF 文件不超过 15 页<br>
          支持 PDF、Markdown、TXT 格式
        </div>
        <button
          class="code-action-btn"
          :class="{ active: showAdvancedOptions }"
          @click="$emit('update:showAdvancedOptions', !showAdvancedOptions)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          <span>高级选项</span>
        </button>
      </div>
      <div class="code-input-actions-right"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { FileText, FileCheck, Loader, X, Rocket, Wand2, Upload } from 'lucide-vue-next'
import TipTapEditor from './TipTapEditor.vue'
import { useDragUpload } from '@/composables/useDragUpload'
import { usePasteService } from '@/composables/usePasteService'

interface UploadedDocument {
  id: string
  filename: string
  status: string
  fileSize?: number
  wordCount?: number
  errorMessage?: string
}

interface Props {
  topic: string
  uploadedDocuments: UploadedDocument[]
  isLoading: boolean
  isEnhancing: boolean
  showAdvancedOptions: boolean
}

interface Emits {
  (e: 'update:topic', value: string): void
  (e: 'update:showAdvancedOptions', value: boolean): void
  (e: 'generate'): void
  (e: 'enhanceTopic'): void
  (e: 'fileUpload', files: FileList): void
  (e: 'removeDocument', docId: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const ALLOWED_EXTS = ['pdf', 'md', 'txt', 'markdown']

const { isDragging, dragHandlers } = useDragUpload({
  allowedExts: ALLOWED_EXTS,
  onFilesDropped: (files) => emit('fileUpload', files as unknown as FileList),
  enabled: computed(() => !props.isLoading),
})

const { onPaste } = usePasteService({
  allowedExts: ALLOWED_EXTS,
  onFilesPasted: (files) => emit('fileUpload', files as unknown as FileList),
  enabled: computed(() => !props.isLoading),
})

const showUploadTooltip = ref(false)

const localTopic = computed({
  get: () => props.topic,
  set: (value) => emit('update:topic', value)
})

const handleGenerate = () => {
  if (!props.topic.trim() || props.isLoading) return
  emit('generate')
}

const handleFileUpload = (e: Event) => {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  emit('fileUpload', files)
  input.value = ''
}

const truncateFilename = (name: string) => {
  return name.length > 20 ? name.substring(0, 18) + '...' : name
}

const isSpinningStatus = (status: string) => {
  return ['uploading', 'pending', 'processing'].includes(status)
}
</script>

<style scoped>
.code-input-card {
  position: relative;
  width: 100%;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-lg);
  box-sizing: border-box;
  box-shadow: var(--shadow-md);
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
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  opacity: 0.08;
  animation: code-float 12s ease-in-out infinite;
}

.code-particle.cp1 {
  font-size: 28px;
  color: var(--color-terminal-keyword);
  top: 15%;
  right: 8%;
  animation-delay: 0s;
}

.code-particle.cp2 {
  font-size: 24px;
  color: var(--color-terminal-string);
  top: 55%;
  right: 12%;
  animation-delay: -2s;
}

.code-particle.cp3 {
  font-size: 20px;
  color: var(--color-terminal-function);
  top: 30%;
  right: 22%;
  animation-delay: -4s;
}

.code-particle.cp4 {
  font-size: 18px;
  color: var(--color-terminal-variable);
  top: 70%;
  right: 5%;
  animation-delay: -6s;
}

.code-particle.cp5 {
  font-size: 22px;
  color: var(--color-terminal-keyword);
  top: 45%;
  right: 28%;
  animation-delay: -8s;
}

.code-particle.cp6 {
  font-size: 16px;
  color: var(--color-terminal-comment);
  top: 20%;
  right: 35%;
  animation-delay: -3s;
}

.code-particle.cp7 {
  font-size: 20px;
  color: var(--color-terminal-string);
  top: 75%;
  right: 20%;
  animation-delay: -5s;
}

.code-particle.cp8 {
  font-size: 18px;
  color: var(--color-terminal-function);
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
    transform: translateY(-10px) rotate(5deg);
    opacity: 0.12;
  }
}

/* 终端头部 */
.code-input-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
  z-index: 1;
}

.terminal-dots {
  display: flex;
  gap: var(--space-xs);
}

.terminal-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
}

.terminal-dot.red {
  background: var(--color-dot-red);
}

.terminal-dot.yellow {
  background: var(--color-dot-yellow);
}

.terminal-dot.green {
  background: var(--color-dot-green);
}

.terminal-title {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 输入区域 */
.code-input-body {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg);
  z-index: 1;
}

.code-input-prompt {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.code-prompt {
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-terminal-string);
  font-weight: var(--font-weight-bold);
}

.code-command {
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

.code-input-textarea {
  flex: 1;
  min-height: 80px;
}

/* 已上传文档列表 */
.code-input-docs {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  padding: 0 var(--space-lg) var(--space-md);
  z-index: 1;
}

.code-doc-tag {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: var(--color-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

.code-doc-tag.doc-ready {
  background: rgba(16, 185, 129, 0.15);
  border-color: var(--color-success);
}

.code-doc-tag.doc-error {
  background: rgba(239, 68, 68, 0.15);
  border-color: var(--color-error);
}

.doc-icon {
  flex-shrink: 0;
}

.doc-name {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}

.doc-status.loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.doc-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  opacity: 0.6;
  transition: var(--transition-fast);
}

.doc-remove:hover {
  opacity: 1;
  color: var(--color-error);
}

/* 底部工具栏 */
.code-input-footer {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xs) var(--space-lg);
  background: var(--color-muted);
  border-top: 1px solid var(--color-border);
  z-index: 1;
}

.code-input-actions-left {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.code-action-btn {
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

.code-action-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.code-action-btn.active {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.code-action-btn input[type="file"] {
  display: none;
}

.upload-tooltip {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: var(--space-sm);
  padding: var(--space-sm);
  background: var(--color-foreground);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-background);
  font-size: var(--font-size-xs);
  white-space: nowrap;
  z-index: 10;
}

.code-input-actions-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.code-input-hint {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Prompt 增强动画（对齐 DeerFlow） */
.enhance-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  border-radius: inherit;
  overflow: hidden;
}

.enhance-glow {
  position: absolute;
  inset: 0;
  background: linear-gradient(45deg, rgba(59,130,246,0.1), rgba(147,51,234,0.1), rgba(59,130,246,0.1));
  background-size: 200% 200%;
  animation: glow-shift 2s linear infinite;
  border-radius: inherit;
}

@keyframes glow-shift {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.enhance-particle {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #60a5fa;
  left: var(--left);
  top: 40%;
  animation: particle-float 1.5s ease-in-out infinite;
  animation-delay: var(--delay);
}

@keyframes particle-float {
  0%, 100% { transform: translateY(0); opacity: 0; scale: 0.5; }
  50% { transform: translateY(-20px); opacity: 1; scale: 1; }
}

.enhance-fade-enter-active,
.enhance-fade-leave-active {
  transition: opacity 0.3s ease;
}
.enhance-fade-enter-from,
.enhance-fade-leave-to {
  opacity: 0;
}

/* 魔法棒按钮 */
.enhance-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  padding: 0;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-all);
}

.enhance-btn:hover:not(:disabled) {
  border-color: var(--color-terminal-keyword);
  color: var(--color-terminal-keyword);
  background: var(--color-primary-light);
}

.enhance-btn:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}

.enhance-btn.enhancing {
  border-color: var(--color-terminal-keyword);
  color: var(--color-terminal-keyword);
}

.enhance-spinner {
  animation: spin 1s linear infinite;
}

.code-generate-btn {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  white-space: nowrap;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-lg);
  background: var(--color-primary-gradient);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-inverse);
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: var(--transition-all);
  box-shadow: var(--shadow-primary);
  position: relative;
  overflow: hidden;
}

.code-generate-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.code-generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), var(--shadow-primary);
}

.code-generate-btn:hover:not(:disabled)::before {
  left: 100%;
}

.code-generate-btn:active:not(:disabled) {
  transform: translateY(0);
}

.code-generate-btn:disabled {
  opacity: var(--opacity-disabled);
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

.btn-text {
  font-family: var(--font-mono);
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .code-input-card {
    margin-bottom: var(--space-md);
  }

  .code-input-body {
    padding: var(--space-md);
  }

  .code-input-textarea {
    min-height: 60px;
    font-size: var(--font-size-sm);
  }

  .code-input-docs {
    padding: 0 var(--space-md) var(--space-sm);
  }

  .code-input-footer {
    flex-direction: column;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-md);
  }

  .code-input-actions-left,
  .code-input-actions-right {
    width: 100%;
    justify-content: space-between;
  }

  .code-generate-btn {
    width: 100%;
    justify-content: center;
    padding: var(--space-md);
  }

  .hide-mobile {
    display: none !important;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .code-input-body {
    padding: var(--space-lg);
  }
}

/* Reduce motion */
@media (prefers-reduced-motion: reduce) {
  .code-particle {
    animation: none;
  }

  .loading-spinner,
  .doc-status.loading {
    animation: none;
  }
}

/* 拖拽上传 overlay */
.drag-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg, rgba(0, 0, 0, 0.6));
  backdrop-filter: blur(8px);
  border: 2px dashed var(--color-primary);
  border-radius: inherit;
}

.drag-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
}

.drag-icon {
  color: var(--color-primary);
  animation: drag-bounce 1s ease-in-out infinite;
}

.drag-text {
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-semibold);
}

.drag-hint {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

@keyframes drag-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.drag-fade-enter-active,
.drag-fade-leave-active {
  transition: opacity 0.2s ease;
}
.drag-fade-enter-from,
.drag-fade-leave-to {
  opacity: 0;
}
</style>
