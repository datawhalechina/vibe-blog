<template>
  <div class="bg-white/95 dark:bg-card border border-border rounded-xl overflow-hidden my-8 hover:border-primary/50 transition-all duration-300 hover:shadow-card-hover">
    <!-- 终端风格头部 -->
    <div class="flex items-center gap-3 px-4 py-3 bg-white/90 dark:bg-muted border-b border-border font-mono text-xs">
      <div class="flex gap-1.5">
        <span class="w-3 h-3 rounded-full bg-red-500 hover:bg-red-600 transition-colors cursor-pointer"></span>
        <span class="w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-600 transition-colors cursor-pointer"></span>
        <span class="w-3 h-3 rounded-full bg-green-500 hover:bg-green-600 transition-colors cursor-pointer"></span>
      </div>
      <span class="flex-1 text-slate-500 dark:text-muted-foreground">$ blog-output</span>
      <span class="text-green-500 font-semibold">ready</span>
    </div>

    <!-- 结果内容 -->
    <div class="p-6">
      <!-- 文章信息 -->
      <div class="mb-6 p-4 bg-primary/5 border border-primary/20 rounded-lg">
        <div class="flex items-center gap-3 mb-2 font-mono text-sm last:mb-0">
          <span class="text-primary font-semibold min-w-[80px]">$ title:</span>
          <span class="text-slate-900 dark:text-foreground flex-1">{{ blog.title }}</span>
        </div>
        <div class="flex items-center gap-3 mb-2 font-mono text-sm last:mb-0">
          <span class="text-primary font-semibold min-w-[80px]">$ type:</span>
          <span class="inline-block px-2 py-1 bg-primary/10 rounded text-xs text-slate-900 dark:text-foreground">{{ blog.type }}</span>
        </div>
        <div class="flex items-center gap-3 mb-2 font-mono text-sm last:mb-0">
          <span class="text-primary font-semibold min-w-[80px]">$ length:</span>
          <span class="text-slate-900 dark:text-foreground flex-1">{{ blog.length }} 字</span>
        </div>
        <div class="flex items-center gap-3 font-mono text-sm">
          <span class="text-primary font-semibold min-w-[80px]">$ created:</span>
          <span class="text-slate-900 dark:text-foreground flex-1">{{ formatDate(blog.createdAt) }}</span>
        </div>
      </div>

      <!-- 文章摘要 -->
      <div class="mb-6 bg-black/5 dark:bg-muted rounded-lg overflow-hidden">
        <div class="px-3 py-2 bg-black/10 dark:bg-black/20 border-b border-border font-mono">
          <span class="text-xs text-muted-foreground">$ cat summary.md</span>
        </div>
        <div class="p-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400 max-h-[150px] overflow-y-auto">
          {{ blog.summary }}
        </div>
      </div>

      <!-- 标签 -->
      <div class="flex items-start gap-3 mb-6 font-mono text-sm">
        <span class="text-primary font-semibold flex-shrink-0">$ tags:</span>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tag in blog.tags"
            :key="tag"
            class="inline-block px-3 py-1.5 bg-primary/10 border border-primary/30 rounded text-xs text-primary transition-all duration-200 hover:bg-primary/20 hover:border-primary cursor-pointer"
          >
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div class="flex flex-col gap-1.5 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg text-center">
          <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">章节数</div>
          <div class="text-xl font-bold text-blue-500 font-mono">{{ blog.sections }}</div>
        </div>
        <div class="flex flex-col gap-1.5 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg text-center">
          <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">配图数</div>
          <div class="text-xl font-bold text-blue-500 font-mono">{{ blog.images }}</div>
        </div>
        <div class="flex flex-col gap-1.5 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg text-center">
          <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">代码块</div>
          <div class="text-xl font-bold text-blue-500 font-mono">{{ blog.codeBlocks }}</div>
        </div>
        <div class="flex flex-col gap-1.5 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg text-center">
          <div class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide">阅读时间</div>
          <div class="text-xl font-bold text-blue-500 font-mono">{{ blog.readTime }}分钟</div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-3 mb-4 flex-wrap">
        <button
          class="flex-1 min-w-[100px] px-5 py-2.5 rounded-lg font-mono text-xs cursor-pointer transition-all duration-200 bg-primary/10 border border-primary text-primary hover:bg-primary/20 hover:shadow-[0_0_20px_rgba(139,92,246,0.3)]"
          @click="$emit('view')"
        >
          $ view
        </button>
        <button
          class="px-5 py-2.5 rounded-lg font-mono text-xs cursor-pointer transition-all duration-200 bg-slate-500/10 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-500/20"
          @click="$emit('edit')"
        >
          $ edit
        </button>
        <button
          class="px-5 py-2.5 rounded-lg font-mono text-xs cursor-pointer transition-all duration-200 bg-slate-500/10 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-500/20"
          @click="$emit('download')"
        >
          $ download
        </button>
        <button
          class="px-5 py-2.5 rounded-lg font-mono text-xs cursor-pointer transition-all duration-200 bg-slate-500/10 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-500/20"
          @click="$emit('share')"
        >
          $ share
        </button>
      </div>

      <!-- 代码块预览 -->
      <div v-if="showCodePreview" class="bg-black/5 dark:bg-muted rounded-lg overflow-hidden mt-4">
        <div class="flex justify-between items-center px-3 py-2 bg-black/10 dark:bg-black/20 border-b border-border font-mono">
          <span class="text-xs text-muted-foreground">$ head -20 article.md</span>
          <button
            class="bg-transparent border-none text-slate-400 text-lg cursor-pointer p-0 w-6 h-6 flex items-center justify-center transition-colors duration-200 hover:text-slate-600 dark:hover:text-slate-300"
            @click="showCodePreview = false"
          >
            ×
          </button>
        </div>
        <pre class="p-3 m-0 font-mono text-xs leading-relaxed text-slate-600 dark:text-slate-400 max-h-[200px] overflow-y-auto bg-white/50 dark:bg-slate-900/50"><code>{{ blog.content.substring(0, 500) }}...</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Blog {
  id: string
  title: string
  type: string
  length: number
  createdAt: Date
  summary: string
  tags: string[]
  sections: number
  images: number
  codeBlocks: number
  readTime: number
  content: string
}

interface Props {
  blog: Blog
}

withDefaults(defineProps<Props>(), {})

const emit = defineEmits<{
  view: []
  edit: []
  download: []
  share: []
}>()


const showCodePreview = ref(false)

const formatDate = (date: Date) => {
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>
