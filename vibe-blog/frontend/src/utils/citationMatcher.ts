/**
 * 引用匹配工具 — 将文章中的 <a> 链接与 citations 数据匹配
 * 支持两种格式：
 *   1. 外部 URL 链接（旧格式）：<a href="https://...">标题</a>
 *   2. 脚注锚点链接（新格式）：<sup><a href="#ref-N" data-source-url="..."></a></sup>
 */

export interface Citation {
  url: string
  title: string
  domain: string
  snippet: string
  relevance?: number
}

/**
 * 归一化 URL：解码 + 去除尾部斜杠 + 小写 hostname
 */
function normalizeUrl(url: string): string {
  try {
    const decoded = decodeURIComponent(url)
    return decoded.replace(/\/+$/, '').toLowerCase()
  } catch {
    return url.replace(/\/+$/, '').toLowerCase()
  }
}

/**
 * 在 citations 列表中查找匹配的引用
 * @param href - 文章中 <a> 标签的 href
 * @param citations - 后端返回的 citations 列表
 * @returns 匹配到的 Citation 或 null
 */
export function matchCitation(href: string, citations: Citation[]): Citation | null {
  if (!href || !citations?.length) return null

  const normalizedHref = normalizeUrl(href)

  for (const citation of citations) {
    if (normalizeUrl(citation.url) === normalizedHref) {
      return citation
    }
  }

  return null
}

/**
 * 扫描容器内所有 <a> 标签，返回匹配到引用的元素列表。
 * 同时支持外部 URL 匹配和 #ref-N 脚注锚点匹配。
 */
export function scanCitationLinks(
  container: HTMLElement,
  citations: Citation[]
): Array<{ element: HTMLAnchorElement; citation: Citation; index: number }> {
  if (!container || !citations?.length) return []

  const links = container.querySelectorAll<HTMLAnchorElement>('a[href]')
  const results: Array<{ element: HTMLAnchorElement; citation: Citation; index: number }> = []

  links.forEach((link) => {
    const href = link.getAttribute('href') || ''

    // New format: footnote anchor with data-source-url for reliable matching
    const sourceUrl = link.getAttribute('data-source-url')
    if (sourceUrl && href.startsWith('#ref-')) {
      const fnMatch = href.match(/^#ref-(\d+)$/)
      const fnIndex = fnMatch ? parseInt(fnMatch[1], 10) : 0
      const matched = matchCitation(sourceUrl, citations)
      if (matched) {
        results.push({ element: link, citation: matched, index: fnIndex || (citations.indexOf(matched) + 1) })
        return
      }
    }

    // Legacy format: external URL
    if (!href.startsWith('http')) return

    const matched = matchCitation(href, citations)
    if (matched) {
      const index = citations.indexOf(matched) + 1
      results.push({ element: link, citation: matched, index })
    }
  })

  return results
}
