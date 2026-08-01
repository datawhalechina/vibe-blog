import { effectScope, ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMarkdownEditing } from '@/composables/useMarkdownEditing'

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function createEditor(overrides: Record<string, unknown> = {}) {
  const previewContent = ref('hello world')
  const completedBlogId = ref<string | null>('blog-1')
  const savedOutputPath = ref('/tmp/blog.md')
  const addProgressItem = vi.fn()
  const service = {
    updateBlogContent: vi.fn().mockResolvedValue({ success: true }),
    polishSelectedText: vi.fn().mockResolvedValue({
      success: true,
      polished_text: 'polished text',
    }),
  }
  const editor = useMarkdownEditing({
    previewContent,
    completedBlogId,
    savedOutputPath,
    addProgressItem,
    service,
    ...overrides,
  })
  return {
    editor,
    previewContent,
    completedBlogId,
    savedOutputPath,
    addProgressItem,
    service,
  }
}

describe('useMarkdownEditing', () => {
  afterEach(() => vi.restoreAllMocks())

  it('enters editing with the preview and cancels back to a clean state', () => {
    const { editor } = createEditor()

    editor.toggleEdit()
    expect(editor.isEditing.value).toBe(true)
    expect(editor.editableContent.value).toBe('hello world')

    editor.selectedText.value = 'hello'
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.toggleEdit()

    expect(editor.isEditing.value).toBe(false)
    expect(editor.editableContent.value).toBe('')
    expect(editor.selectedText.value).toBe('')
  })

  it('formats wrapped Markdown and persists the exact current content', async () => {
    const { editor, previewContent, service } = createEditor()
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }

    await editor.applyMarkdownFormat('bold')

    expect(editor.editableContent.value).toBe('**hello** world')
    expect(previewContent.value).toBe('**hello** world')
    expect(service.updateBlogContent).toHaveBeenCalledWith(
      'blog-1',
      '**hello** world',
      '/tmp/blog.md',
    )
  })

  it('formats each selected line and persists without a saved path', async () => {
    const { editor, previewContent, savedOutputPath, addProgressItem, service } = createEditor()
    previewContent.value = 'first\nsecond'
    savedOutputPath.value = ''
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 12 }

    await editor.applyMarkdownFormat('quote')

    expect(editor.editableContent.value).toBe('> first\n> second')
    expect(service.updateBlogContent).toHaveBeenCalledWith(
      'blog-1',
      '> first\n> second',
      undefined,
    )
    expect(addProgressItem).toHaveBeenCalledWith(
      expect.stringContaining('未能将内容持久化到文件'),
      'warning',
    )
  })

  it('reports the existing error when persistence has no completed blog ID', async () => {
    const { editor, completedBlogId, addProgressItem, service } = createEditor()
    completedBlogId.value = null
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }

    await editor.applyMarkdownFormat('italic')

    expect(service.updateBlogContent).not.toHaveBeenCalled()
    expect(addProgressItem).toHaveBeenCalledWith(
      '无法保存编辑结果：缺少已完成的文章 ID',
      'error',
    )
  })

  it('reports persistence API failures through progress', async () => {
    const service = {
      updateBlogContent: vi.fn().mockResolvedValue({
        success: false,
        error: 'write failed',
      }),
      polishSelectedText: vi.fn(),
    }
    const { editor, addProgressItem } = createEditor({ service })
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }

    await editor.applyMarkdownFormat('code')

    expect(addProgressItem).toHaveBeenCalledWith(
      '保存编辑结果失败: write failed',
      'error',
    )
  })

  it('generates a polish preview and applies it only after confirmation', async () => {
    const { editor, previewContent, service } = createEditor()
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.selectedText.value = 'hello'
    editor.openPolishDialog()
    editor.polishInstruction.value = 'shorter'

    await editor.handlePolish()
    expect(service.polishSelectedText).toHaveBeenCalledWith(
      'hello',
      'shorter',
      expect.any(AbortSignal),
    )
    expect(editor.polishedTextPreview.value).toBe('polished text')
    expect(previewContent.value).toBe('hello world')

    await editor.applyPolishedText()
    expect(previewContent.value).toBe('polished text world')
    expect(service.updateBlogContent).toHaveBeenCalledWith(
      'blog-1',
      'polished text world',
      '/tmp/blog.md',
    )
  })

  it('ignores a polish response after the dialog is closed', async () => {
    const deferred = createDeferred<{ success: boolean; polished_text: string }>()
    const service = {
      updateBlogContent: vi.fn(),
      polishSelectedText: vi.fn().mockReturnValue(deferred.promise),
    }
    const { editor, addProgressItem } = createEditor({ service })
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.selectedText.value = 'hello'
    editor.openPolishDialog()

    const request = editor.handlePolish()
    editor.closePolishDialog()
    deferred.resolve({ success: true, polished_text: 'late result' })
    await request

    expect(editor.polishedText.value).toBe('')
    expect(addProgressItem).not.toHaveBeenCalledWith(
      '润色结果已生成，可确认替换',
      'success',
    )
  })

  it('ignores a polish response after the instruction changes', async () => {
    const deferred = createDeferred<{ success: boolean; polished_text: string }>()
    const service = {
      updateBlogContent: vi.fn(),
      polishSelectedText: vi.fn().mockReturnValue(deferred.promise),
    }
    const { editor, addProgressItem } = createEditor({ service })
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.selectedText.value = 'hello'
    editor.polishInstruction.value = 'formal'
    editor.openPolishDialog()

    const request = editor.handlePolish()
    editor.polishInstruction.value = 'shorter'
    deferred.resolve({ success: true, polished_text: 'late result' })
    await request

    expect(editor.polishedText.value).toBe('')
    expect(addProgressItem).not.toHaveBeenCalledWith(
      '润色结果已生成，可确认替换',
      'success',
    )
  })

  it('reports polish API failures through progress', async () => {
    const service = {
      updateBlogContent: vi.fn(),
      polishSelectedText: vi.fn().mockResolvedValue({
        success: false,
        error: 'model unavailable',
      }),
    }
    const { editor, addProgressItem } = createEditor({ service })
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.selectedText.value = 'hello'
    editor.openPolishDialog()

    await editor.handlePolish()

    expect(addProgressItem).toHaveBeenCalledWith(
      '润色失败: model unavailable',
      'error',
    )
  })

  it('aborts an active polish request when its scope is disposed', async () => {
    let requestSignal: AbortSignal | undefined
    const service = {
      updateBlogContent: vi.fn(),
      polishSelectedText: vi.fn().mockImplementation(
        (_text: string, _instruction: string, signal?: AbortSignal) => {
          requestSignal = signal
          return new Promise(() => undefined)
        },
      ),
    }
    const scope = effectScope()
    const editor = scope.run(() => createEditor({ service }).editor)!
    editor.toggleEdit()
    editor.selectionRange.value = { start: 0, end: 5 }
    editor.selectedText.value = 'hello'
    editor.openPolishDialog()

    void editor.handlePolish()
    scope.stop()

    expect(requestSignal?.aborted).toBe(true)
  })
})
