<template>
  <div class="advanced-options-panel">
    <div class="options-row">
      <!-- 文章类型 -->
      <div class="option-item">
        <span class="option-label">
          <FileText :size="14" /> 文章类型:
        </span>
        <select v-model="localArticleType" :disabled="isLoading">
          <option value="tutorial">教程型</option>
          <option value="problem-solution">问题解决</option>
          <option value="comparison">对比分析</option>
          <option value="storybook">科普绘本</option>
        </select>
      </div>

      <!-- 文章长度 -->
      <div class="option-item">
        <span class="option-label">
          <File :size="14" /> 文章长度:
        </span>
        <select v-model="localTargetLength" :disabled="isLoading">
          <option value="mini">快速 Mini</option>
          <option value="short">短文</option>
          <option value="medium">中等</option>
          <option value="long">长文</option>
          <option value="custom">自定义</option>
        </select>
      </div>

      <!-- 受众适配 -->
      <div class="option-item">
        <span class="option-label">
          <Users :size="14" /> 受众适配:
        </span>
        <select v-model="localAudienceAdaptation" :disabled="isLoading">
          <option value="default">默认风格</option>
          <option value="high-school">高中生版</option>
          <option value="children">儿童版</option>
          <option value="professional">职场版</option>
        </select>
      </div>

      <!-- 配图风格 -->
      <div class="option-item">
        <span class="option-label">
          <Palette :size="14" /> 配图风格:
        </span>
        <select v-model="localImageStyle" :disabled="isLoading">
          <option v-for="style in imageStyles" :key="style.id" :value="style.id">
            {{ style.icon }} {{ style.name }}
          </option>
        </select>
      </div>

      <!-- 生成封面动画 -->
      <div v-if="appConfig.features?.cover_video" class="option-item checkbox-item">
        <label>
          <input type="checkbox" v-model="localGenerateCoverVideo" :disabled="isLoading">
          <Video :size="14" />
          <span>生成封面动画</span>
        </label>
        <span class="option-hint" title="将封面图转换为循环播放的动画视频（约需 2-5 分钟）">ⓘ</span>
      </div>

      <!-- 视频尺寸 -->
      <div v-if="localGenerateCoverVideo" class="option-item">
        <span class="option-label">
          <Monitor :size="14" /> 视频尺寸:
        </span>
        <select v-model="localVideoAspectRatio" :disabled="isLoading">
          <option value="16:9">横屏(16:9)</option>
          <option value="9:16">竖屏(9:16)</option>
        </select>
      </div>

      <!-- 背景调查 -->
      <div class="option-item checkbox-item">
        <label>
          <input type="checkbox" v-model="localBackgroundInvestigation" :disabled="isLoading">
          <Search :size="14" />
          <span>背景调查</span>
        </label>
        <span class="option-hint" title="生成前先搜索相关资料，关闭可加速但可能降低内容丰富度">ⓘ</span>
      </div>

      <!-- 深度思考 -->
      <div class="option-item checkbox-item">
        <label>
          <input type="checkbox" v-model="localDeepThinking" :disabled="isLoading">
          <Brain :size="14" />
          <span>深度思考</span>
        </label>
        <span class="option-hint" title="启用后 LLM 会进行更深入的推理，生成时间约增加 2-3 倍">ⓘ</span>
      </div>

      <!-- 交互式生成 -->
      <div class="option-item checkbox-item">
        <label>
          <input type="checkbox" v-model="localInteractive" :disabled="isLoading">
          <MessageSquare :size="14" />
          <span>交互式生成</span>
        </label>
        <span class="option-hint" title="大纲生成后暂停等待确认，可以审核和修改大纲后再开始写作">ⓘ</span>
      </div>
    </div>

    <!-- 自定义配置面板 -->
    <div v-if="localTargetLength === 'custom'" class="custom-config-panel">
      <div class="custom-config-title">
        <Settings :size="14" /> 自定义配置
      </div>
      <div class="custom-config-row">
        <div class="custom-item">
          <label>章节数:</label>
          <input
            type="number"
            v-model.number="localCustomConfig.sectionsCount"
            min="1"
            max="12"
          >
        </div>
        <div class="custom-item">
          <label>配图数:</label>
          <input
            type="number"
            v-model.number="localCustomConfig.imagesCount"
            min="0"
            max="20"
          >
        </div>
        <div class="custom-item">
          <label>代码块:</label>
          <input
            type="number"
            v-model.number="localCustomConfig.codeBlocksCount"
            min="0"
            max="10"
          >
        </div>
        <div class="custom-item">
          <label>目标字数:</label>
          <input
            type="number"
            v-model.number="localCustomConfig.targetWordCount"
            min="300"
            max="15000"
            step="500"
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FileText, File, Users, Palette, Video, Monitor, Settings, Search, Brain, MessageSquare } from 'lucide-vue-next'

