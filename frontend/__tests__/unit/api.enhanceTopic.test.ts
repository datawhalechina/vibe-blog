/**
 * 101.08 Prompt 增强 — API 层测试
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { enhanceTopic } from '@/services/api'

const mockEnhancedTopic = '深入理解 LangGraph：从零构建多智能体协作系统的完整指南'

const server = setupServer(
  http.post('/api/blog/enhance-topic', async ({ request }) => {
    const body = (await request.json()) as { topic?: string }
    if (!body?.topic) {
      return HttpResponse.json(
        { success: false, error: 'Topic is required' },
        { status: 400 }
      )
    }
    return HttpResponse.json({
      success: true,
      enhanced_topic: mockEnhancedTopic,
    })
  }),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('enhanceTopic API', () => {
  it('should return enhanced topic on success', async () => {
    const data = await enhanceTopic('LangGraph 入门')
    expect(data.success).toBe(true)
    expect(data.enhanced_topic).toBe(mockEnhancedTopic)
  })

  it('should handle server error gracefully', async () => {
    server.use(
      http.post('/api/blog/enhance-topic', () => {
        return HttpResponse.json(
          { success: false, error: '服务不可用' },
          { status: 500 }
        )
      })
    )
    const data = await enhanceTopic('test')
    expect(data.success).toBe(false)
    expect(data.error).toBe('服务不可用')
  })

  it('should send topic in request body', async () => {
    let receivedTopic = ''
    server.use(
      http.post('/api/blog/enhance-topic', async ({ request }) => {
        const body = (await request.json()) as { topic: string }
        receivedTopic = body.topic
        return HttpResponse.json({ success: true, enhanced_topic: body.topic })
      })
    )
    await enhanceTopic('Vue3 最佳实践')
    expect(receivedTopic).toBe('Vue3 最佳实践')
  })
})
