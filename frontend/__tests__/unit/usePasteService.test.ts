import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { usePasteService } from '@/composables/usePasteService'

function createFile(name: string): File {
  return new File(['content'], name, { type: 'application/octet-stream' })
}

function createPasteEvent(files: File[]): ClipboardEvent {
  const clipboardData = {
    files: files,
    items: files.map(f => ({ kind: 'file', getAsFile: () => f })),
  }
  const event = new Event('paste') as unknown as ClipboardEvent
  Object.defineProperty(event, 'clipboardData', { value: clipboardData })
  event.preventDefault = vi.fn()
  event.stopPropagation = vi.fn()
  return event
}

describe('usePasteService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns onPaste handler', () => {
    const { onPaste } = usePasteService()
    expect(typeof onPaste).toBe('function')
  })

  it('calls onFilesPasted with valid files', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf', 'md'],
      onFilesPasted,
    })

    const files = [createFile('doc.pdf'), createFile('notes.md')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(onFilesPasted).toHaveBeenCalledOnce()
    const pastedFiles = onFilesPasted.mock.calls[0][0] as File[]
    expect(pastedFiles).toHaveLength(2)
  })

  it('filters out files with disallowed extensions', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
    })

    const files = [createFile('doc.pdf'), createFile('image.png')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(onFilesPasted).toHaveBeenCalledOnce()
    const pastedFiles = onFilesPasted.mock.calls[0][0] as File[]
    expect(pastedFiles).toHaveLength(1)
    expect(pastedFiles[0].name).toBe('doc.pdf')
  })

  it('does not call onFilesPasted when no valid files', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
    })

    const files = [createFile('image.png')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(onFilesPasted).not.toHaveBeenCalled()
  })

  it('prevents default when files are pasted', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
    })

    const files = [createFile('doc.pdf')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('still prevents default when files exist but none match extensions', () => {
    // Implementation calls preventDefault as soon as clipboard has files,
    // before filtering by extension. This prevents the browser from handling
    // the paste even if no files pass the filter.
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
    })

    const files = [createFile('image.png')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(event.preventDefault).toHaveBeenCalled()
    expect(onFilesPasted).not.toHaveBeenCalled()
  })

  it('does nothing when enabled is false', () => {
    const onFilesPasted = vi.fn()
    const enabled = ref(false)
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
      enabled,
    })

    const files = [createFile('doc.pdf')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(onFilesPasted).not.toHaveBeenCalled()
  })

  it('allows all files when allowedExts is empty', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: [],
      onFilesPasted,
    })

    const files = [createFile('anything.xyz')]
    const event = createPasteEvent(files)

    onPaste(event)

    expect(onFilesPasted).toHaveBeenCalledOnce()
  })

  it('does nothing when no clipboardData files', () => {
    const onFilesPasted = vi.fn()
    const { onPaste } = usePasteService({
      allowedExts: ['pdf'],
      onFilesPasted,
    })

    const event = createPasteEvent([])
    onPaste(event)

    expect(onFilesPasted).not.toHaveBeenCalled()
  })
})
