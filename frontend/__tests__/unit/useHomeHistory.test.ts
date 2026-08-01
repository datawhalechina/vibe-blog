import { describe, expect, it, vi } from 'vitest'

import { useHomeHistory } from '@/composables/useHomeHistory'

const record = (id: string, contentType = 'blog') => ({
  id,
  topic: `Topic ${id}`,
  content_type: contentType,
  created_at: '2026-08-01T00:00:00Z',
})

describe('useHomeHistory', () => {
  it('replaces the first page and appends later pages', async () => {
    const service = {
      getHistory: vi.fn()
        .mockResolvedValueOnce({
          success: true,
          records: [record('1')],
          total: 2,
          page: 1,
          page_size: 12,
          total_pages: 2,
        })
        .mockResolvedValueOnce({
          success: true,
          records: [record('2')],
          total: 2,
          page: 2,
          page_size: 12,
          total_pages: 2,
        }),
      getHistoryRecord: vi.fn(),
    }
    const history = useHomeHistory({ service, router: { push: vi.fn() } })

    await history.loadHistory()
    await history.loadMoreHistory()

    expect(history.historyRecords.value.map(({ id }) => id)).toEqual(['1', '2'])
    expect(history.historyCurrentPage.value).toBe(2)
    expect(service.getHistory).toHaveBeenNthCalledWith(2, {
      page: 2,
      page_size: 12,
      content_type: undefined,
    })
  })

  it('reloads page one when filtering or returning to the blogs tab', async () => {
    const service = {
      getHistory: vi.fn().mockResolvedValue({
        success: true,
        records: [],
        total: 0,
        page: 1,
        page_size: 12,
        total_pages: 1,
      }),
      getHistoryRecord: vi.fn(),
    }
    const history = useHomeHistory({ service, router: { push: vi.fn() } })

    await history.filterByContentType('xhs')
    await history.switchHistoryTab('xhs')
    await history.switchHistoryTab('blogs')

    expect(history.historyContentType.value).toBe('xhs')
    expect(history.currentHistoryTab.value).toBe('blogs')
    expect(service.getHistory).toHaveBeenCalledTimes(2)
    expect(service.getHistory).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 12,
      content_type: 'xhs',
    })
  })

  it.each([
    ['blog', '/blog/history-1'],
    ['xhs', '/xhs?history_id=history-1'],
  ])('opens %s history at the existing destination', async (contentType, path) => {
    const push = vi.fn()
    const service = {
      getHistory: vi.fn(),
      getHistoryRecord: vi.fn().mockResolvedValue({
        success: true,
        record: record('history-1', contentType),
      }),
    }
    const history = useHomeHistory({ service, router: { push } })

    await history.loadHistoryDetail('history-1')

    expect(push).toHaveBeenCalledWith(path)
  })

  it('keeps API failures non-fatal', async () => {
    const error = new Error('offline')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const service = {
      getHistory: vi.fn().mockRejectedValue(error),
      getHistoryRecord: vi.fn().mockRejectedValue(error),
    }
    const history = useHomeHistory({ service, router: { push: vi.fn() } })

    await expect(history.loadHistory()).resolves.toBeUndefined()
    await expect(history.loadHistoryDetail('1')).resolves.toBeUndefined()

    expect(consoleError).toHaveBeenCalledTimes(2)
    consoleError.mockRestore()
  })
})
