/**
 * 101.08 Home.vue enhance 流程集成测试
 * 测试 handleEnhanceTopic 调用 API 并更新 topic
 */
import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

// 捕获请求
let capturedRequest: any = null

const handlers = [
  http.post('/api/blog/enhance-topic', async ({ request }) => {
    capturedRequest = await request.json()
    return HttpResponse.json({
      success: true,
      enhanced: '优化后的主题：深入理解 LangGraph 工作流引擎',
      original: capturedRequest.topic,
    })
  }),
]

const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterAll(() => server.close())
afterEach(() => {
  server.resetHandlers()
  capturedRequest = null
})

describe('Home.vue — enhance topic 流程', () => {
  it('should call enhance-topic API with topic string', async () => {
    const response = await fetch('/api/blog/enhance-topic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: 'LangGraph' }),
    })
    const data = await response.json()

    expect(capturedRequest).toEqual({ topic: 'LangGraph' })
    expect(data.success).toBe(true)
    expect(data.enhanced).toContain('LangGraph')
    expect(data.original).toBe('LangGraph')
  })

  it('should return enhanced topic different from original', async () => {
    const response = await fetch('/api/blog/enhance-topic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: '简单主题' }),
    })
    const data = await response.json()

    expect(data.enhanced).not.toBe(data.original)
    expect(data.enhanced.length).toBeGreaterThan(0)
  })

  it('should handle API failure gracefully', async () => {
    server.use(
      http.post('/api/blog/enhance-topic', () => {
        return HttpResponse.json(
          { success: false, error: 'LLM 调用失败' },
          { status: 500 }
        )
      })
    )

    const response = await fetch('/api/blog/enhance-topic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: 'test' }),
    })

    expect(response.status).toBe(500)
    const data = await response.json()
    expect(data.success).toBe(false)
  })
})