interface CustomConfig {
  sectionsCount: number
  imagesCount: number
  codeBlocksCount: number
  targetWordCount: number
}

interface ImageStyle {
  id: string
  name: string
  icon: string
}

interface Props {
  articleType: string
  targetLength: string
  audienceAdaptation: string
  imageStyle: string
  generateCoverVideo: boolean
  videoAspectRatio: string
  deepThinking: boolean
  backgroundInvestigation: boolean
  interactive: boolean
  isLoading?: boolean
  customConfig: CustomConfig
  imageStyles: ImageStyle[]
  appConfig: {
    features?: Record<string, boolean>
  }
}

interface Emits {
  (e: 'update:articleType', value: string): void
  (e: 'update:targetLength', value: string): void
  (e: 'update:audienceAdaptation', value: string): void
  (e: 'update:imageStyle', value: string): void
  (e: 'update:generateCoverVideo', value: boolean): void
  (e: 'update:videoAspectRatio', value: string): void
  (e: 'update:deepThinking', value: boolean): void
  (e: 'update:backgroundInvestigation', value: boolean): void
  (e: 'update:interactive', value: boolean): void
  (e: 'update:customConfig', value: CustomConfig): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Two-way binding with v-model
const localArticleType = computed({
  get: () => props.articleType,
  set: (value) => emit('update:articleType', value)
})

const localTargetLength = computed({
  get: () => props.targetLength,
  set: (value) => emit('update:targetLength', value)
})

const localAudienceAdaptation = computed({
  get: () => props.audienceAdaptation,
  set: (value) => emit('update:audienceAdaptation', value)
})

const localImageStyle = computed({
  get: () => props.imageStyle,
  set: (value) => emit('update:imageStyle', value)
})

const localGenerateCoverVideo = computed({
  get: () => props.generateCoverVideo,
  set: (value) => emit('update:generateCoverVideo', value)
})

const localVideoAspectRatio = computed({
  get: () => props.videoAspectRatio,
  set: (value) => emit('update:videoAspectRatio', value)
})

const localDeepThinking = computed({
  get: () => props.deepThinking,
  set: (value) => emit('update:deepThinking', value)
})

const localBackgroundInvestigation = computed({
  get: () => props.backgroundInvestigation,
  set: (value) => emit('update:backgroundInvestigation', value)
})

const localInteractive = computed({
  get: () => props.interactive,
  set: (value) => emit('update:interactive', value)
})

const localCustomConfig = computed({
  get: () => props.customConfig,
  set: (value) => emit('update:customConfig', value)
})
</script>

<style scoped>
.advanced-options-panel {
  width: 100%;
  margin: 0 0 var(--space-md) 0;
  padding: var(--space-md);
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-sizing: border-box;
  transition: var(--transition-colors);
}

.options-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.option-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.option-label {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.option-item select,
.option-item input[type="number"] {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  cursor: pointer;
  outline: none;
  min-width: 100px;
  font-family: var(--font-mono);
  transition: var(--transition-all);
}

.option-item select:hover,
.option-item input[type="number"]:hover {
  border-color: var(--color-border-hover);
}

.option-item select:focus,
.option-item input[type="number"]:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.checkbox-item label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.checkbox-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

.option-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  cursor: help;
}

/* 自定义配置 */
.custom-config-panel {
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-input);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.custom-config-title {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-sm);
  font-style: italic;
}

.custom-config-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-md);
}

.custom-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.custom-item label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.custom-item input[type="number"] {
  width: 100%;
  min-width: 0;
}

/* Mobile Responsive */
@media (max-width: 767px) {
  .advanced-options-panel {
    margin: 0 var(--space-md) var(--space-md);
    padding: var(--space-sm);
  }

  .options-row {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-sm);
  }

  .option-item {
    width: 100%;
    justify-content: space-between;
  }

  .option-item select,
  .option-item input[type="number"] {
    flex: 1;
    min-width: 0;
  }

  .custom-config-row {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .options-row {
    gap: var(--space-sm);
  }

  .custom-config-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
