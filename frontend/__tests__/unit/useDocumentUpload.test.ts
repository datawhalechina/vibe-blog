import { effectScope, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useDocumentUpload } from '@/composables/useDocumentUpload'

const createFile = () => new File(['content'], 'notes.md', { type: 'text/markdown' })

describe('useDocumentUpload', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('replaces the temporary upload with a polled ready document', async () => {
    const service = {
      uploadDocument: vi.fn().mockResolvedValue({
        success: true,
        document_id: 'doc-1',
        filename: 'notes.md',
        status: 'pending',
      }),
      getDocumentStatus: vi.fn().mockResolvedValue({
        success: true,
        status: 'ready',
        markdown_length: 420,
      }),
    }
    const uploads = useDocumentUpload({ service })

    const upload = uploads.uploadDocument(createFile())
    expect(uploads.uploadedDocuments.value[0]).toMatchObject({
      filename: 'notes.md',
      status: 'uploading',
    })
    await upload
    await nextTick()

    expect(uploads.uploadedDocuments.value).toEqual([
      expect.objectContaining({
        id: 'doc-1',
        status: 'ready',
        wordCount: 420,
      }),
    ])
    expect(uploads.getReadyDocumentIds()).toEqual(['doc-1'])
  })

  it('removes failed temporary uploads and reports the existing message', async () => {
    const onError = vi.fn()
    const service = {
      uploadDocument: vi.fn().mockResolvedValue({
        success: false,
        error: 'unsupported file',
      }),
      getDocumentStatus: vi.fn(),
    }
    const uploads = useDocumentUpload({ service, onError })

    await uploads.uploadDocument(createFile())

    expect(uploads.uploadedDocuments.value).toEqual([])
    expect(onError).toHaveBeenCalledWith('上传失败: unsupported file')
  })

  it('removes documents and cancels their pending poll timer', async () => {
    vi.useFakeTimers()
    const service = {
      uploadDocument: vi.fn().mockResolvedValue({
        success: true,
        document_id: 'doc-1',
        status: 'pending',
      }),
      getDocumentStatus: vi.fn().mockResolvedValue({
        success: true,
        status: 'pending',
      }),
    }
    const uploads = useDocumentUpload({
      service,
      pollIntervalMs: 2_000,
    })

    await uploads.uploadDocument(createFile())
    await nextTick()
    uploads.removeDocument('doc-1')
    await vi.advanceTimersByTimeAsync(4_000)

    expect(uploads.uploadedDocuments.value).toEqual([])
    expect(service.getDocumentStatus).toHaveBeenCalledOnce()
  })

  it('clears pending poll timers when its effect scope stops', async () => {
    vi.useFakeTimers()
    const service = {
      uploadDocument: vi.fn().mockResolvedValue({
        success: true,
        document_id: 'doc-1',
        status: 'pending',
      }),
      getDocumentStatus: vi.fn().mockResolvedValue({
        success: true,
        status: 'pending',
      }),
    }
    const scope = effectScope()
    const uploads = scope.run(() =>
      useDocumentUpload({ service, pollIntervalMs: 2_000 }),
    )!

    await uploads.uploadDocument(createFile())
    await nextTick()
    scope.stop()
    await vi.advanceTimersByTimeAsync(4_000)

    expect(service.getDocumentStatus).toHaveBeenCalledOnce()
  })

  it('does not schedule another poll when an in-flight status request resolves after disposal', async () => {
    vi.useFakeTimers()
    let resolveStatus!: (value: { success: boolean; status: string }) => void
    const service = {
      uploadDocument: vi.fn().mockResolvedValue({
        success: true,
        document_id: 'doc-1',
        status: 'pending',
      }),
      getDocumentStatus: vi.fn().mockImplementation(
        () => new Promise((resolve) => {
          resolveStatus = resolve
        }),
      ),
    }
    const scope = effectScope()
    const uploads = scope.run(() =>
      useDocumentUpload({ service, pollIntervalMs: 2_000 }),
    )!

    await uploads.uploadDocument(createFile())
    scope.stop()
    resolveStatus({ success: true, status: 'pending' })
    await Promise.resolve()
    await vi.advanceTimersByTimeAsync(4_000)

    expect(service.getDocumentStatus).toHaveBeenCalledOnce()
  })
})
