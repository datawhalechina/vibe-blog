/**
 * 101.08 Phase 3 — deepThinking / backgroundInvestigation 参数传递集成测试
 *
 * 验证 Home.vue 中 createBlogTask 调用时，deep_thinking 和 background_investigation
 * 参数能正确传递到 API 请求体。
 *
 * 由于 Home.vue 依赖过多（router、store、多个子组件），这里采用
 * "直接调用 api.createBlogTask 并用 MSW 拦截请求体" 的方式验证参数传递链路。
 * 这与 Home.vue 中 handleGenerate 的调用路径一致：
 *   deepThinking.value → params.deep_thinking → createBlogTask(params) → fetch body
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createBlogTask } from '@/services/api'

const server = setupServer(
  http.post('/api/blog/generate', () =>
    HttpResponse.json({ success: true, task_id: 'task-toggle-test' })
  )
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Home.vue — deepThinking / backgroundInvestigation parameter passing', () => {
  it('should pass deep_thinking=true to API request body', async () => {
    let capturedBody: any = null
    server.use(
      http.post('/api/blog/generate', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ success: true, task_id: 'task-dt' })
      })
    )

    await createBlogTask({
      topic: 'Test deep thinking',
      article_type: 'tutorial',
      target_length: 'medium',
      deep_thinking: true,
      background_investigation: true,
    })

    expect(capturedBody).toBeTruthy()
    expect(capturedBody.deep_thinking).toBe(true)
  })

  it('should pass background_investigation=false to API request body', async () => {
    let capturedBody: any = null
    server.use(
      http.post('/api/blog/generate', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ success: true, task_id: 'task-bi' })
      })
    )

    await createBlogTask({
      topic: 'Test background investigation',
      article_type: 'tutorial',
      target_length: 'medium',
      deep_thinking: false,
      background_investigation: false,
    })

    expect(capturedBody).toBeTruthy()
    expect(capturedBody.background_investigation).toBe(false)
  })
})
