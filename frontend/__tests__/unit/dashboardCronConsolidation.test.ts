import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Dashboard and Cron consolidation', () => {
  it('makes Dashboard the shared queue and cron surface', () => {
    const dashboard = readFileSync(resolve(process.cwd(), 'src/views/Dashboard.vue'), 'utf8')

    expect(dashboard).toContain("type DashboardTab = 'queue' | 'cron'")
    expect(dashboard).toContain('useCronJobs(5000)')
    expect(dashboard).toContain("route.query.tab === 'cron'")
    expect(dashboard).not.toContain('@edit=')
    expect(dashboard).not.toContain("fetch(`${API_BASE}/api/scheduler")
  })

  it('redirects the legacy route and removes the duplicate view', () => {
    const router = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf8')

    expect(existsSync(resolve(process.cwd(), 'src/views/CronManager.vue'))).toBe(false)
    expect(router).toContain("path: '/cron'")
    expect(router).toContain("path: '/dashboard'")
    expect(router).toContain("tab: 'cron'")
    expect(router).not.toContain("import('../views/CronManager.vue')")
  })
})
