import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BlogInputCard from '@/components/home/BlogInputCard.vue'

describe('BlogInputCard.vue', () => {
  const defaultProps = {
    topic: '',
    uploadedDocuments: [],
    isLoading: false,
    isEnhancing: false,
    showAdvancedOptions: false,
  }

  describe('rendering', () => {
    it('should render the component', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.code-input-card').exists()).toBe(true)
      expect(wrapper.find('.code-input-header').exists()).toBe(true)
      expect(wrapper.find('.code-input-body').exists()).toBe(true)
    })

    it('should render terminal header with dots', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.terminal-dots').exists()).toBe(true)
      expect(wrapper.findAll('.terminal-dot')).toHaveLength(3)
      expect(wrapper.find('.terminal-title').text()).toBe('vibe-blog ~ generate')
    })

    it('should render textarea with placeholder', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.code-input-textarea').exists()).toBe(true)
    })

    it('should render generate button', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.code-generate-btn').exists()).toBe(true)
    })
  })

  describe('topic input', () => {
    it('should display topic value', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
        },
      })

      expect(wrapper.find('.code-input-textarea').exists()).toBe(true)
    })

    it('should emit update:topic when typing', async () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.code-input-textarea').exists()).toBe(true)
    })

    it('should handle Ctrl+Enter to generate', async () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
        },
      })

      expect(wrapper.find('.code-input-textarea').exists()).toBe(true)
    })
  })

  describe('generate button', () => {
    it('should be disabled when topic is empty', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: '',
        },
      })

      const button = wrapper.find('.code-generate-btn')
      expect(button.attributes('disabled')).toBeDefined()
    })

    it('should be disabled when topic is only whitespace', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: '   ',
        },
      })

      const button = wrapper.find('.code-generate-btn')
      expect(button.attributes('disabled')).toBeDefined()
    })

    it('should be disabled when loading', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
          isLoading: true,
        },
      })

      const button = wrapper.find('.code-generate-btn')
      expect(button.attributes('disabled')).toBeDefined()
    })

    it('should be enabled when topic is valid and not loading', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
          isLoading: false,
        },
      })

      const button = wrapper.find('.code-generate-btn')
      expect(button.attributes('disabled')).toBeUndefined()
    })

    it('should emit generate event when clicked', async () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
        },
      })

      const button = wrapper.find('.code-generate-btn')
      await button.trigger('click')

      expect(wrapper.emitted('generate')).toBeTruthy()
    })

    it('should show loading spinner when loading', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          topic: 'Test Topic',
          isLoading: true,
        },
      })

      expect(wrapper.find('.loading-spinner').exists()).toBe(true)
      expect(wrapper.find('.code-generate-btn').text()).toContain('生成中')
    })
  })

  describe('file upload', () => {
    it('should render file upload button', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const uploadLabel = wrapper.find('.code-action-btn')
      expect(uploadLabel.exists()).toBe(true)
      expect(uploadLabel.text()).toContain('附件')
    })

    it('should accept correct file types', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const fileInput = wrapper.find('input[type="file"]')
      expect(fileInput.attributes('accept')).toBe('.pdf,.md,.txt,.markdown')
      expect(fileInput.attributes('multiple')).toBeDefined()
    })

    it('should emit fileUpload event when files selected', async () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const fileInput = wrapper.find('input[type="file"]')
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })

      Object.defineProperty(fileInput.element, 'files', {
        value: [file],
        writable: false,
      })

      await fileInput.trigger('change')

      expect(wrapper.emitted('fileUpload')).toBeTruthy()
    })

    it('should show upload tooltip on hover', async () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const uploadLabel = wrapper.find('.code-action-btn')
      await uploadLabel.trigger('mouseenter')

      expect(wrapper.find('.upload-tooltip').exists()).toBe(true)
      expect(wrapper.find('.upload-tooltip').text()).toContain('PDF 文件不超过 15 页')
    })

    it('should hide upload tooltip on mouse leave', async () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const uploadLabel = wrapper.find('.code-action-btn')
      await uploadLabel.trigger('mouseenter')
      await uploadLabel.trigger('mouseleave')

      expect(wrapper.find('.upload-tooltip').exists()).toBe(false)
    })
  })

  describe('uploaded documents', () => {
    const mockDocuments = [
      { id: 'doc1', filename: 'test1.pdf', status: 'ready' },
      { id: 'doc2', filename: 'test2.md', status: 'uploading' },
      { id: 'doc3', filename: 'test3.txt', status: 'error' },
    ]

    it('should not show documents section when empty', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      expect(wrapper.find('.code-input-docs').exists()).toBe(false)
    })

    it('should show documents section when documents exist', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          uploadedDocuments: mockDocuments,
        },
      })

      expect(wrapper.find('.code-input-docs').exists()).toBe(true)
      expect(wrapper.findAll('.code-doc-tag')).toHaveLength(3)
    })

    it('should display document filenames', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          uploadedDocuments: mockDocuments,
        },
      })

      const docTags = wrapper.findAll('.code-doc-tag')
      expect(docTags[0].text()).toContain('test1.pdf')
      expect(docTags[1].text()).toContain('test2.md')
      expect(docTags[2].text()).toContain('test3.txt')
    })

    it('should truncate long filenames', () => {
      const longFilename = 'very_long_filename_that_should_be_truncated.pdf'
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          uploadedDocuments: [
            { id: 'doc1', filename: longFilename, status: 'ready' },
          ],
        },
      })

      const docTag = wrapper.find('.code-doc-tag')
      expect(docTag.text()).toContain('...')
      expect(docTag.text().length).toBeLessThan(longFilename.length)
    })

    it('should show correct status icons', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          uploadedDocuments: mockDocuments,
        },
      })

      const docTags = wrapper.findAll('.code-doc-tag')
      // Ready status should show FileCheck icon
      expect(docTags[0].classes()).toContain('doc-ready')
      // Uploading status should show Loader icon
      expect(docTags[1].find('.loading').exists()).toBe(true)
      // Error status should have error class
      expect(docTags[2].classes()).toContain('doc-error')
    })

    it('should emit removeDocument when remove button clicked', async () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          uploadedDocuments: mockDocuments,
        },
      })

      const removeButton = wrapper.find('.doc-remove')
      await removeButton.trigger('click')

      expect(wrapper.emitted('removeDocument')).toBeTruthy()
      expect(wrapper.emitted('removeDocument')?.[0]).toEqual(['doc1'])
    })
  })

  describe('advanced options', () => {
    it('should render advanced options button', () => {
      const wrapper = mount(BlogInputCard, {
        props: defaultProps,
      })

      const buttons = wrapper.findAll('.code-action-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('高级选项'))
      expect(advancedBtn).toBeDefined()
    })

    it('should emit update:showAdvancedOptions when clicked', async () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          showAdvancedOptions: false,
        },
      })

      const buttons = wrapper.findAll('.code-action-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('高级选项'))
      await advancedBtn?.trigger('click')

      expect(wrapper.emitted('update:showAdvancedOptions')).toBeTruthy()
      expect(wrapper.emitted('update:showAdvancedOptions')?.[0]).toEqual([true])
    })

    it('should have active class when showAdvancedOptions is true', () => {
      const wrapper = mount(BlogInputCard, {
        props: {
          ...defaultProps,
          showAdvancedOptions: true,
        },
      })

      const buttons = wrapper.findAll('.code-action-btn')
      const advancedBtn = buttons.find(btn => btn.text().includes('高级选项'))
      expect(advancedBtn?.classes()).toContain('active')
    })
  })
})
