import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  formatFileSize,
  formatWordCount,
  getStatusText,
  getStatusIcon,
  isSpinningStatus,
  getStageIcon,
  parseCookies,
  escapeHtml,
  formatTime,
  downloadFile,
  copyToClipboard,
} from '@/utils/helpers'

describe('helpers.ts', () => {
  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0B')
      expect(formatFileSize(500)).toBe('500B')
      expect(formatFileSize(1023)).toBe('1023B')
    })

    it('should format kilobytes correctly', () => {
      expect(formatFileSize(1024)).toBe('1.0KB')
      expect(formatFileSize(2048)).toBe('2.0KB')
      expect(formatFileSize(1536)).toBe('1.5KB')
      expect(formatFileSize(1024 * 1024 - 1)).toMatch(/KB$/)
    })

    it('should format megabytes correctly', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.0MB')
      expect(formatFileSize(2 * 1024 * 1024)).toBe('2.0MB')
      expect(formatFileSize(1.5 * 1024 * 1024)).toBe('1.5MB')
    })
  })

  describe('formatWordCount', () => {
    it('should format small counts correctly', () => {
      expect(formatWordCount(0)).toBe('0 字')
      expect(formatWordCount(500)).toBe('500 字')
      expect(formatWordCount(999)).toBe('999 字')
    })

    it('should format thousands correctly', () => {
      expect(formatWordCount(1000)).toBe('约 1.0 千字')
      expect(formatWordCount(2500)).toBe('约 2.5 千字')
      expect(formatWordCount(9999)).toBe('约 10.0 千字')
    })

    it('should format ten thousands correctly', () => {
      expect(formatWordCount(10000)).toBe('约 1.0 万字')
      expect(formatWordCount(25000)).toBe('约 2.5 万字')
      expect(formatWordCount(100000)).toBe('约 10.0 万字')
    })
  })

  describe('getStatusText', () => {
    it('should return correct text for known statuses', () => {
      expect(getStatusText('uploading')).toBe('上传中...')
      expect(getStatusText('pending')).toBe('等待解析...')
      expect(getStatusText('parsing')).toBe('解析中...')
      expect(getStatusText('ready')).toBe('已就绪')
      expect(getStatusText('error')).toBe('解析失败')
      expect(getStatusText('timeout')).toBe('超时')
    })

    it('should return original status for unknown statuses', () => {
      expect(getStatusText('unknown')).toBe('unknown')
      expect(getStatusText('custom-status')).toBe('custom-status')
    })
  })

  describe('getStatusIcon', () => {
    it('should return correct icon for known statuses', () => {
      expect(getStatusIcon('uploading')).toBe('⏳')
      expect(getStatusIcon('pending')).toBe('🔄')
      expect(getStatusIcon('parsing')).toBe('⚙️')
      expect(getStatusIcon('ready')).toBe('✅')
      expect(getStatusIcon('error')).toBe('❌')
      expect(getStatusIcon('timeout')).toBe('⚠️')
    })

    it('should return default icon for unknown statuses', () => {
      expect(getStatusIcon('unknown')).toBe('📄')
      expect(getStatusIcon('custom-status')).toBe('📄')
    })
  })

  describe('isSpinningStatus', () => {
    it('should return true for spinning statuses', () => {
      expect(isSpinningStatus('uploading')).toBe(true)
      expect(isSpinningStatus('pending')).toBe(true)
      expect(isSpinningStatus('parsing')).toBe(true)
    })

    it('should return false for non-spinning statuses', () => {
      expect(isSpinningStatus('ready')).toBe(false)
      expect(isSpinningStatus('error')).toBe(false)
      expect(isSpinningStatus('timeout')).toBe(false)
      expect(isSpinningStatus('unknown')).toBe(false)
    })
  })

  describe('getStageIcon', () => {
    it('should return correct icon for known stages', () => {
      expect(getStageIcon('start')).toBe('🚀')
      expect(getStageIcon('researcher')).toBe('🔍')
      expect(getStageIcon('planner')).toBe('📋')
      expect(getStageIcon('writer')).toBe('✍️')
      expect(getStageIcon('artist')).toBe('🎨')
      expect(getStageIcon('reviewer')).toBe('✅')
    })

    it('should return default icon for unknown stages', () => {
      expect(getStageIcon('unknown')).toBe('⚙️')
      expect(getStageIcon('custom-stage')).toBe('⚙️')
    })
  })

  describe('parseCookies', () => {
    it('should parse JSON array format', () => {
      const jsonCookies = JSON.stringify([
        { name: 'cookie1', value: 'value1', domain: '.example.com', path: '/' },
        { name: 'cookie2', value: 'value2', domain: '.example.com', path: '/' },
      ])
      const result = parseCookies(jsonCookies)
      expect(result).toHaveLength(2)
      expect(result[0]).toEqual({ name: 'cookie1', value: 'value1', domain: '.example.com', path: '/' })
    })

    it('should parse browser cookie string format', () => {
      const cookieString = 'cookie1=value1; cookie2=value2'
      const result = parseCookies(cookieString)
      expect(result).toHaveLength(2)
      expect(result[0]).toEqual({ name: 'cookie1', value: 'value1', domain: '.xiaohongshu.com', path: '/' })
      expect(result[1]).toEqual({ name: 'cookie2', value: 'value2', domain: '.xiaohongshu.com', path: '/' })
    })

    it('should handle cookies with spaces', () => {
      const cookieString = '  cookie1 = value1 ;  cookie2 = value2  '
      const result = parseCookies(cookieString)
      expect(result).toHaveLength(2)
      expect(result[0].name).toBe('cookie1')
      expect(result[0].value).toBe('value1')
    })

    it('should skip empty cookie pairs', () => {
      const cookieString = 'cookie1=value1;;; cookie2=value2'
      const result = parseCookies(cookieString)
      expect(result).toHaveLength(2)
    })

    it('should handle invalid cookie format', () => {
      const cookieString = 'invalid-cookie-without-equals'
      const result = parseCookies(cookieString)
      expect(result).toHaveLength(0)
    })
  })

  describe('escapeHtml', () => {
    it('should escape HTML special characters', () => {
      expect(escapeHtml('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;')
      expect(escapeHtml('<div>Test</div>')).toBe('&lt;div&gt;Test&lt;/div&gt;')
    })

    it('should handle plain text', () => {
      expect(escapeHtml('Hello World')).toBe('Hello World')
      expect(escapeHtml('123')).toBe('123')
    })

    it('should handle special characters', () => {
      expect(escapeHtml('&')).toBe('&amp;')
      expect(escapeHtml('"')).toBe('"')
      expect(escapeHtml("'")).toBe("'")
    })
  })

  describe('formatTime', () => {
    it('should return formatted time string', () => {
      const result = formatTime()
      expect(result).toMatch(/^\d{1,2}:\d{2}:\d{2}$/)
    })
  })

  describe('downloadFile', () => {
    beforeEach(() => {
      // Mock DOM methods
      document.body.appendChild = vi.fn()
      document.body.removeChild = vi.fn()
    })

    it('should create and click download link', () => {
      const clickSpy = vi.fn()
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue({
        click: clickSpy,
        href: '',
        download: '',
        target: '',
      } as any)

      downloadFile('https://example.com/file.pdf', 'test.pdf')

      expect(createElementSpy).toHaveBeenCalledWith('a')
      expect(clickSpy).toHaveBeenCalled()
      expect(document.body.appendChild).toHaveBeenCalled()
      expect(document.body.removeChild).toHaveBeenCalled()

      createElementSpy.mockRestore()
    })
  })

  describe('copyToClipboard', () => {
    it('should copy text to clipboard successfully', async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined)
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: writeTextMock,
        },
        writable: true,
        configurable: true,
      })

      const result = await copyToClipboard('test text')

      expect(result).toBe(true)
      expect(writeTextMock).toHaveBeenCalledWith('test text')
    })

    it('should return false on clipboard error', async () => {
      const writeTextMock = vi.fn().mockRejectedValue(new Error('Clipboard error'))
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: writeTextMock,
        },
        writable: true,
        configurable: true,
      })

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const result = await copyToClipboard('test text')

      expect(result).toBe(false)
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })
  })
})
