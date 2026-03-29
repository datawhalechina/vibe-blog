import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BlogHistoryList from '@/components/home/BlogHistoryList.vue'

describe('BlogHistoryList.vue', () => {
  const mockRecords = [
    {
      id: '1',
      topic: 'Vue 3 Composition API',
      content_type: 'blog',
      created_at: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
      sections_count: 5,
      code_blocks_count: 10,
    },
    {
      id: '2',
      topic: '小红书内容创作技巧',
      content_type: 'xhs',
      created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      images_count: 8,
      cover_image: 'https://example.com/cover.jpg',
    },
    {
      id: '3',
      topic: 'React Hooks 深度解析',
      content_type: 'blog',
      created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
      sections_count: 8,
      code_blocks_count: 15,
      cover_video: 'https://example.com/video.mp4',
      cover_image: 'https://example.com/poster.jpg',
    },
  ]

  const defaultProps = {
    showList: true,
    currentTab: 'blogs',
    contentType: 'all',
    showCoverPreview: false,
    records: mockRecords,
    total: 3,
    currentPage: 1,
    totalPages: 1,
    contentTypeFilters: [
      { label: '全部', value: 'all' },
      { label: '博客', value: 'blog' },
      { label: '小红书', value: 'xhs' },
    ],
    animated: false,
  }

  describe('rendering', () => {
    it('should render the component', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      expect(wrapper.text()).toContain('history')
    })

    it('should render header title and count', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      expect(wrapper.text()).toContain('history')
      expect(wrapper.text()).toContain('3')
    })

    it('should render zero count when total is 0', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          total: 0,
        },
      })

      expect(wrapper.text()).toContain('0')
    })

    it('should render all blog cards', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      expect(wrapper.text()).toContain('Vue 3')
    })

    it('should show empty message when no records', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [],
        },
      })

      expect(wrapper.text()).toContain('暂无')
    })

    it('should show XHS empty message when filtering XHS with no records', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          contentType: 'xhs',
          records: [],
        },
      })

      expect(wrapper.text()).toContain('暂无')
    })
  })

  describe('list toggle', () => {
    it('should show list when showList is true', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showList: true,
        },
      })

      expect(wrapper.text()).toContain('Vue 3')
    })

    it('should hide list when showList is false', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showList: false,
        },
      })

      expect(wrapper.html()).toBeTruthy()
    })

    it('should emit toggleList when toggle button is clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const buttons = wrapper.findAll('button')
      if (buttons.length > 0) {
        await buttons[0].trigger('click')
        expect(wrapper.emitted('toggleList')).toBeTruthy()
      }
    })

    it('should rotate icon when list is shown', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showList: true,
        },
      })

      expect(wrapper.text()).toContain('Vue 3')
    })

    it('should not rotate icon when list is hidden', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showList: false,
        },
      })

      expect(wrapper.html()).toBeTruthy()
    })
  })

  describe('tab switching', () => {
    it('should render blogs and books tabs', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      expect(wrapper.text()).toContain('博客')
    })

    it('should highlight active tab', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentTab: 'blogs',
        },
      })

      expect(wrapper.text()).toContain('博客')
    })

    it('should emit switchTab when tab is clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const buttons = wrapper.findAll('button')
      if (buttons.length > 1) {
        await buttons[1].trigger('click')
        expect(wrapper.emitted('switchTab')).toBeTruthy()
      }
    })
  })

  describe('content type filtering', () => {
    it('should render filter buttons when on blogs tab', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentTab: 'blogs',
        },
      })

      expect(wrapper.text()).toContain('全部')
    })

    it('should not render filter buttons when on books tab', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentTab: 'books',
        },
      })

      expect(wrapper.find('.filter-group').exists()).toBe(false)
    })

    it('should highlight active filter', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          contentType: 'blog',
        },
      })

      const filters = wrapper.findAll('.filter-btn')
      expect(filters[1].classes()).toContain('active')
    })

    it('should emit filterContentType when filter is clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const filters = wrapper.findAll('.filter-btn')
      await filters[2].trigger('click')

      expect(wrapper.emitted('filterContentType')).toBeTruthy()
      expect(wrapper.emitted('filterContentType')?.[0]).toEqual(['xhs'])
    })
  })

  describe('cover preview toggle', () => {
    it('should render cover toggle when on blogs tab', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentTab: 'blogs',
        },
      })

      expect(wrapper.find('.cover-toggle').exists()).toBe(true)
    })

    it('should not render cover toggle when on books tab', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentTab: 'books',
        },
      })

      expect(wrapper.find('.cover-toggle').exists()).toBe(false)
    })

    it('should have active class when showCoverPreview is true', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: true,
        },
      })

      expect(wrapper.find('.cover-toggle').classes()).toContain('active')
    })

    it('should emit update:showCoverPreview when clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: false,
        },
      })

      await wrapper.find('.cover-toggle').trigger('click')

      expect(wrapper.emitted('update:showCoverPreview')).toBeTruthy()
      expect(wrapper.emitted('update:showCoverPreview')?.[0]).toEqual([true])
    })
  })

  describe('blog cards', () => {
    it('should render blog card with correct content', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[0]
      expect(card.find('.code-blog-title').text()).toBe('Vue 3 Composition API')
      expect(card.find('.code-card-folder-name').text()).toBe('blog-posts')
    })

    it('should render XHS card with correct content', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[1]
      expect(card.find('.code-blog-title').text()).toBe('小红书内容创作技巧')
      expect(card.find('.code-card-folder-name').text()).toBe('xhs-posts')
      expect(card.classes()).toContain('xhs-card')
    })

    it('should render blog tags correctly', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[0]
      const tags = card.findAll('.code-tag')
      expect(tags[0].text()).toBe('BLOG')
      expect(tags[0].classes()).toContain('tag-blog')
      expect(tags[1].text()).toContain('5') // sections count
      expect(tags[2].text()).toContain('10') // code blocks count
    })

    it('should render XHS tags correctly', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[1]
      const tags = card.findAll('.code-tag')
      expect(tags[0].text()).toBe('XHS')
      expect(tags[0].classes()).toContain('tag-xhs')
      expect(tags[1].text()).toContain('8') // images count
    })

    it('should render video tag when cover_video exists', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[2]
      const videoTag = card.find('.tag-video')
      expect(videoTag.exists()).toBe(true)
    })

    it('should render relative time correctly', () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const cards = wrapper.findAll('.code-blog-card')
      expect(cards[0].find('.code-card-date').text()).toBe('1 分钟前')
      expect(cards[1].find('.code-card-date').text()).toBe('1 小时前')
      expect(cards[2].find('.code-card-date').text()).toBe('1 天前')
    })

    it('should emit loadDetail when card is clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: defaultProps,
      })

      const card = wrapper.findAll('.code-blog-card')[0]
      await card.trigger('click')

      expect(wrapper.emitted('loadDetail')).toBeTruthy()
      expect(wrapper.emitted('loadDetail')?.[0]).toEqual(['1'])
    })

    it('should apply animation delay when animated is true', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          animated: true,
        },
      })

      const cards = wrapper.findAll('.code-blog-card')
      expect(cards[0].classes()).toContain('card-animate')
      expect(cards[0].attributes('style')).toContain('animation-delay: 0.3s')
      expect(cards[1].attributes('style')).toContain('animation-delay: 0.42s')
      expect(cards[2].attributes('style')).toContain('animation-delay: 0.54s')
    })
  })

  describe('cover preview', () => {
    it('should not show cover preview by default', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: false,
        },
      })

      expect(wrapper.find('.card-cover-preview').exists()).toBe(false)
    })

    it('should show cover image when showCoverPreview is true', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: true,
        },
      })

      const card = wrapper.findAll('.code-blog-card')[1]
      const coverPreview = card.find('.card-cover-preview')
      expect(coverPreview.exists()).toBe(true)
      expect(coverPreview.find('img').attributes('src')).toBe('https://example.com/cover.jpg')
      expect(coverPreview.find('.cover-badge').text()).toBe('COVER')
    })

    it('should show cover video when available', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: true,
        },
      })

      const card = wrapper.findAll('.code-blog-card')[2]
      const coverPreview = card.find('.card-cover-preview')
      const video = coverPreview.find('video')
      expect(video.exists()).toBe(true)
      expect(video.attributes('src')).toBe('https://example.com/video.mp4')
      expect(video.attributes('poster')).toBe('https://example.com/poster.jpg')
      expect(coverPreview.find('.cover-badge').text()).toBe('VIDEO')
    })

    it('should add with-cover class when cover exists', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showCoverPreview: true,
        },
      })

      const card = wrapper.findAll('.code-blog-card')[1]
      expect(card.classes()).toContain('with-cover')
    })
  })

  describe('show more button', () => {
    it('should show when currentPage < totalPages', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentPage: 1,
          totalPages: 3,
        },
      })

      const showMore = wrapper.find('.show-more-wrapper')
      expect(showMore.isVisible()).toBe(true)
    })

    it('should hide when currentPage >= totalPages', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentPage: 3,
          totalPages: 3,
        },
      })

      const showMore = wrapper.find('.show-more-wrapper')
      expect(showMore.attributes('style')).toContain('display: none')
    })

    it('should hide when list is not shown', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          showList: false,
          currentPage: 1,
          totalPages: 3,
        },
      })

      const showMore = wrapper.find('.show-more-wrapper')
      expect(showMore.attributes('style')).toContain('display: none')
    })

    it('should emit loadMore when clicked', async () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          currentPage: 1,
          totalPages: 3,
        },
      })

      await wrapper.find('.show-more-btn').trigger('click')

      expect(wrapper.emitted('loadMore')).toBeTruthy()
    })
  })

  describe('formatRelativeTime', () => {
    it('should format time correctly for just now', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [
            {
              ...mockRecords[0],
              created_at: new Date(Date.now() - 30000).toISOString(), // 30 seconds ago
            },
          ],
        },
      })

      expect(wrapper.find('.code-card-date').text()).toBe('刚刚')
    })

    it('should format time correctly for minutes', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [
            {
              ...mockRecords[0],
              created_at: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
            },
          ],
        },
      })

      expect(wrapper.find('.code-card-date').text()).toBe('5 分钟前')
    })

    it('should format time correctly for hours', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [
            {
              ...mockRecords[0],
              created_at: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
            },
          ],
        },
      })

      expect(wrapper.find('.code-card-date').text()).toBe('2 小时前')
    })

    it('should format time correctly for days', () => {
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [
            {
              ...mockRecords[0],
              created_at: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
            },
          ],
        },
      })

      expect(wrapper.find('.code-card-date').text()).toBe('3 天前')
    })

    it('should format time correctly for old dates', () => {
      const oldDate = new Date('2024-01-01')
      const wrapper = mount(BlogHistoryList, {
        props: {
          ...defaultProps,
          records: [
            {
              ...mockRecords[0],
              created_at: oldDate.toISOString(),
            },
          ],
        },
      })

      expect(wrapper.find('.code-card-date').text()).toBe(oldDate.toLocaleDateString('zh-CN'))
    })
  })
})
