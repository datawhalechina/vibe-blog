import { describe, expect, it } from 'vitest'

import {
  formatStorybookPreview,
  isStorybookOutputs,
} from '@/utils/storybookPreview'

describe('storybookPreview', () => {
  it('formats a complete Storybook output as deterministic Markdown', () => {
    const output = {
      title: '缓存小镇历险记',
      subtitle: '把缓存想成街角储物柜',
      core_metaphor: '储物柜让常用物品离你更近',
      pages: [
        {
          page_number: 1,
          title: '为什么需要缓存',
          image_url: 'https://example.com/cache.png',
          content: '每次都跑去仓库会很慢。',
          tech_point: '缓存降低访问延迟',
          real_world_example: '浏览器缓存静态资源',
          key_takeaway: '把常用数据放近一点',
        },
      ],
    }

    expect(isStorybookOutputs(output)).toBe(true)
    expect(formatStorybookPreview(output)).toBe([
      '# 缓存小镇历险记',
      '',
      '> 把缓存想成街角储物柜',
      '',
      '**核心比喻：** 储物柜让常用物品离你更近',
      '',
      '## 第 1 页：为什么需要缓存',
      '',
      '![为什么需要缓存](https://example.com/cache.png)',
      '',
      '每次都跑去仓库会很慢。',
      '',
      '- **技术点：** 缓存降低访问延迟',
      '- **现实案例：** 浏览器缓存静态资源',
      '- **本页要点：** 把常用数据放近一点',
    ].join('\n'))
  })

  it('omits missing optional fields and unsafe image URLs', () => {
    const output = {
      pages: [
        { content: '第一页正文', image_url: 'javascript:alert(1)' },
        { page_number: 4, title: '最后一页' },
      ],
    }

    expect(formatStorybookPreview(output)).toBe([
      '## 第 1 页',
      '',
      '第一页正文',
      '',
      '## 第 4 页：最后一页',
    ].join('\n'))
  })

  it('rejects missing, non-array, and empty pages', () => {
    expect(isStorybookOutputs({ title: 'No pages' })).toBe(false)
    expect(isStorybookOutputs({ pages: 'invalid' })).toBe(false)
    expect(isStorybookOutputs({ pages: [] })).toBe(false)
    expect(formatStorybookPreview(null)).toBe('')
    expect(formatStorybookPreview({ pages: [] })).toBe('')
  })
})
