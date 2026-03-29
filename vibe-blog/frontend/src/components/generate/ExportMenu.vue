<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="sm"
        class="h-8 gap-1 text-xs"
        :disabled="isDownloading || !content"
      >
        <Loader2 v-if="isDownloading" :size="14" class="animate-spin" />
        <Download v-else :size="14" />
        <span>导出</span>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-48">
      <DropdownMenuLabel class="text-xs text-muted-foreground font-mono">$ export --format</DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        v-for="fmt in formats"
        :key="fmt.id"
        class="text-xs font-mono cursor-pointer"
        @click="handleExport(fmt.id)"
      >
        <component :is="fmt.icon" :size="14" class="mr-2" />
        <span class="flex-1">{{ fmt.label }}</span>
        <span class="text-muted-foreground">{{ fmt.ext }}</span>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

<script setup lang="ts">
import { Download, Loader2, FileText, Globe, Type, FileDown, FileType } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface Props {
  content: string
  filename: string
  isDownloading?: boolean
}

withDefaults(defineProps<Props>(), {
  isDownloading: false,
})

const emit = defineEmits<{
  (e: 'export', format: string): void
}>()

const formats = [
  { id: 'markdown', label: 'Markdown', ext: '.md', icon: FileText },
  { id: 'html', label: 'HTML', ext: '.html', icon: Globe },
  { id: 'text', label: '纯文本', ext: '.txt', icon: Type },
  { id: 'pdf', label: 'PDF', ext: '.pdf', icon: FileDown },
  { id: 'word', label: 'Word', ext: '.docx', icon: FileType },
]

const handleExport = (format: string) => {
  emit('export', format)
}
</script>
