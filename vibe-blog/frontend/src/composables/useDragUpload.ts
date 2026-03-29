import { ref, toValue, onUnmounted } from 'vue'
import type { Ref } from 'vue'

interface UseDragUploadOptions {
  allowedExts?: string[]
  onFilesDropped?: (files: File[]) => void
  enabled?: Ref<boolean> | boolean
}

interface UseDragUploadReturn {
  isDragging: Ref<boolean>
  dragHandlers: {
    onDragover: (e: DragEvent) => void
    onDragenter: (e: DragEvent) => void
    onDragleave: (e: DragEvent) => void
    onDrop: (e: DragEvent) => void
  }
}

export function useDragUpload(options: UseDragUploadOptions = {}): UseDragUploadReturn {
  const { allowedExts = [], onFilesDropped, enabled = true } = options
  const isDragging = ref(false)
  let dragCounter = 0

  const getFileExt = (filename: string): string => {
    const dot = filename.lastIndexOf('.')
    return dot > -1 ? filename.substring(dot + 1).toLowerCase() : ''
  }

  const isAllowedFile = (file: File): boolean => {
    if (allowedExts.length === 0) return true
    return allowedExts.includes(getFileExt(file.name))
  }

  const handleDragover = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDragenter = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!toValue(enabled)) return
    dragCounter += 1
    isDragging.value = true
  }

  const handleDragleave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter -= 1
    if (dragCounter <= 0) {
      dragCounter = 0
      isDragging.value = false
    }
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounter = 0
    isDragging.value = false
    if (!toValue(enabled) || !onFilesDropped) return
    const droppedFiles = e.dataTransfer?.files
    if (!droppedFiles || droppedFiles.length === 0) return
    const validFiles: File[] = []
    for (let i = 0; i < droppedFiles.length; i++) {
      if (isAllowedFile(droppedFiles[i])) {
        validFiles.push(droppedFiles[i])
      }
    }
    if (validFiles.length > 0) {
      onFilesDropped(validFiles)
    }
  }

  onUnmounted(() => {
    dragCounter = 0
    isDragging.value = false
  })

  return {
    isDragging,
    dragHandlers: {
      onDragover: handleDragover,
      onDragenter: handleDragenter,
      onDragleave: handleDragleave,
      onDrop: handleDrop,
    },
  }
}
