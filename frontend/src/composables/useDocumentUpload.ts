import { getCurrentScope, onScopeDispose, ref } from 'vue'

import * as api from '@/services/api'

export interface UploadedDocument {
  id: string
  filename: string
  status: string
  fileSize?: number
  wordCount?: number
  errorMessage?: string
}

type DocumentUploadService = Pick<
  typeof api,
  'uploadDocument' | 'getDocumentStatus'
>

interface UseDocumentUploadOptions {
  service?: DocumentUploadService
  onError?: (message: string) => void
  pollIntervalMs?: number
  maxAttempts?: number
}

let temporaryId = 0

export function useDocumentUpload(options: UseDocumentUploadOptions = {}) {
  const service = options.service ?? api
  const onError = options.onError ?? (() => undefined)
  const pollIntervalMs = options.pollIntervalMs ?? 2_000
  const maxAttempts = options.maxAttempts ?? 60
  const uploadedDocuments = ref<UploadedDocument[]>([])
  const pollTimers = new Map<string, ReturnType<typeof setTimeout>>()
  let disposed = false

  const clearPoll = (documentId: string) => {
    const timer = pollTimers.get(documentId)
    if (timer) clearTimeout(timer)
    pollTimers.delete(documentId)
  }

  const updateDocument = (
    documentId: string,
    status: string,
    wordCount?: number,
    errorMessage?: string,
  ) => {
    const document = uploadedDocuments.value.find(({ id }) => id === documentId)
    if (!document) return
    document.status = status
    if (wordCount !== undefined) document.wordCount = wordCount
    if (errorMessage) document.errorMessage = errorMessage
  }

  const pollDocumentStatus = async (documentId: string, attempt = 0) => {
    if (disposed || !uploadedDocuments.value.some(({ id }) => id === documentId)) return
    if (attempt >= maxAttempts) {
      updateDocument(documentId, 'timeout')
      clearPoll(documentId)
      return
    }

    try {
      const data = await service.getDocumentStatus(documentId)
      if (data.success) {
        const status = data.status || 'pending'
        updateDocument(
          documentId,
          status,
          data.markdown_length,
          data.error_message,
        )
        if (status === 'ready' || status === 'error') {
          clearPoll(documentId)
          return
        }
      }
    } catch (error) {
      console.error('Poll document status error:', error)
    }

    if (disposed || !uploadedDocuments.value.some(({ id }) => id === documentId)) return

    const timer = setTimeout(
      () => void pollDocumentStatus(documentId, attempt + 1),
      pollIntervalMs,
    )
    pollTimers.set(documentId, timer)
  }

  const uploadDocument = async (file: File) => {
    const tempId = `temp_${Date.now()}_${temporaryId++}`
    uploadedDocuments.value.push({
      id: tempId,
      filename: file.name,
      status: 'uploading',
      fileSize: file.size,
    })

    try {
      const data = await service.uploadDocument(file)
      uploadedDocuments.value = uploadedDocuments.value.filter(
        ({ id }) => id !== tempId,
      )
      if (!data.success || !data.document_id) {
        onError(`上传失败: ${data.error || '未知错误'}`)
        return
      }

      uploadedDocuments.value.push({
        id: data.document_id,
        filename: data.filename || file.name,
        status: data.status || 'pending',
        fileSize: file.size,
      })
      void pollDocumentStatus(data.document_id)
    } catch (error) {
      uploadedDocuments.value = uploadedDocuments.value.filter(
        ({ id }) => id !== tempId,
      )
      const message = error instanceof Error ? error.message : String(error)
      onError(`上传失败: ${message}`)
    }
  }

  const handleFileUpload = async (files: FileList) => {
    for (const file of Array.from(files)) await uploadDocument(file)
  }

  const removeDocument = (documentId: string) => {
    clearPoll(documentId)
    uploadedDocuments.value = uploadedDocuments.value.filter(
      ({ id }) => id !== documentId,
    )
  }

  const getReadyDocumentIds = () =>
    uploadedDocuments.value
      .filter(({ status }) => status === 'ready')
      .map(({ id }) => id)

  const dispose = () => {
    disposed = true
    for (const documentId of pollTimers.keys()) clearPoll(documentId)
  }

  if (getCurrentScope()) onScopeDispose(dispose)

  return {
    uploadedDocuments,
    handleFileUpload,
    uploadDocument,
    removeDocument,
    getReadyDocumentIds,
    dispose,
  }
}
