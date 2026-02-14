/**
 * MSW Request Handlers
 * Mock API endpoints for testing DeerFlow feature migration (101.04~101.09)
 */
import { http, HttpResponse } from 'msw'

// ========== Mock Data ==========

export const mockEvaluation = {
  grade: 'A-',
  overall_score: 83,
  scores: {
    factual_accuracy: 85,
    completeness: 78,
    coherence: 92,
    relevance: 88,
    citation_quality: 70,
    writing_quality: 85,
  },
  strengths: ['代码示例丰富且可运行', '章节结构清晰有层次'],
  weaknesses: ['引用来源偏少'],
  suggestions: ['补充 3-5 个权威引用', '在核心概念处增加图示说明'],
  summary: '文章结构清晰，建议补充更多引用。',
  word_count: 3500,
  citation_count: 8,
  image_count: 4,
  code_block_count: 6,
}

export const mockCitations = [
  {
    url: 'https://langchain-ai.github.io/langgraph/',
    title: 'LangGraph: Multi-Agent Workflows',
    domain: 'langchain-ai.github.io',
    snippet: 'A framework for building stateful, multi-actor applications...',
  },
  {
    url: 'https://docs.python.org/3/library/asyncio.html',
    title: 'asyncio — Asynchronous I/O',
    domain: 'docs.python.org',
    snippet: 'This module provides infrastructure for writing single-threaded...',
  },
]

export const mockEnhancedTopic = '深入理解 LangGraph：从零构建多智能体协作系统的完整指南'

// ========== Handlers ==========

export const handlers = [
  // 101.08: Prompt Enhancement - enhance topic
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

  // 101.04: Quality Evaluation
  http.get('/api/blog/:id/evaluate', ({ params }) => {
    const { id } = params
    if (id === 'not-found') {
      return HttpResponse.json(
        { success: false, error: 'Article not found' },
        { status: 404 }
      )
    }
    return HttpResponse.json({
      success: true,
      evaluation: mockEvaluation,
    })
  }),

  // Blog generation with new params (101.06: deep_thinking, background_investigation)
  http.post('/api/blog/generate', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({
      success: true,
      task_id: `task-${Date.now()}`,
      // Echo back params for testing
      _params: {
        deep_thinking: body?.deep_thinking ?? false,
        background_investigation: body?.background_investigation ?? true,
      },
    })
  }),

  // History record with citations (101.05)
  http.get('/api/history/:id', ({ params }) => {
    const { id } = params
    return HttpResponse.json({
      success: true,
      record: {
        id,
        topic: 'Test Article',
        content_type: 'blog',
        created_at: '2026-02-14T10:00:00Z',
        citations: mockCitations,
      },
    })
  }),
]
