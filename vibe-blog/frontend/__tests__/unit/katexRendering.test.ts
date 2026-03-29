/**
 * KaTeX math formula rendering tests
 * Verifies that useMarkdownRenderer correctly renders inline and display math
 */
import { describe, it, expect } from 'vitest'
import { useMarkdownRenderer } from '@/composables/useMarkdownRenderer'

describe('KaTeX math rendering', () => {
  const { renderMarkdown } = useMarkdownRenderer()

  it('renders inline math with $ delimiters', () => {
    const result = renderMarkdown('The formula $E=mc^2$ is famous.')
    expect(result).toContain('katex')
    expect(result).toContain('E')
  })

  it('renders display/block math with $$ delimiters', () => {
    const result = renderMarkdown('$$\n\\int_0^1 x^2 dx\n$$')
    expect(result).toContain('katex-display')
  })

  it('does not break normal text without math', () => {
    const result = renderMarkdown('Hello world, no math here.')
    expect(result).toContain('Hello world, no math here.')
    expect(result).not.toContain('katex')
  })

  it('renders mixed content: text + inline math', () => {
    const result = renderMarkdown('Area of circle: $A = \\pi r^2$, where r is radius.')
    expect(result).toContain('katex')
    expect(result).toContain('where r is radius')
  })

  it('handles throwOnError: false gracefully for invalid LaTeX', () => {
    // Invalid LaTeX should not throw, should render error span instead
    const result = renderMarkdown('Bad formula: $\\invalidcommand{x}$')
    expect(result).toBeDefined()
    // Should not throw, just render something
    expect(typeof result).toBe('string')
  })
})
