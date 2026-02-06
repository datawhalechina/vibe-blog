import { ref, watch, nextTick, computed } from 'vue'
import mermaid from 'mermaid'
import { useThemeStore } from '../stores/theme'

/**
 * Mermaid 图表渲染 Composable
 *
 * 功能：
 * - 主题配置（深色/浅色模式）
 * - 代码预处理
 * - 图表渲染
 * - 错误处理
 */
export function useMermaidRenderer() {
  const themeStore = useThemeStore()
  const isDark = computed(() => themeStore.isDark)

  /**
   * 获取 Mermaid 主题配置
   */
  const getMermaidTheme = () => {
    if (isDark.value) {
      return {
        theme: 'dark',
        themeVariables: {
          primaryColor: '#818cf8',
          primaryTextColor: '#f8fafc',
          primaryBorderColor: '#6366f1',
          lineColor: '#475569',
          secondaryColor: '#ec4899',
          tertiaryColor: '#22c55e',
          background: '#1a2332',
          mainBkg: '#1a2332',
          secondBkg: '#0a0e1a',
          tertiaryBkg: '#151b2e',
          secondaryTextColor: '#cbd5e1',
          tertiaryTextColor: '#94a3b8',
          textColor: '#f8fafc',
          mainContrastColor: '#f8fafc',
          darkTextColor: '#0a0e1a',
          border1: '#475569',
          border2: '#334155',
          arrowheadColor: '#818cf8',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '14px',
          nodeBorder: '#6366f1',
          clusterBkg: '#1f2937',
          clusterBorder: '#475569',
          defaultLinkColor: '#818cf8',
          titleColor: '#f8fafc',
          edgeLabelBackground: '#1a2332',
          actorBorder: '#6366f1',
          actorBkg: '#1a2332',
          actorTextColor: '#f8fafc',
          actorLineColor: '#94a3b8',
          signalColor: '#f8fafc',
          signalTextColor: '#f8fafc',
          labelBoxBkgColor: '#1a2332',
          labelBoxBorderColor: '#6366f1',
          labelTextColor: '#f8fafc',
          loopTextColor: '#f8fafc',
          noteBorderColor: '#ec4899',
          noteBkgColor: '#1f2937',
          noteTextColor: '#f8fafc',
          activationBorderColor: '#6366f1',
          activationBkgColor: '#1f2937',
          sequenceNumberColor: '#0a0e1a',
          sectionBkgColor: '#1f2937',
          altSectionBkgColor: '#151b2e',
          sectionBkgColor2: '#0a0e1a',
          excludeBkgColor: '#334155',
          taskBorderColor: '#6366f1',
          taskBkgColor: '#1a2332',
          taskTextColor: '#f8fafc',
          taskTextLightColor: '#cbd5e1',
          taskTextOutsideColor: '#f8fafc',
          taskTextClickableColor: '#818cf8',
          activeTaskBorderColor: '#ec4899',
          activeTaskBkgColor: '#1f2937',
          gridColor: '#334155',
          doneTaskBkgColor: '#22c55e',
          doneTaskBorderColor: '#16a34a',
          critBorderColor: '#ef4444',
          critBkgColor: '#dc2626',
          todayLineColor: '#ec4899',
          labelColor: '#0a0e1a',
          errorBkgColor: '#dc2626',
          errorTextColor: '#f8fafc',
          classText: '#f8fafc',
          fillType0: '#1a2332',
          fillType1: '#1f2937',
          fillType2: '#151b2e',
          fillType3: '#0a0e1a',
          fillType4: '#334155',
          fillType5: '#475569',
          fillType6: '#64748b',
          fillType7: '#94a3b8'
        }
      }
    } else {
      return {
        theme: 'base',
        themeVariables: {
          primaryColor: '#e0e7ff',
          primaryTextColor: '#0f172a',
          primaryBorderColor: '#6366f1',
          lineColor: '#cbd5e1',
          secondaryColor: '#fce7f3',
          tertiaryColor: '#dcfce7',
          background: '#ffffff',
          mainBkg: '#ffffff',
          secondBkg: '#f8fafc',
          tertiaryBkg: '#f1f5f9',
          secondaryTextColor: '#475569',
          tertiaryTextColor: '#64748b',
          textColor: '#0f172a',
          mainContrastColor: '#0f172a',
          darkTextColor: '#ffffff',
          border1: '#e2e8f0',
          border2: '#cbd5e1',
          arrowheadColor: '#6366f1',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '14px',
          nodeBorder: '#6366f1',
          clusterBkg: '#f8fafc',
          clusterBorder: '#cbd5e1',
          defaultLinkColor: '#6366f1',
          titleColor: '#0f172a',
          edgeLabelBackground: '#ffffff',
          actorBorder: '#6366f1',
          actorBkg: '#e0e7ff',
          actorTextColor: '#1e293b',
          actorLineColor: '#64748b',
          signalColor: '#0f172a',
          signalTextColor: '#0f172a',
          labelBoxBkgColor: '#e0e7ff',
          labelBoxBorderColor: '#6366f1',
          labelTextColor: '#1e293b',
          loopTextColor: '#0f172a',
          noteBorderColor: '#ec4899',
          noteBkgColor: '#fce7f3',
          noteTextColor: '#831843',
          activationBorderColor: '#6366f1',
          activationBkgColor: '#e0e7ff',
          sequenceNumberColor: '#ffffff',
          sectionBkgColor: '#f8fafc',
          altSectionBkgColor: '#ffffff',
          sectionBkgColor2: '#e0e7ff',
          excludeBkgColor: '#f1f5f9',
          taskBorderColor: '#6366f1',
          taskBkgColor: '#e0e7ff',
          taskTextColor: '#1e293b',
          taskTextLightColor: '#475569',
          taskTextOutsideColor: '#0f172a',
          taskTextClickableColor: '#4f46e5',
          activeTaskBorderColor: '#ec4899',
          activeTaskBkgColor: '#fce7f3',
          gridColor: '#e2e8f0',
          doneTaskBkgColor: '#dcfce7',
          doneTaskBorderColor: '#22c55e',
          critBorderColor: '#ef4444',
          critBkgColor: '#fee2e2',
          todayLineColor: '#ec4899',
          labelColor: '#ffffff',
          errorBkgColor: '#fee2e2',
          errorTextColor: '#991b1b',
          classText: '#0f172a',
          fillType0: '#e0e7ff',
          fillType1: '#fce7f3',
          fillType2: '#dcfce7',
          fillType3: '#fef3c7',
          fillType4: '#dbeafe',
          fillType5: '#f3e8ff',
          fillType6: '#fce7f3',
          fillType7: '#e0f2fe'
        }
      }
    }
  }

  /**
   * 初始化 Mermaid
   */
  const initializeMermaid = () => {
    mermaid.initialize({
      startOnLoad: false,
      ...getMermaidTheme(),
      securityLevel: 'loose',
      logLevel: 'error',
      flowchart: {
        htmlLabels: true,
        useMaxWidth: true,
        curve: 'basis',
        padding: 20,
        nodeSpacing: 50,
        rankSpacing: 50,
        diagramPadding: 20,
        wrappingWidth: 200
      },
      sequence: {
        diagramMarginX: 50,
        diagramMarginY: 20,
        actorMargin: 50,
        width: 150,
        height: 65,
        boxMargin: 10,
        boxTextMargin: 5,
        noteMargin: 10,
        messageMargin: 35,
        mirrorActors: true,
        bottomMarginAdj: 1,
        useMaxWidth: true,
        rightAngles: false,
        showSequenceNumbers: false,
        wrap: true,
        wrapPadding: 10
      },
      gantt: {
        titleTopMargin: 25,
        barHeight: 20,
        barGap: 4,
        topPadding: 50,
        leftPadding: 75,
        gridLineStartPadding: 35,
        fontSize: 12,
        numberSectionStyles: 4,
        axisFormat: '%Y-%m-%d',
        useMaxWidth: true
      },
      journey: {
        diagramMarginX: 50,
        diagramMarginY: 20,
        actorMargin: 50,
        width: 150,
        height: 65,
        boxMargin: 10,
        useMaxWidth: true
      },
      class: {
        arrowMarkerAbsolute: false,
        useMaxWidth: true
      },
      git: {
        arrowMarkerAbsolute: false,
        useMaxWidth: true
      },
      state: {
        dividerMargin: 10,
        sizeUnit: 5,
        padding: 8,
        textHeight: 10,
        titleShift: -15,
        noteMargin: 10,
        forkWidth: 70,
        forkHeight: 7,
        miniPadding: 2,
        fontSizeFactor: 5.02,
        fontSize: 24,
        labelHeight: 16,
        edgeLengthFactor: '20',
        compositTitleSize: 35,
        radius: 5,
        useMaxWidth: true
      },
      er: {
        diagramPadding: 20,
        layoutDirection: 'TB',
        minEntityWidth: 100,
        minEntityHeight: 75,
        entityPadding: 15,
        stroke: 'gray',
        fill: 'honeydew',
        fontSize: 12,
        useMaxWidth: true
      },
      pie: {
        useMaxWidth: true
      },
      quadrantChart: {
        chartWidth: 500,
        chartHeight: 500,
        titleFontSize: 20,
        titlePadding: 10,
        quadrantPadding: 5,
        xAxisLabelPadding: 5,
        yAxisLabelPadding: 5,
        xAxisLabelFontSize: 16,
        yAxisLabelFontSize: 16,
        quadrantLabelFontSize: 16,
        quadrantTextTopPadding: 5,
        pointTextPadding: 5,
        pointLabelFontSize: 12,
        pointRadius: 5,
        xAxisPosition: 'top',
        yAxisPosition: 'left',
        quadrantInternalBorderStrokeWidth: 1,
        quadrantExternalBorderStrokeWidth: 2
      }
    })
  }

  /**
   * 预处理 Mermaid 代码
   */
  const preprocessMermaidCode = (code: string): string => {
    // 1. 替换中文标点符号
    code = code.replace(/[""'']/g, '"')
    code = code.replace(/（/g, '(').replace(/）/g, ')')
    code = code.replace(/【/g, '[').replace(/】/g, ']')
    code = code.replace(/：/g, ':')
    code = code.replace(/；/g, ';')
    code = code.replace(/，/g, ',')

    // 2. 修复空标签问题
    code = code.replace(/(\bsubgraph\s+\w+)\[""\]/g, '$1[" "]')
    code = code.replace(/(\w+)\[""\]/g, '$1[" "]')

    // 3. 处理节点文本中的特殊字符
    code = code.replace(/\[([^\]]+)\]/g, (match, content) => {
      if (content.startsWith('"') && content.endsWith('"')) return match
      if (/[\\\/\n·•–—\(\)="]/.test(content) || content.includes('\\n')) {
        let fixed = content.replace(/\\n/g, '<br/>')
        fixed = fixed.replace(/"/g, '#quot;')
        return '["' + fixed + '"]'
      }
      return match
    })

    // 4. 移除多余的空行
    code = code.split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .join('\n')

    return code
  }

  /**
   * 创建错误提示块
   */
  const createMermaidErrorBlock = (code: string, errorMsg: string): HTMLElement => {
    const div = document.createElement('div')
    div.className = 'mermaid-error-container'
    div.innerHTML = `
      <div class="mermaid-error-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>Mermaid 图表渲染失败</span>
      </div>
      <div class="mermaid-error-message">
        <strong>错误信息:</strong> ${errorMsg}
      </div>
      <details class="mermaid-error-details">
        <summary>查看原始代码</summary>
        <pre><code>${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>
      </details>
      <div class="mermaid-error-tips">
        <strong>常见问题:</strong>
        <ul>
          <li>检查图表类型声明 (graph, flowchart, sequenceDiagram 等)</li>
          <li>确保节点 ID 不包含特殊字符</li>
          <li>检查箭头语法 (-->, --->, ==>, etc.)</li>
          <li>确保所有引号、括号成对出现</li>
        </ul>
      </div>
    `
    return div
  }

  /**
   * 渲染 Mermaid 图表
   */
  const renderMermaid = async (container?: HTMLElement | null) => {
    await nextTick()

    const targetContainer = container || document.querySelector('.blog-content')
    if (!targetContainer) return

    const mermaidBlocks = targetContainer.querySelectorAll('pre code.language-mermaid')
    if (mermaidBlocks.length === 0) return

    for (let i = 0; i < mermaidBlocks.length; i++) {
      const block = mermaidBlocks[i] as HTMLElement
      const originalCode = block.textContent || ''

      try {
        const code = preprocessMermaidCode(originalCode)
        const div = document.createElement('div')
        div.className = 'mermaid-container'
        div.id = 'mermaid-' + i

        const { svg } = await mermaid.render('mermaid-graph-' + i + '-' + Date.now(), code)
        div.innerHTML = svg
        block.parentElement?.replaceWith(div)
      } catch (e: any) {
        console.warn('Mermaid 图表渲染失败:', e.message, '\n原始代码:', originalCode)
        const errorDiv = createMermaidErrorBlock(originalCode, e.message)
        block.parentElement?.replaceWith(errorDiv)
      }
    }
  }

  // 初始化 Mermaid
  initializeMermaid()

  // 监听主题变化
  watch(isDark, () => {
    initializeMermaid()
    renderMermaid()
  })

  return {
    renderMermaid,
    initializeMermaid
  }
}
