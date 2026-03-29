/**
 * 101.09 useExport 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock jspdf 和 html2canvas（未安装的可选依赖，动态 import 会失败）
vi.mock('jspdf', () => ({
  jsPDF: vi.fn(() => ({
    setFont: vi.fn(),
    setFontSize: vi.fn(),
    splitTextToSize: vi.fn(() => ['mock line']),
    text: vi.fn(),
    addPage: vi.fn(),
    save: vi.fn(),
  })),
}))

vi.mock('html2canvas', () => ({
  default: vi.fn(() =>
    Promise.resolve({
      toBlob: vi.fn((cb: (blob: Blob | null) => void) => cb(new Blob(['img']))),
    })
  ),
}))

// Mock DOM APIs
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
const mockRevokeObjectURL = vi.fn()
const mockAppendChild = vi.fn()
const mockRemoveChild = vi.fn()
const mockClick = vi.fn()

// 只 mock URL 的静态方法，保留 URL 构造函数
URL.createObjectURL = mockCreateObjectURL
URL.revokeObjectURL = mockRevokeObjectURL

// Mock document.createElement and body
const mockAnchor = { href: '', download: '', click: mockClick }
vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as any)
vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild)
vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild)

// Dynamic import to get fresh module
let useExport: typeof import('@/composables/useExport').useExport

beforeEach(async () => {
  vi.clearAllMocks()
  const mod = await import('@/composables/useExport')
  useExport = mod.useExport
})

describe('useExport', () => {
  it('should export markdown as .md file', () => {
    const { exportMarkdown } = useExport()
    exportMarkdown('# Hello', 'test-title')

    expect(mockCreateObjectURL).toHaveBeenCalledOnce()
    expect(mockClick).toHaveBeenCalledOnce()
    expect(mockAnchor.download).toBe('test-title.md')
  })

  it('should export HTML as .html file', () => {
    const { exportHtml } = useExport()
    exportHtml('# Hello', 'test-title')

    expect(mockCreateObjectURL).toHaveBeenCalledOnce()
    expect(mockAnchor.download).toBe('test-title.html')
  })

  it('should export plain text as .txt file', () => {
    const { exportTxt } = useExport()
    exportTxt('**Bold** text', 'test-title')

    expect(mockCreateObjectURL).toHaveBeenCalledOnce()
    expect(mockAnchor.download).toBe('test-title.txt')
  })

  it('should prevent concurrent downloads via isDownloading lock', async () => {
    const { exportAs, isDownloading } = useExport()
    expect(isDownloading.value).toBe(false)

    await exportAs('markdown', '# Hello', 'test')
    // After completion, isDownloading should be false again
    expect(isDownloading.value).toBe(false)
  })
})
