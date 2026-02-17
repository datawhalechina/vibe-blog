import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ProgressDrawer from '@/components/home/ProgressDrawer.vue'

describe('ProgressDrawer.vue', () => {
  const defaultProps = {
    visible: true,
    expanded: false,
    isLoading: false,
    statusBadge: 'idle',
    progressText: 'Ready',
    progressItems: [],
    articleType: 'tutorial',
    targetLength: 'medium',
    embedded: false,
    taskId: null,
    outlineData: null,
    waitingForOutline: false,
    previewContent: '',
  }

  describe('rendering', () => {
    it('should render when visible is true', () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      expect(wrapper.find('.progress-drawer').exists()).toBe(true)
      expect(wrapper.find('.progress-bar-mini').exists()).toBe(true)
    })

    it('should not render when visible is false', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          visible: false,
        },
      })

      expect(wrapper.find('.progress-drawer').exists()).toBe(false)
    })

    it('should render status badge', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          statusBadge: 'generating',
        },
      })

      expect(wrapper.find('.progress-status').text()).toBe('generating')
    })

    it('should render progress text', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          progressText: 'Generating blog...',
        },
      })

      expect(wrapper.find('.progress-text').text()).toBe('Generating blog...')
    })

    it('should render logs count', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          progressItems: [
            { time: '10:00:00', message: 'Log 1', type: 'info' },
            { time: '10:00:01', message: 'Log 2', type: 'success' },
          ],
        },
      })

      expect(wrapper.find('.progress-logs').text()).toBe('2 logs')
    })
  })

  describe('loading indicator', () => {
    it('should show active indicator when loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: true,
        },
      })

      const indicator = wrapper.find('.progress-indicator')
      expect(indicator.classes()).toContain('active')
    })

    it('should not show active indicator when not loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: false,
        },
      })

      const indicator = wrapper.find('.progress-indicator')
      expect(indicator.classes()).not.toContain('active')
    })

    it('should show stop button when loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: true,
        },
      })

      expect(wrapper.find('.progress-stop-btn').exists()).toBe(true)
      expect(wrapper.find('.progress-stop-btn').text()).toContain('中断')
    })

    it('should not show stop button when not loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: false,
        },
      })

      expect(wrapper.find('.progress-stop-btn').exists()).toBe(false)
    })
  })

  describe('expansion', () => {
    it('should have expanded class when expanded is true', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
        },
      })

      expect(wrapper.find('.progress-drawer').classes()).toContain('expanded')
    })

    it('should not have expanded class when expanded is false', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: false,
        },
      })

      expect(wrapper.find('.progress-drawer').classes()).not.toContain('expanded')
    })

    it('should show content when expanded', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
        },
      })

      const content = wrapper.find('.progress-content')
      expect(content.isVisible()).toBe(true)
    })

    it('should hide content when not expanded', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: false,
        },
      })

      const content = wrapper.find('.progress-content')
      // v-show sets display: none, check the style attribute
      expect(content.attributes('style')).toContain('display: none')
    })

    it('should rotate toggle icon when expanded', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
        },
      })

      const icon = wrapper.find('.progress-toggle-btn svg')
      expect(icon.classes()).toContain('rotate-down')
    })
  })

  describe('task header', () => {
    it('should render task command with article type and length', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          articleType: 'guide',
          targetLength: 'long',
        },
      })

      const header = wrapper.find('.progress-task-header')
      expect(header.text()).toContain('generate')
      expect(header.text()).toContain('guide')
      expect(header.text()).toContain('long')
    })

    it('should render task ID when provided', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          taskId: 'task-123',
        },
      })

      expect(wrapper.find('.progress-task-id').text()).toBe('task-123')
    })

    it('should not render task ID when null', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          taskId: null,
        },
      })

      expect(wrapper.find('.progress-task-id').exists()).toBe(false)
    })
  })

  describe('progress logs', () => {
    const mockLogs = [
      { time: '10:00:00', message: 'Starting generation', type: 'info' },
      { time: '10:00:05', message: 'Generation complete', type: 'success' },
      { time: '10:00:10', message: 'Error occurred', type: 'error' },
      { time: '10:00:15', message: 'Warning message', type: 'warning' },
      { time: '10:00:20', message: 'Streaming data', type: 'stream' },
    ]

    it('should render all progress items', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: mockLogs,
        },
      })

      const logItems = wrapper.findAll('.progress-log-item')
      expect(logItems).toHaveLength(5)
    })

    it('should render log time, icon, and message', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [mockLogs[0]],
        },
      })

      const logItem = wrapper.find('.progress-log-item')
      expect(logItem.find('.progress-log-time').text()).toBe('10:00:00')
      expect(logItem.find('.progress-log-icon').text()).toBe('○')
      expect(logItem.find('.progress-log-msg').text()).toBe('Starting generation')
    })

    it('should render correct icons for different log types', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: mockLogs,
        },
      })

      const logItems = wrapper.findAll('.progress-log-item')
      expect(logItems[0].find('.progress-log-icon').text()).toBe('○') // info
      expect(logItems[1].find('.progress-log-icon').text()).toBe('✓') // success
      expect(logItems[2].find('.progress-log-icon').text()).toBe('✗') // error
      expect(logItems[3].find('.progress-log-icon').text()).toBe('⚠') // warning
      expect(logItems[4].find('.progress-log-icon').text()).toBe('◐') // stream
    })

    it('should apply correct CSS classes for log types', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: mockLogs,
        },
      })

      const logItems = wrapper.findAll('.progress-log-item')
      expect(logItems[0].classes()).toContain('info')
      expect(logItems[1].classes()).toContain('success')
      expect(logItems[2].classes()).toContain('error')
      expect(logItems[3].classes()).toContain('warning')
      expect(logItems[4].classes()).toContain('stream')
    })

    it('should render log detail when provided', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [
            {
              time: '10:00:00',
              message: 'Error occurred',
              type: 'error',
              detail: 'Stack trace here',
            },
          ],
        },
      })

      const detail = wrapper.find('.progress-log-detail')
      expect(detail.exists()).toBe(true)
      expect(detail.text()).toBe('Stack trace here')
    })

    it('should not render log detail when not provided', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [mockLogs[0]],
        },
      })

      expect(wrapper.find('.progress-log-detail').exists()).toBe(false)
    })

    it('should show loading spinner when loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          isLoading: true,
          progressText: 'Generating...',
        },
      })

      expect(wrapper.text()).toContain('Generating...')
    })

    it('should not show loading spinner when not loading', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          isLoading: false,
        },
      })

      expect(wrapper.find('.progress-loading-line').exists()).toBe(false)
    })
  })

  describe('events', () => {
    it('should emit toggle when mini bar is clicked', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      await wrapper.find('.progress-bar-mini').trigger('click')

      expect(wrapper.emitted('toggle')).toBeTruthy()
    })

    it('should emit toggle when toggle button is clicked', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      await wrapper.find('.progress-toggle-btn').trigger('click')

      expect(wrapper.emitted('toggle')).toBeTruthy()
    })

    it('should emit close when close button is clicked', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      await wrapper.find('.progress-close-btn').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('should emit stop when stop button is clicked', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: true,
        },
      })

      await wrapper.find('.progress-stop-btn').trigger('click')

      expect(wrapper.emitted('stop')).toBeTruthy()
    })

    it('should stop event propagation when clicking stop button', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          isLoading: true,
        },
      })

      await wrapper.find('.progress-stop-btn').trigger('click')

      // Should emit stop but not toggle
      expect(wrapper.emitted('stop')).toBeTruthy()
      expect(wrapper.emitted('toggle')).toBeFalsy()
    })

    it('should stop event propagation when clicking toggle button', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      await wrapper.find('.progress-toggle-btn').trigger('click')

      // Should emit toggle only once (from button, not from mini bar)
      expect(wrapper.emitted('toggle')).toHaveLength(1)
    })

    it('should stop event propagation when clicking close button', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: defaultProps,
      })

      await wrapper.find('.progress-close-btn').trigger('click')

      // Should emit close but not toggle
      expect(wrapper.emitted('close')).toBeTruthy()
      expect(wrapper.emitted('toggle')).toBeFalsy()
    })
  })

  describe('auto-scroll', () => {
    it('should auto-scroll to bottom when new items are added', async () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [
            { time: '10:00:00', message: 'Log 1', type: 'info' },
          ],
        },
      })

      // Mock scrollTop and scrollHeight
      const progressBody = wrapper.find('.progress-logs-container').element as HTMLElement
      Object.defineProperty(progressBody, 'scrollHeight', {
        configurable: true,
        value: 1000,
      })
      Object.defineProperty(progressBody, 'scrollTop', {
        configurable: true,
        writable: true,
        value: 0,
      })

      // Add new item
      await wrapper.setProps({
        progressItems: [
          { time: '10:00:00', message: 'Log 1', type: 'info' },
          { time: '10:00:01', message: 'Log 2', type: 'success' },
        ],
      })

      await nextTick()

      // Should scroll to bottom
      expect(progressBody.scrollTop).toBe(1000)
    })
  })

  describe('HTML rendering in messages', () => {
    it('should render HTML in log messages', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [
            {
              time: '10:00:00',
              message: '<strong>Bold text</strong>',
              type: 'info',
            },
          ],
        },
      })

      const logMsg = wrapper.find('.progress-log-msg')
      expect(logMsg.html()).toContain('<strong>Bold text</strong>')
    })
  })

  describe('search card rendering', () => {
    const searchItem = {
      time: '10:00:00',
      message: '🔍 LangGraph 教程',
      type: 'search',
      data: {
        query: 'LangGraph 教程',
        results: [
          { title: 'LangGraph 入门', url: 'https://example.com/1', domain: 'example.com' },
          { title: 'LangGraph 进阶', url: 'https://example.com/2', domain: 'example.com' },
          { title: 'LangGraph 实战', url: 'https://example.com/3', domain: 'blog.com' },
        ],
      },
    }

    it('should render search query text', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [searchItem] },
      })
      expect(wrapper.text()).toContain('LangGraph 教程')
    })

    it('should render search result card titles', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [searchItem] },
      })
      expect(wrapper.text()).toContain('LangGraph 入门')
    })

    it('should render favicon images with correct src', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [searchItem] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should render search card links with correct href', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [searchItem] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should limit search results to 8 cards', () => {
      const manyResults = Array.from({ length: 12 }, (_, i) => ({
        title: `Result ${i + 1}`,
        url: `https://example.com/${i}`,
        domain: 'example.com',
      }))
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [{
            ...searchItem,
            data: { query: 'test', results: manyResults },
          }],
        },
      })
      expect(wrapper.text()).toContain('Result')
    })

    it('should not affect normal log rendering', () => {
      const wrapper = mount(ProgressDrawer, {
        props: {
          ...defaultProps,
          expanded: true,
          progressItems: [
            { time: '10:00:00', message: 'Normal log', type: 'info' },
            searchItem,
          ],
        },
      })
      expect(wrapper.text()).toContain('Normal log')
    })
  })

  describe('crawl card rendering', () => {
    const crawlItem = {
      time: '10:00:01',
      message: '📖 已抓取 3 篇',
      type: 'crawl',
      data: {
        title: 'LangGraph 官方文档',
        url: 'https://docs.langchain.com/langgraph',
        contentLength: 15360,
        count: 3,
      },
    }

    it('should render crawl card with title and URL', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [crawlItem] },
      })
      expect(wrapper.text()).toContain('LangGraph 官方文档')
    })

    it('should render crawl link as clickable anchor', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [crawlItem] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should render content size in KB', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [crawlItem] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should fallback to URL when title is missing', () => {
      const noTitleItem = {
        ...crawlItem,
        data: { url: 'https://example.com/page', contentLength: 1024 },
      }
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [noTitleItem] },
      })
      expect(wrapper.text()).toContain('https://example.com/page')
    })
  })

  describe('mixed rendering', () => {
    it('should render search cards, crawl cards, and normal logs together', () => {
      const mixedItems = [
        { time: '10:00:00', message: 'Starting', type: 'info' },
        {
          time: '10:00:01',
          message: '🔍 搜索',
          type: 'search',
          data: {
            query: 'test',
            results: [{ title: 'R1', url: 'https://a.com', domain: 'a.com' }],
          },
        },
        {
          time: '10:00:02',
          message: '📖 爬取',
          type: 'crawl',
          data: { title: 'Page', url: 'https://b.com', count: 1 },
        },
        { time: '10:00:03', message: 'Done', type: 'success' },
      ]
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: mixedItems },
      })

      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('animation control', () => {
    const makeSearchItem = (count: number) => ({
      time: '10:00:00',
      message: '🔍 search',
      type: 'search',
      data: {
        query: 'test',
        results: Array.from({ length: count }, (_, i) => ({
          title: `Result ${i + 1}`,
          url: `https://example.com/${i}`,
          domain: 'example.com',
        })),
      },
    })

    it('should apply animation to the first 6 cards', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [makeSearchItem(8)] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should not apply animation to cards after the 6th', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [makeSearchItem(8)] },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('should cap animation delay at 300ms', () => {
      const wrapper = mount(ProgressDrawer, {
        props: { ...defaultProps, expanded: true, progressItems: [makeSearchItem(8)] },
      })
      expect(wrapper.exists()).toBe(true)
    })
  })
})
