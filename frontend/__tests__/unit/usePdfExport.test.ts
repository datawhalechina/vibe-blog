import { describe, it, expect } from 'vitest'
import { preprocessMarkdownForPdf } from '../../src/composables/usePdfExport'

describe('preprocessMarkdownForPdf', () => {
  it('expands details tags', () => {
    const input = '<details><summary>Click me</summary>Content here</details>'
    const result = preprocessMarkdownForPdf(input)
    expect(result).not.toContain('<details')
    expect(result).not.toContain('</details>')
    expect(result).toContain('**Click me**')
    expect(result).toContain('Content here')
  })

  it('removes anchor links', () => {
    const input = 'Hello <a name="section1"></a> World'
    const result = preprocessMarkdownForPdf(input)
    expect(result).not.toContain('<a name=')
    expect(result).toContain('Hello')
    expect(result).toContain('World')
  })

  it('handles empty string', () => {
    expect(preprocessMarkdownForPdf('')).toBe('')
  })

  it('preserves normal markdown', () => {
    const input = '# Title\n\nSome **bold** text'
    expect(preprocessMarkdownForPdf(input)).toBe(input)
  })

  it('handles multiple details blocks', () => {
    const input = '<details><summary>A</summary>1</details><details><summary>B</summary>2</details>'
    const result = preprocessMarkdownForPdf(input)
    expect(result).toContain('**A**')
    expect(result).toContain('**B**')
  })
})
