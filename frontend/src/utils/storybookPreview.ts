export interface StorybookPage {
  page_number?: number | string
  title?: string
  content?: string
  image_url?: string
  tech_point?: string
  real_world_example?: string
  key_takeaway?: string
}

export interface StorybookOutputs {
  title?: string
  subtitle?: string
  core_metaphor?: string
  pages: StorybookPage[]
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === 'object' && value !== null && !Array.isArray(value)
)

const text = (value: unknown) => (
  typeof value === 'string' ? value.trim() : ''
)

const safeImageUrl = (value: unknown) => {
  const url = text(value)
  if (!/^(https?:\/\/|\/)/i.test(url)) return ''
  return url.replace(/([()])/g, '\\$1')
}

const imageAlt = (value: string) => value.replace(/([\\[\]])/g, '\\$1')

export function isStorybookOutputs(value: unknown): value is StorybookOutputs {
  return (
    isRecord(value)
    && Array.isArray(value.pages)
    && value.pages.length > 0
    && value.pages.every(isRecord)
  )
}

export function formatStorybookPreview(value: unknown): string {
  if (!isStorybookOutputs(value)) return ''

  const sections: string[] = []
  const title = text(value.title)
  const subtitle = text(value.subtitle)
  const coreMetaphor = text(value.core_metaphor)
  if (title) sections.push(`# ${title}`)
  if (subtitle) sections.push(`> ${subtitle}`)
  if (coreMetaphor) sections.push(`**核心比喻：** ${coreMetaphor}`)

  value.pages.forEach((page, index) => {
    const pageNumber = (
      typeof page.page_number === 'number'
      || (typeof page.page_number === 'string' && page.page_number.trim())
    ) ? page.page_number : index + 1
    const pageTitle = text(page.title)
    const pageSections = [
      `## 第 ${pageNumber} 页${pageTitle ? `：${pageTitle}` : ''}`,
    ]
    const imageUrl = safeImageUrl(page.image_url)
    if (imageUrl) {
      pageSections.push(`![${imageAlt(pageTitle || `第 ${pageNumber} 页配图`)}](${imageUrl})`)
    }
    const content = text(page.content)
    if (content) pageSections.push(content)

    const details = [
      ['技术点', text(page.tech_point)],
      ['现实案例', text(page.real_world_example)],
      ['本页要点', text(page.key_takeaway)],
    ].filter((entry) => entry[1])
    if (details.length) {
      pageSections.push(
        details.map(([label, detail]) => `- **${label}：** ${detail}`).join('\n'),
      )
    }
    sections.push(pageSections.join('\n\n'))
  })

  return sections.join('\n\n')
}
