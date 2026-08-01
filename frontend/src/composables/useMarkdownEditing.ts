import {
  computed,
  getCurrentScope,
  nextTick,
  onScopeDispose,
  ref,
  type Ref,
} from 'vue'

import * as api from '@/services/api'

type MarkdownEditingService = Pick<
  typeof api,
  'polishSelectedText' | 'updateBlogContent'
>

type ProgressReporter = (message: string, type?: string) => void

interface UseMarkdownEditingOptions {
  previewContent: Ref<string>
  completedBlogId: Ref<string | null>
  savedOutputPath: Ref<string>
  addProgressItem: ProgressReporter
  service?: MarkdownEditingService
}

export type MarkdownFormat = 'bold' | 'italic' | 'code' | 'quote' | 'list'

export function useMarkdownEditing(options: UseMarkdownEditingOptions) {
  const service = options.service ?? api
  const isEditing = ref(false)
  const editableContent = ref('')
  const editAreaRef = ref<HTMLElement | null>(null)
  const editTextareaRef = ref<HTMLTextAreaElement | null>(null)
  const showPolishDialog = ref(false)
  const showSelectionToolbar = ref(false)
  const polishInstruction = ref('')
  const polishLoading = ref(false)
  const polishedText = ref('')
  const selectedText = ref('')
  const selectionRange = ref({ start: 0, end: 0 })
  const selectionToolbarPosition = ref({ top: 0, left: 0 })
  const polishRequestId = ref(0)
  let polishAbortController: AbortController | null = null

  const selectedTextPreview = computed(() => selectedText.value.trim())
  const polishedTextPreview = computed(() => polishedText.value.trim())
  const canPolish = computed(() => selectedTextPreview.value.length > 0)
  const hasSelection = computed(() => {
    const { start, end } = selectionRange.value
    return end > start
  })

  const invalidatePolishRequest = () => {
    polishRequestId.value += 1
    polishAbortController?.abort()
    polishAbortController = null
  }

  const resetSelectionState = () => {
    invalidatePolishRequest()
    showPolishDialog.value = false
    showSelectionToolbar.value = false
    polishLoading.value = false
    polishedText.value = ''
    polishInstruction.value = ''
    selectedText.value = ''
    selectionRange.value = { start: 0, end: 0 }
  }

  const toggleEdit = () => {
    if (isEditing.value) {
      resetSelectionState()
      editableContent.value = ''
      isEditing.value = false
      return
    }
    editableContent.value = options.previewContent.value
    isEditing.value = true
  }

  const closePolishDialog = () => resetSelectionState()

  const updateSelectionToolbarPosition = (start: number, end: number) => {
    const textarea = editTextareaRef.value
    const editArea = editAreaRef.value
    if (!textarea || !editArea) return

    const textareaRect = textarea.getBoundingClientRect()
    const editAreaRect = editArea.getBoundingClientRect()
    const mirror = document.createElement('div')
    const mirrorStyle = window.getComputedStyle(textarea)
    const styleKeys = [
      'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
      'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
      'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
      'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
      'fontFamily', 'lineHeight', 'letterSpacing', 'textAlign', 'textTransform',
      'textIndent', 'textDecoration', 'tabSize',
    ] as const

    mirror.style.position = 'fixed'
    mirror.style.top = `${textareaRect.top}px`
    mirror.style.left = `${textareaRect.left}px`
    mirror.style.whiteSpace = 'pre-wrap'
    mirror.style.wordBreak = 'break-word'
    mirror.style.pointerEvents = 'none'
    mirror.style.visibility = 'hidden'
    styleKeys.forEach((key) => { mirror.style[key] = mirrorStyle[key] })
    mirror.textContent = editableContent.value.slice(0, start)

    const selectedSpan = document.createElement('span')
    selectedSpan.textContent = editableContent.value.slice(start, end) || ' '
    mirror.appendChild(selectedSpan)
    document.body.appendChild(mirror)
    mirror.scrollTop = textarea.scrollTop
    mirror.scrollLeft = textarea.scrollLeft

    const selectedRect = selectedSpan.getBoundingClientRect()
    document.body.removeChild(mirror)
    const rawTop = selectedRect.top - editAreaRect.top - 12
    const rawLeft = selectedRect.left - editAreaRect.left + (selectedRect.width / 2)
    const clampedLeft = Math.min(
      Math.max(rawLeft, 72),
      Math.max(editAreaRect.width - 72, 72),
    )
    selectionToolbarPosition.value = {
      top: Math.max(rawTop, 8),
      left: clampedLeft,
    }
  }

  const handleTextSelection = async () => {
    const textarea = editTextareaRef.value
    if (!textarea) return
    const start = textarea.selectionStart ?? 0
    const end = textarea.selectionEnd ?? 0
    if (end <= start) {
      resetSelectionState()
      return
    }

    const rawSelectedText = editableContent.value.slice(start, end)
    if (!rawSelectedText.trim()) {
      resetSelectionState()
      return
    }

    selectionRange.value = { start, end }
    selectedText.value = rawSelectedText
    polishedText.value = ''
    showPolishDialog.value = false
    await nextTick()
    updateSelectionToolbarPosition(start, end)
    showSelectionToolbar.value = true
  }

  const updateSelectionAfterEdit = async (start: number, end: number) => {
    await nextTick()
    const textarea = editTextareaRef.value
    if (!textarea) return
    textarea.focus()
    textarea.setSelectionRange(start, end)
    selectionRange.value = { start, end }
    selectedText.value = editableContent.value.slice(start, end)
    updateSelectionToolbarPosition(start, end)
    showSelectionToolbar.value = true
  }

  const applyWrappedFormat = async (prefix: string, suffix = prefix) => {
    const { start, end } = selectionRange.value
    if (end <= start) return
    const selection = editableContent.value.slice(start, end)
    editableContent.value = `${editableContent.value.slice(0, start)}${prefix}${selection}${suffix}${editableContent.value.slice(end)}`
    options.previewContent.value = editableContent.value
    await updateSelectionAfterEdit(start + prefix.length, end + prefix.length)
  }

  const applyLinePrefixFormat = async (prefix: string) => {
    const { start, end } = selectionRange.value
    if (end <= start) return
    const lineStart = editableContent.value.lastIndexOf('\n', start - 1) + 1
    const selectedBlock = editableContent.value.slice(lineStart, end)
    const formattedBlock = selectedBlock
      .split('\n')
      .map((line) => `${prefix}${line}`)
      .join('\n')
    editableContent.value = `${editableContent.value.slice(0, lineStart)}${formattedBlock}${editableContent.value.slice(end)}`
    options.previewContent.value = editableContent.value
    await updateSelectionAfterEdit(lineStart, lineStart + formattedBlock.length)
  }

  const persistEditedContent = async (successMessage: string) => {
    if (!options.completedBlogId.value) {
      options.addProgressItem('无法保存编辑结果：缺少已完成的文章 ID', 'error')
      return
    }

    try {
      const result = await service.updateBlogContent(
        options.completedBlogId.value,
        editableContent.value,
        options.savedOutputPath.value || undefined,
      )
      if (!result.success) throw new Error(result.error || '保存失败')
      if (!options.savedOutputPath.value) {
        options.addProgressItem(
          `${successMessage}（已更新数据库，但由于缺少文件路径，未能将内容持久化到文件）`,
          'warning',
        )
      } else {
        options.addProgressItem(successMessage, 'success')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      options.addProgressItem(`保存编辑结果失败: ${message}`, 'error')
    }
  }

  const applyMarkdownFormat = async (type: MarkdownFormat) => {
    if (!hasSelection.value) return
    const formats = {
      bold: { apply: () => applyWrappedFormat('**'), message: '选中文本已加粗并保存' },
      italic: { apply: () => applyWrappedFormat('*'), message: '选中文本已斜体并保存' },
      code: { apply: () => applyWrappedFormat('`'), message: '选中文本已转为行内代码并保存' },
      quote: { apply: () => applyLinePrefixFormat('> '), message: '选中文本已转为引用并保存' },
      list: { apply: () => applyLinePrefixFormat('- '), message: '选中文本已转为无序列表并保存' },
    }
    await formats[type].apply()
    await persistEditedContent(formats[type].message)
  }

  const openPolishDialog = () => {
    if (!canPolish.value) return
    polishedText.value = ''
    showSelectionToolbar.value = false
    showPolishDialog.value = true
  }

  const handleEditScroll = () => {
    showSelectionToolbar.value = false
    if (showPolishDialog.value) closePolishDialog()
  }

  const handleEditInput = () => {
    options.previewContent.value = editableContent.value
    showSelectionToolbar.value = false
  }

  const isPolishRequestStillValid = (
    requestId: number,
    start: number,
    end: number,
    expectedSelectedText: string,
    expectedInstruction: string,
  ) => (
    polishRequestId.value === requestId
    && isEditing.value
    && showPolishDialog.value
    && selectionRange.value.start === start
    && selectionRange.value.end === end
    && selectedTextPreview.value === expectedSelectedText
    && polishInstruction.value.trim() === expectedInstruction
  )

  const handlePolish = async () => {
    if (!canPolish.value || polishLoading.value) return
    const requestId = polishRequestId.value + 1
    const expectedSelectedText = selectedTextPreview.value
    const expectedInstruction = polishInstruction.value.trim()
    const { start, end } = selectionRange.value
    polishRequestId.value = requestId
    polishAbortController?.abort()
    const controller = new AbortController()
    polishAbortController = controller
    polishLoading.value = true

    try {
      const result = await service.polishSelectedText(
        expectedSelectedText,
        expectedInstruction,
        controller.signal,
      )
      if (!result.success || !result.polished_text) {
        throw new Error(result.error || '润色失败')
      }
      if (!isPolishRequestStillValid(
        requestId,
        start,
        end,
        expectedSelectedText,
        expectedInstruction,
      )) return
      polishedText.value = result.polished_text
      options.addProgressItem('润色结果已生成，可确认替换', 'success')
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (
        (error instanceof Error && error.name === 'AbortError')
        || !isPolishRequestStillValid(
          requestId,
          start,
          end,
          expectedSelectedText,
          expectedInstruction,
        )
      ) return
      options.addProgressItem(`润色失败: ${message}`, 'error')
    } finally {
      if (polishRequestId.value === requestId) {
        polishLoading.value = false
        polishAbortController = null
      }
    }
  }

  const applyPolishedText = async () => {
    if (!polishedTextPreview.value) return
    const { start, end } = selectionRange.value
    const nextText = polishedTextPreview.value
    editableContent.value = `${editableContent.value.slice(0, start)}${nextText}${editableContent.value.slice(end)}`
    options.previewContent.value = editableContent.value
    resetSelectionState()
    await nextTick()
    const textarea = editTextareaRef.value
    if (textarea) {
      const cursor = start + nextText.length
      textarea.focus()
      textarea.setSelectionRange(cursor, cursor)
    }
    await persistEditedContent('选中文本已润色替换并保存')
  }

  const dispose = () => resetSelectionState()
  if (getCurrentScope()) onScopeDispose(dispose)

  return {
    isEditing,
    editableContent,
    editAreaRef,
    editTextareaRef,
    showPolishDialog,
    showSelectionToolbar,
    polishInstruction,
    polishLoading,
    polishedText,
    selectedText,
    selectionRange,
    selectionToolbarPosition,
    selectedTextPreview,
    polishedTextPreview,
    canPolish,
    toggleEdit,
    closePolishDialog,
    handleTextSelection,
    applyMarkdownFormat,
    openPolishDialog,
    handleEditScroll,
    handleEditInput,
    handlePolish,
    applyPolishedText,
    dispose,
  }
}
