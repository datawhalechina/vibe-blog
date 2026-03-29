<template>
  <div
    class="tiptap-wrapper"
    :class="{ focused: isFocused }"
    @click="focusEditor"
  >
    <editor-content :editor="editor" class="tiptap-content" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'

interface Props {
  modelValue: string
  placeholder?: string
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '',
  disabled: false,
})
const emit = defineEmits<Emits>()

const isFocused = ref(false)

const editor = useEditor({
  content: props.modelValue || '',
  editable: !props.disabled,
  extensions: [
    StarterKit.configure({
      heading: false,
      bulletList: false,
      orderedList: false,
      blockquote: false,
      codeBlock: false,
      horizontalRule: false,
      hardBreak: {
        keepMarks: false,
      },
    }),
    Placeholder.configure({
      placeholder: props.placeholder,
    }),
  ],
  editorProps: {
    attributes: {
      class: 'prose prose-base tiptap-prose',
    },
    handleKeyDown(view, event) {
      if (event.key === 'Enter' && event.ctrlKey) {
        event.preventDefault()
        emit('submit')
        return true
      }
      return false
    },
  },
  onUpdate({ editor: ed }) {
    const text = ed.getText()
    emit('update:modelValue', text)
  },
  onFocus() {
    isFocused.value = true
  },
  onBlur() {
    isFocused.value = false
  },
})

watch(() => props.modelValue, (newVal) => {
  if (!editor.value) return
  const current = editor.value.getText()
  if (current !== newVal) {
    editor.value.commands.setContent(newVal || '')
  }
})

watch(() => props.disabled, (val) => {
  editor.value?.setEditable(!val)
})

const focusEditor = () => {
  editor.value?.commands.focus()
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})

defineExpose({ focusEditor })
</script>

<style scoped>
.tiptap-wrapper {
  flex: 1;
  min-height: 80px;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: text;
  transition: border-color 0.2s ease;
}

.tiptap-wrapper.focused {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.tiptap-content {
  width: 100%;
  height: 100%;
}

.tiptap-content :deep(.tiptap) {
  outline: none;
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  color: var(--color-foreground);
  line-height: var(--line-height-relaxed);
  min-height: 60px;
  max-height: 200px;
  overflow-y: auto;
}

.tiptap-content :deep(.tiptap p) {
  margin: 0;
}

.tiptap-content :deep(.tiptap p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--color-text-muted);
  pointer-events: none;
  height: 0;
}
</style>
