import { ref } from 'vue'

import * as api from '@/services/api'

type HomeHistoryService = Pick<typeof api, 'getHistory' | 'getHistoryRecord'>

interface HistoryRouter {
  push: (destination: string) => unknown
}

interface UseHomeHistoryOptions {
  service?: HomeHistoryService
  router: HistoryRouter
}

export function useHomeHistory(options: UseHomeHistoryOptions) {
  const service = options.service ?? api
  const currentHistoryTab = ref('blogs')
  const historyContentType = ref('all')
  const historyRecords = ref<api.HistoryRecord[]>([])
  const historyTotal = ref(0)
  const historyCurrentPage = ref(1)
  const historyTotalPages = ref(1)
  const contentTypeFilters = [
    { label: '全部', value: 'all' },
    { label: '博客', value: 'blog' },
    { label: '小红书', value: 'xhs' },
  ]

  const loadHistory = async (page = 1) => {
    try {
      const data = await service.getHistory({
        page,
        page_size: 12,
        content_type: historyContentType.value === 'all'
          ? undefined
          : historyContentType.value,
      })
      if (!data.success) return

      historyRecords.value = page === 1
        ? data.records
        : [...historyRecords.value, ...data.records]
      historyTotal.value = data.total
      historyCurrentPage.value = data.page
      historyTotalPages.value = data.total_pages
    } catch (error) {
      console.error('Load history error:', error)
    }
  }

  const loadMoreHistory = async () => {
    if (historyCurrentPage.value < historyTotalPages.value) {
      await loadHistory(historyCurrentPage.value + 1)
    }
  }

  const switchHistoryTab = async (tab: string) => {
    currentHistoryTab.value = tab
    if (tab === 'blogs') await loadHistory(1)
  }

  const filterByContentType = async (contentType: string) => {
    historyContentType.value = contentType
    await loadHistory(1)
  }

  const loadHistoryDetail = async (historyId: string) => {
    try {
      const data = await service.getHistoryRecord(historyId)
      if (!data.success || !data.record) return
      if (data.record.content_type === 'xhs') {
        options.router.push(`/xhs?history_id=${historyId}`)
        return
      }
      options.router.push(`/blog/${historyId}`)
    } catch (error) {
      console.error('Load history detail error:', error)
    }
  }

  return {
    currentHistoryTab,
    historyContentType,
    historyRecords,
    historyTotal,
    historyCurrentPage,
    historyTotalPages,
    contentTypeFilters,
    loadHistory,
    loadMoreHistory,
    switchHistoryTab,
    filterByContentType,
    loadHistoryDetail,
  }
}
