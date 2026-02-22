import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useDragUpload } from '@/composables/useDragUpload'

function createDragEvent(type: string, files: File[] = []): DragEvent {
  const dt = {
    files: files,
    items: files.map(f => ({ kind: 'file', getAsFile: () => f })),
  }
  const event = new Event(type) as unknown as DragEvent
  Object.defineProperty(event, 'dataTransfer', { value: dt })
  event.preventDefault = vi.fn()
  event.stopPropagation = vi.fn()
  return event
}

function createFile(name: string): File {
  return new File(['content'], name, { type: 'application/octet-stream' })
}

describe('useDragUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('isDragging is false initially', () => {
    const { isDragging } = useDragUpload()
    expect(isDragging.value).toBe(false)
  })

  it('sets isDragging to true on dragenter', () => {
    const { isDragging, dragHandlers } = useDragUpload()
    const event = createDragEvent('dragenter')

    dragHandlers.onDragenter(event)

    expect(isDragging.value).toBe(true)
  })

  it('sets isDragging to false when all dragleave events fire', () => {
    const { isDragging, dragHandlers } = useDragUpload()

    dragHandlers.onDragenter(createDragEvent('dragenter'))
    dragHandlers.onDragenter(createDragEvent('dragenter'))
    expect(isDragging.value).toBe(true)

    dragHandlers.onDragleave(createDragEvent('dragleave'))
    expect(isDragging.value).toBe(true) // still dragging, counter = 1

    dragHandlers.onDragleave(createDragEvent('dragleave'))
    expect(isDragging.value).toBe(false) // counter = 0
  })

  it('calls onFilesDropped with valid files on drop', () => {
    const onFilesDropped = vi.fn()
    const { dragHandlers } = useDragUpload({
      allowedExts: ['pdf', 'txt'],
      onFilesDropped,
    })

    const files = [createFile('doc.pdf'), createFile('image.png'), createFile('notes.txt')]
    const event = createDragEvent('drop', files)

    dragHandlers.onDragenter(createDragEvent('dragenter'))
    dragHandlers.onDrop(event)

    expect(onFilesDropped).toHaveBeenCalledOnce()
    const droppedFiles = onFilesDropped.mock.calls[0][0] as File[]
    expect(droppedFiles).toHaveLength(2)
    expect(droppedFiles[0].name).toBe('doc.pdf')
    expect(droppedFiles[1].name).toBe('notes.txt')
  })

  it('does not call onFilesDropped when no valid files', () => {
    const onFilesDropped = vi.fn()
    const { dragHandlers } = useDragUpload({
      allowedExts: ['pdf'],
      onFilesDropped,
    })

    const files = [createFile('image.png')]
    dragHandlers.onDrop(createDragEvent('drop', files))

    expect(onFilesDropped).not.toHaveBeenCalled()
  })

  it('resets isDragging on drop', () => {
    const { isDragging, dragHandlers } = useDragUpload()

    dragHandlers.onDragenter(createDragEvent('dragenter'))
    expect(isDragging.value).toBe(true)

    dragHandlers.onDrop(createDragEvent('drop'))
    expect(isDragging.value).toBe(false)
  })

  it('prevents default on dragover', () => {
    const { dragHandlers } = useDragUpload()
    const event = createDragEvent('dragover')

    dragHandlers.onDragover(event)

    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('does not set isDragging when enabled is false', () => {
    const enabled = ref(false)
    const { isDragging, dragHandlers } = useDragUpload({ enabled })

    dragHandlers.onDragenter(createDragEvent('dragenter'))

    expect(isDragging.value).toBe(false)
  })

  it('does not call onFilesDropped when enabled is false', () => {
    const onFilesDropped = vi.fn()
    const enabled = ref(false)
    const { dragHandlers } = useDragUpload({
      allowedExts: ['pdf'],
      onFilesDropped,
      enabled,
    })

    const files = [createFile('doc.pdf')]
    dragHandlers.onDrop(createDragEvent('drop', files))

    expect(onFilesDropped).not.toHaveBeenCalled()
  })

  it('allows all files when allowedExts is empty', () => {
    const onFilesDropped = vi.fn()
    const { dragHandlers } = useDragUpload({
      allowedExts: [],
      onFilesDropped,
    })

    const files = [createFile('anything.xyz')]
    dragHandlers.onDrop(createDragEvent('drop', files))

    expect(onFilesDropped).toHaveBeenCalledOnce()
    expect(onFilesDropped.mock.calls[0][0]).toHaveLength(1)
  })
})
