import { toValue } from 'vue'
import type { Ref } from 'vue'

interface UsePasteServiceOptions {
  allowedExts?: string[]
  onFilesPasted?: (files: File[]) => void
  enabled?: Ref<boolean> | boolean
}

interface UsePasteServiceReturn {
  onPaste: (e: ClipboardEvent) => void
}

export function usePasteService(options: UsePasteServiceOptions = {}): UsePasteServiceReturn {
  const { allowedExts = [], onFilesPasted, enabled = true } = options

  const getFileExt = (filename: string): string => {
    const dot = filename.lastIndexOf('.')
    return dot > -1 ? filename.substring(dot + 1).toLowerCase() : ''
  }

  const isAllowedFile = (file: File): boolean => {
    if (allowedExts.length === 0) return true
    return allowedExts.includes(getFileExt(file.name))
  }

  const onPaste = (e: ClipboardEvent) => {
    if (!toValue(enabled)) return
    const files = e.clipboardData?.files
    if (files && files.length > 0 && onFilesPasted) {
      e.preventDefault()
      e.stopPropagation()
      const validFiles: File[] = []
      for (let i = 0; i < files.length; i++) {
        if (isAllowedFile(files[i])) {
          validFiles.push(files[i])
        }
      }
      if (validFiles.length > 0) {
        onFilesPasted(validFiles)
      }
    }
  }

  return { onPaste }
}
