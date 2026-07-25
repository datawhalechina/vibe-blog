import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import CronJobCard from '@/components/cron/CronJobCard.vue'
import type { CronJobView } from '@/composables/useCronJobs'

const errorJob: CronJobView = {
  id: 'cron-1',
  name: 'Daily summary',
  enabled: true,
  schedule: { kind: 'cron', expr: '0 9 * * *' },
  last_status: 'error',
  last_error: 'timeout',
  consecutive_errors: 1,
  generation: { topic: 'Daily summary' },
  tags: [],
}

describe('CronJobCard actions', () => {
  it('keeps supported actions without rendering execution history', () => {
    const wrapper = mount(CronJobCard, { props: { job: errorJob } })

    expect(wrapper.find('button[title="编辑"]').exists()).toBe(false)
    expect(wrapper.find('button[title="暂停"]').exists()).toBe(true)
    expect(wrapper.find('button[title="执行"]').exists()).toBe(true)
    expect(wrapper.find('button[title="重试"]').exists()).toBe(true)
    expect(wrapper.find('button[title="删除"]').exists()).toBe(true)
    expect(wrapper.find('button[title="历史"]').exists()).toBe(false)
  })
})
