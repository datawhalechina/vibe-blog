import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Generate workflow boundaries', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/views/Generate.vue'),
    'utf8',
  )

  it('composes focused editing and citation composables', () => {
    expect(source).toContain("from '@/composables/useMarkdownEditing'")
    expect(source).toContain("from '@/composables/useCitationInteractions'")
  })

  it('does not own editing persistence or citation DOM effects', () => {
    expect(source).not.toContain('api.polishSelectedText')
    expect(source).not.toContain('api.updateBlogContent')
    expect(source).not.toContain('scanCitationLinks')
    expect(source).not.toContain("addEventListener('mouseenter'")
    expect(source).not.toContain("addEventListener('mouseleave'")
  })
})
