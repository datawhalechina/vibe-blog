<template>
  <Dialog :open="visible" @update:open="(v: boolean) => { if (!v) $emit('close') }">
    <DialogContent class="max-w-md max-h-[80vh] overflow-y-auto font-mono">
      <DialogHeader>
        <DialogTitle class="sr-only">质量评估</DialogTitle>
        <DialogDescription class="sr-only">文章质量评估结果</DialogDescription>
      </DialogHeader>

      <!-- 加载态 -->
      <div v-if="loading" class="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
        <Loader2 :size="20" class="animate-spin" />
        <span class="font-mono">$ evaluate --verbose</span>
      </div>

      <!-- 评估结果 -->
      <template v-else-if="evaluation">
        <!-- 等级 + 总分 -->
        <div class="flex items-center gap-3 mb-4">
          <Badge :class="gradeVariant" class="text-lg font-bold px-3 py-1">{{ evaluation.grade }}</Badge>
          <span class="text-lg font-semibold">{{ evaluation.overall_score }}/100</span>
        </div>

        <!-- 6 维度评分 -->
        <div class="space-y-2 mb-4">
          <div v-for="(label, key) in scoreLabels" :key="key" class="flex items-center gap-2 text-xs">
            <span class="min-w-16 text-muted-foreground">{{ label }}</span>
            <Progress :model-value="evaluation.scores[key]" class="h-2 flex-1" />
            <span class="min-w-9 text-right text-muted-foreground">{{ evaluation.scores[key] }}%</span>
          </div>
        </div>

        <!-- 统计信息 -->
        <Separator />
        <div class="flex flex-wrap gap-4 py-3 text-xs text-muted-foreground">
          <span>📝 {{ evaluation.word_count }} 字</span>
          <span>📎 {{ evaluation.citation_count }} 引用</span>
          <span>🖼️ {{ evaluation.image_count }} 图片</span>
          <span>💻 {{ evaluation.code_block_count }} 代码块</span>
        </div>
        <Separator />

        <!-- 优点 -->
        <div v-if="evaluation.strengths?.length" class="mt-4 space-y-1">
          <div class="text-xs font-semibold text-green-500">✓ 优点</div>
          <div v-for="(item, i) in evaluation.strengths" :key="i" class="text-xs text-muted-foreground pl-4">{{ item }}</div>
        </div>

        <!-- 不足 -->
        <div v-if="evaluation.weaknesses?.length" class="mt-4 space-y-1">
          <div class="text-xs font-semibold text-red-500">✗ 不足</div>
          <div v-for="(item, i) in evaluation.weaknesses" :key="i" class="text-xs text-muted-foreground pl-4">{{ item }}</div>
        </div>

        <!-- 建议 -->
        <div v-if="evaluation.suggestions?.length" class="mt-4 space-y-1">
          <div class="text-xs font-semibold text-primary">→ 建议</div>
          <div v-for="(item, i) in evaluation.suggestions" :key="i" class="text-xs text-muted-foreground pl-4">{{ item }}</div>
        </div>

        <!-- 总结 -->
        <Separator class="mt-4" />
        <p class="text-xs text-muted-foreground leading-relaxed pt-3">{{ evaluation.summary }}</p>
      </template>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loader2 } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'

interface Scores {
  factual_accuracy: number
  completeness: number
  coherence: number
  relevance: number
  citation_quality: number
  writing_quality: number
}

interface Evaluation {
  grade: string
  overall_score: number
  scores: Scores
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  summary: string
  word_count: number
  citation_count: number
  image_count: number
  code_block_count: number
}

interface Props {
  visible: boolean
  evaluation: Evaluation | null
  loading: boolean
}

const props = defineProps<Props>()
defineEmits<{ (e: 'close'): void }>()

const scoreLabels: Record<string, string> = {
  factual_accuracy: '事实准确',
  completeness: '内容完整',
  coherence: '逻辑连贯',
  relevance: '主题相关',
  citation_quality: '引用质量',
  writing_quality: '写作质量',
}

const gradeVariant = computed(() => {
  const grade = props.evaluation?.grade || ''
  if (grade.startsWith('A')) return 'bg-green-500 text-white hover:bg-green-500'
  if (grade.startsWith('B')) return 'bg-blue-500 text-white hover:bg-blue-500'
  if (grade.startsWith('C')) return 'bg-yellow-500 text-white hover:bg-yellow-500'
  return 'bg-red-500 text-white hover:bg-red-500'
})
</script>
