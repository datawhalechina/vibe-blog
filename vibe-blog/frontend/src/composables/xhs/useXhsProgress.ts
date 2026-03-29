import { ref, reactive, type Ref } from 'vue'

/**
 * 小红书进度管理 Composable
 *
 * 职责：
 * - 进度百分比计算
 * - 阶段状态管理
 * - 时间估算
 * - 进度重置
 */

export interface Stage {
  id: string
  icon: string
  name: string
}

export interface SubProgress {
  current: number
  total: number
}

export function useXhsProgress() {
  // 进度状态
  const progressPercent = ref(0)
  const progressTitle = ref('🚀 小红书内容生成中...')
  const currentStageText = ref('准备中...')
  const timeEstimate = ref('预计剩余: --')
  const hoveredStage = ref<string | null>(null)
  const imageSubProgress = ref<SubProgress | null>(null)

  // 阶段定义
  const stages: Stage[] = [
    { id: 'search', icon: '🔍', name: '搜索' },
    { id: 'outline', icon: '📋', name: '大纲' },
    { id: 'content', icon: '📝', name: '文案' },
    { id: 'storyboard', icon: '🎨', name: '分镜' },
    { id: 'images', icon: '🖼️', name: '图片' },
    { id: 'video', icon: '🎬', name: '视频' }
  ]

  // 阶段状态
  const stageStatuses = reactive<Record<string, string>>({})
  const stageDetails = reactive<Record<string, string>>({})

  // 开始时间
  let startTime: number | null = null

  /**
   * 重置进度
   */
  const reset = () => {
    progressPercent.value = 0
    currentStageText.value = '准备中...'
    timeEstimate.value = '预计剩余: --'
    progressTitle.value = '🚀 小红书内容生成中...'
    imageSubProgress.value = null
    startTime = Date.now()

    stages.forEach(s => {
      stageStatuses[s.id] = 'waiting'
      stageDetails[s.id] = ''
    })
  }

  /**
   * 更新进度
   */
  const updateProgress = (percent: number, message: string) => {
    progressPercent.value = percent
    currentStageText.value = message
    updateTimeEstimate(percent)
  }

  /**
   * 更新阶段指示器
   */
  const updateStageIndicators = (
    currentStage: string,
    subProgress?: SubProgress
  ) => {
    const stageIds = stages.map(s => s.id)
    let stageIndex = stageIds.indexOf(currentStage)
    const isComplete = currentStage === 'complete'
    if (isComplete) stageIndex = stageIds.length

    stageIds.forEach((id, index) => {
      if (index < stageIndex || isComplete) {
        stageStatuses[id] = 'completed'
      } else if (index === stageIndex) {
        stageStatuses[id] = 'active'
        if (id === 'images' && subProgress) {
          imageSubProgress.value = subProgress
        }
      } else {
        stageStatuses[id] = 'waiting'
      }
    })
  }

  /**
   * 更新阶段详情
   */
  const updateStageDetail = (stageId: string, detail: string) => {
    stageDetails[stageId] = detail
  }

  /**
   * 更新时间估算
   */
  const updateTimeEstimate = (progress: number) => {
    if (!startTime || progress <= 0) return

    const elapsed = (Date.now() - startTime) / 1000
    const estimated = (elapsed / progress) * (100 - progress)

    if (estimated > 60) {
      timeEstimate.value = `预计剩余: ${Math.ceil(estimated / 60)} 分钟`
    } else {
      timeEstimate.value = `预计剩余: ${Math.ceil(estimated)} 秒`
    }
  }

  /**
   * 标记完成
   */
  const markComplete = () => {
    progressPercent.value = 100
    progressTitle.value = '🎉 生成完成！'
    currentStageText.value = '全部完成'

    const elapsed = Math.ceil((Date.now() - (startTime || Date.now())) / 1000)
    timeEstimate.value = `总耗时: ${elapsed} 秒`

    stages.forEach(s => (stageStatuses[s.id] = 'completed'))
  }

  /**
   * 标记错误
   */
  const markError = (message: string) => {
    progressTitle.value = '❌ 生成失败'
    currentStageText.value = message
  }

  /**
   * 标记取消
   */
  const markCancelled = () => {
    progressTitle.value = '⚠️ 已取消生成'
    currentStageText.value = '任务已被用户取消'
  }

  /**
   * 获取阶段状态类名
   */
  const getStageClass = (stageId: string): string => {
    const status = stageStatuses[stageId]
    if (status === 'completed') return 'completed'
    if (status === 'active') return 'active'
    return 'waiting'
  }

  /**
   * 获取阶段状态文本
   */
  const getStageStatus = (stageId: string): string => {
    const status = stageStatuses[stageId]
    if (status === 'completed') return '已完成'
    if (status === 'active') return '进行中'
    return '等待中'
  }

  return {
    // 状态（只读）
    progressPercent: readonly(progressPercent) as Readonly<Ref<number>>,
    progressTitle: readonly(progressTitle) as Readonly<Ref<string>>,
    currentStageText: readonly(currentStageText) as Readonly<Ref<string>>,
    timeEstimate: readonly(timeEstimate) as Readonly<Ref<string>>,
    hoveredStage,
    imageSubProgress: readonly(imageSubProgress) as Readonly<Ref<SubProgress | null>>,
    stages,
    stageStatuses,
    stageDetails,

    // 方法
    reset,
    updateProgress,
    updateStageIndicators,
    updateStageDetail,
    markComplete,
    markError,
    markCancelled,
    getStageClass,
    getStageStatus
  }
}

function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>
}
