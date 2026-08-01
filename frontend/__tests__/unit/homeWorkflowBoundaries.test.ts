import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Home workflow boundaries', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/views/Home.vue'),
    'utf8',
  )

  it('composes focused workflow composables', () => {
    expect(source).toContain("from '../composables/useTaskStream'")
    expect(source).toContain("from '../composables/useDocumentUpload'")
    expect(source).toContain("from '../composables/useGenerationForm'")
    expect(source).toContain("from '../composables/useHomeHistory'")
  })

  it('does not own task stream parsing or API workflow details', () => {
    expect(source).not.toContain('EventSource')
    expect(source).not.toContain('eventSource.addEventListener(')
    expect(source).not.toContain('sectionContentMap')
    expect(source).not.toContain('api.createTaskStream')
    expect(source).not.toContain('api.uploadDocument')
    expect(source).not.toContain('api.getDocumentStatus')
    expect(source).not.toContain('api.getHistory(')
    expect(source).not.toContain('api.getHistoryRecord')
  })
})
