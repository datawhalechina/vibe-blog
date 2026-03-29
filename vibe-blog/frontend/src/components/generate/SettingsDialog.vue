<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Settings :size="18" />
          <span>设置</span>
        </DialogTitle>
        <DialogDescription>调整模型、搜索、生成和 Agent 参数</DialogDescription>
      </DialogHeader>

      <!-- 加载态 -->
      <div v-if="loading" class="flex items-center justify-center py-16">
        <Loader2 :size="24" class="animate-spin text-muted-foreground" />
      </div>

      <!-- 设置内容 -->
      <Tabs v-else v-model="activeTab" class="flex-1 min-h-0 flex flex-col">
        <TabsList class="w-full justify-start">
          <TabsTrigger v-for="tab in tabs" :key="tab.id" :value="tab.id" class="text-xs">
            <component :is="tab.icon" :size="14" class="mr-1.5" />
            {{ tab.label }}
          </TabsTrigger>
        </TabsList>

        <div class="flex-1 overflow-y-auto py-4 space-y-1">
          <template v-for="(meta, key) in filteredSettings" :key="key">
            <!-- Bool → Switch -->
            <div v-if="meta.type === 'bool'" class="flex items-center justify-between py-2 px-1">
              <Label :for="key" class="text-sm cursor-pointer">{{ meta.label }}</Label>
              <Switch :id="key" :checked="localValues[key]" @update:checked="localValues[key] = $event" />
            </div>

            <!-- Select -->
            <div v-else-if="meta.type === 'select'" class="flex items-center justify-between py-2 px-1 gap-4">
              <Label :for="key" class="text-sm shrink-0">{{ meta.label }}</Label>
              <Select v-model="localValues[key]">
                <SelectTrigger :id="key" class="w-48 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="opt in meta.options" :key="opt" :value="opt" class="text-xs">
                    {{ opt }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- Int → Input -->
            <div v-else-if="meta.type === 'int'" class="flex items-center justify-between py-2 px-1 gap-4">
              <Label :for="key" class="text-sm shrink-0">
                {{ meta.label }}
                <span v-if="meta.min != null || meta.max != null" class="text-muted-foreground text-xs ml-1">
                  ({{ meta.min ?? '' }}–{{ meta.max ?? '' }})
                </span>
              </Label>
              <Input
                :id="key"
                type="number"
                :min="meta.min"
                :max="meta.max"
                :model-value="localValues[key]"
                @update:model-value="localValues[key] = Number($event)"
                class="w-32 h-8 text-xs"
              />
            </div>

            <!-- Str → Input -->
            <div v-else class="flex items-center justify-between py-2 px-1 gap-4">
              <Label :for="key" class="text-sm shrink-0">{{ meta.label }}</Label>
              <Input
                :id="key"
                :model-value="localValues[key]"
                @update:model-value="localValues[key] = $event"
                class="w-64 h-8 text-xs font-mono"
              />
            </div>
          </template>
        </div>
      </Tabs>

      <!-- Footer -->
      <div class="flex items-center justify-between pt-4 border-t">
        <p v-if="saveError" class="text-xs text-destructive">{{ saveError }}</p>
        <p v-else-if="saveSuccess" class="text-xs text-green-500">已保存</p>
        <span v-else />
        <div class="flex gap-2">
          <Button variant="outline" size="sm" @click="$emit('update:open', false)">取消</Button>
          <Button size="sm" :disabled="saving" @click="handleSave">
            <Loader2 v-if="saving" :size="14" class="animate-spin mr-1" />
            保存
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, markRaw } from 'vue'
import { Settings, Loader2, Cpu, Search, Zap, Bot, ToggleLeft } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface SettingMeta {
  tab: string
  type: string
  label: string
  default: any
  value: any
  options?: string[]
  min?: number
  max?: number
}

const props = defineProps<{ open: boolean }>()
defineEmits<{ (e: 'update:open', v: boolean): void }>()

const tabs = [
  { id: 'model', label: '模型', icon: markRaw(Cpu) },
  { id: 'search', label: '搜索', icon: markRaw(Search) },
  { id: 'generation', label: '生成', icon: markRaw(Zap) },
  { id: 'agent', label: 'Agent', icon: markRaw(Bot) },
  { id: 'feature', label: '功能', icon: markRaw(ToggleLeft) },
]

const activeTab = ref('model')
const loading = ref(false)
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const settingsSchema = ref<Record<string, SettingMeta>>({})
const localValues = ref<Record<string, any>>({})

const filteredSettings = computed(() => {
  const result: Record<string, SettingMeta> = {}
  for (const [key, meta] of Object.entries(settingsSchema.value)) {
    if (meta.tab === activeTab.value) {
      result[key] = meta
    }
  }
  return result
})

async function fetchSettings() {
  loading.value = true
  try {
    const resp = await fetch('/api/settings')
    const data = await resp.json()
    if (data.success) {
      settingsSchema.value = data.settings
      const vals: Record<string, any> = {}
      for (const [key, meta] of Object.entries(data.settings as Record<string, SettingMeta>)) {
        vals[key] = meta.value
      }
      localValues.value = vals
    }
  } catch (e) {
    console.error('Failed to fetch settings:', e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const resp = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(localValues.value),
    })
    const data = await resp.json()
    if (data.success) {
      saveSuccess.value = true
      setTimeout(() => { saveSuccess.value = false }, 2000)
    }
    if (data.errors?.length) {
      saveError.value = data.errors.join('; ')
    }
  } catch (e: any) {
    saveError.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

watch(() => props.open, (v) => {
  if (v) {
    fetchSettings()
    saveError.value = ''
    saveSuccess.value = false
  }
})
</script>
