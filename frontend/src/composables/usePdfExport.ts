/**
 * 1003.13 PDF 导出增强
 *
 * DOM 截图方案替代纯文本写入。
 */

export interface PdfExportOptions {
  filename?: string
  marginLeft?: number
  marginRight?: number
  marginTop?: number
  marginBottom?: number
  showPageNumbers?: boolean
  scale?: number
}

const DEFAULT_OPTIONS: Required<PdfExportOptions> = {
  filename: 'export.pdf',
  marginLeft: 15,
  marginRight: 15,
  marginTop: 20,
  marginBottom: 20,
  showPageNumbers: true,
  scale: 2,
}

/**
 * SVG->PNG 转换：将 DOM 中所有 SVG 替换为等效 PNG img
 */
export async function convertSvgsToImages(element: HTMLElement): Promise<void> {
  const svgs = element.querySelectorAll('svg')
  const promises = Array.from(svgs).map(async (svg) => {
    try {
      const svgData = new XMLSerializer().serializeToString(svg)
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(svgBlob)

      const img = new Image()
      img.width = svg.clientWidth || 200
      img.height = svg.clientHeight || 200

      await new Promise<void>((resolve, reject) => {
        img.onload = () => {
          URL.revokeObjectURL(url)
          resolve()
        }
        img.onerror = () => {
          URL.revokeObjectURL(url)
          reject(new Error('SVG to image conversion failed'))
        }
        img.src = url
      })

      svg.parentNode?.replaceChild(img, svg)
    } catch {
      // Tolerate individual SVG conversion failures
      console.warn('[pdf] SVG conversion failed, skipping')
    }
  })
  await Promise.all(promises)
}

/**
 * Markdown 预处理：展开 details、清理锚点
 */
export function preprocessMarkdownForPdf(markdown: string): string {
  // Expand <details> tags
  let result = markdown.replace(/<details[^>]*>/gi, '')
  result = result.replace(/<\/details>/gi, '')
  result = result.replace(/<summary[^>]*>(.*?)<\/summary>/gi, '**$1**')
  // Remove anchor links
  result = result.replace(/<a[^>]*name="[^"]*"[^>]*><\/a>/gi, '')
  return result
}

/**
 * 将高 canvas 按 A4 页面尺寸切割为多页
 */
export function splitCanvasIntoPages(
  canvas: HTMLCanvasElement,
  pageWidth: number,
  pageHeight: number,
  marginLeft: number,
  marginTop: number,
  marginBottom: number,
): HTMLCanvasElement[] {
  const contentHeight = pageHeight - marginTop - marginBottom
  const scale = (pageWidth - marginLeft * 2) / canvas.width
  const scaledHeight = canvas.height * scale
  const pageCount = Math.ceil(scaledHeight / contentHeight)
  const pages: HTMLCanvasElement[] = []

  for (let i = 0; i < pageCount; i++) {
    const pageCanvas = document.createElement('canvas')
    pageCanvas.width = canvas.width
    const srcY = Math.floor((i * contentHeight) / scale)
    const srcH = Math.min(Math.floor(contentHeight / scale), canvas.height - srcY)
    pageCanvas.height = srcH

    const ctx = pageCanvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(canvas, 0, srcY, canvas.width, srcH, 0, 0, canvas.width, srcH)
    }
    pages.push(pageCanvas)
  }

  return pages
}

/**
 * 主入口：DOM 元素 -> PDF 文件下载
 * Note: Requires jspdf and html2canvas to be installed (already in project)
 */
export async function exportElementToPdf(
  element: HTMLElement,
  options?: PdfExportOptions,
): Promise<void> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // Dynamic imports to avoid bundling issues
  const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
    import('jspdf'),
    import('html2canvas'),
  ])

  // Clone element to avoid modifying the original DOM
  const clone = element.cloneNode(true) as HTMLElement
  clone.style.position = 'absolute'
  clone.style.left = '-9999px'
  clone.style.width = `${element.offsetWidth}px`
  document.body.appendChild(clone)

  try {
    // Convert SVGs to images in the clone
    await convertSvgsToImages(clone)

    // Render to canvas
    const canvas = await html2canvas(clone, {
      scale: opts.scale,
      useCORS: true,
      logging: false,
    })

    const pdf = new jsPDF('p', 'mm', 'a4')
    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = pdf.internal.pageSize.getHeight()

    // Split into pages
    const pages = splitCanvasIntoPages(
      canvas, pdfWidth, pdfHeight,
      opts.marginLeft, opts.marginTop, opts.marginBottom,
    )

    for (let i = 0; i < pages.length; i++) {
      if (i > 0) pdf.addPage()

      const pageData = pages[i].toDataURL('image/png')
      const imgWidth = pdfWidth - opts.marginLeft - opts.marginRight
      const imgHeight = (pages[i].height / pages[i].width) * imgWidth

      pdf.addImage(pageData, 'PNG', opts.marginLeft, opts.marginTop, imgWidth, imgHeight)

      // Page numbers
      if (opts.showPageNumbers) {
        pdf.setFontSize(9)
        pdf.setTextColor(150)
        pdf.text(
          `${i + 1} / ${pages.length}`,
          pdfWidth / 2,
          pdfHeight - 10,
          { align: 'center' },
        )
      }
    }

    pdf.save(opts.filename)
  } finally {
    document.body.removeChild(clone)
  }
}
