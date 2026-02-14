"""
75.09 Google Scholar 学术搜索服务 — 单元测试（TDD）

覆盖：
  1. 基础可用性检查（有/无 API Key）
  2. 单查询搜索（成功 / 无 Key / API 异常）
  3. 学术元数据解析（year / citedBy / publicationInfo / pdfUrl）
  4. 批量并行搜索（多查询 + URL 去重）
  5. 重试机制（指数退避）
  6. 摘要生成
  7. 全局实例管理（init / get 懒加载）
"""
import os
import time
from unittest.mock import patch, MagicMock, call

import pytest

from services.blog_generator.services.scholar_search_service import (
    ScholarSearchService,
    init_scholar_service,
    get_scholar_service,
)


# ============================================================
# Fixtures
# ============================================================

MOCK_SCHOLAR_RESPONSE = {
    "organic": [
        {
            "title": "Attention Is All You Need",
            "link": "https://arxiv.org/abs/1706.03762",
            "pdfUrl": "https://arxiv.org/pdf/1706.03762",
            "snippet": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            "year": 2017,
            "citedBy": 120000,
            "publicationInfo": "Advances in Neural Information Processing Systems",
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "link": "https://arxiv.org/abs/1810.04805",
            "snippet": "We introduce a new language representation model called BERT...",
            "year": 2019,
            "citedBy": 85000,
            "publicationInfo": "NAACL-HLT 2019",
        },
    ]
}

MOCK_SCHOLAR_RESPONSE_2 = {
    "organic": [
        {
            "title": "GPT-4 Technical Report",
            "link": "https://arxiv.org/abs/2303.08774",
            "pdfUrl": "https://arxiv.org/pdf/2303.08774",
            "snippet": "We report the development of GPT-4...",
            "year": 2023,
            "citedBy": 5000,
            "publicationInfo": "arXiv preprint",
        },
        {
            # 与 MOCK_SCHOLAR_RESPONSE 中的第一条重复（用于测试去重）
            "title": "Attention Is All You Need (duplicate)",
            "link": "https://arxiv.org/abs/1706.03762",
            "pdfUrl": "https://arxiv.org/pdf/1706.03762",
            "snippet": "duplicate entry",
            "year": 2017,
            "citedBy": 120000,
            "publicationInfo": "NeurIPS 2017",
        },
    ]
}

MOCK_EMPTY_RESPONSE = {"organic": []}


def _make_mock_resp(data: dict) -> MagicMock:
    """构造 mock requests.Response"""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


# ============================================================
# 1. 基础可用性
# ============================================================

class TestScholarAvailability:
    def test_is_available_with_key(self):
        svc = ScholarSearchService(api_key="test-key")
        assert svc.is_available() is True

    def test_is_available_without_key(self):
        svc = ScholarSearchService(api_key="")
        assert svc.is_available() is False

    def test_default_config(self):
        svc = ScholarSearchService(api_key="key")
        assert svc.default_max == 5
        assert svc.timeout == 10

    def test_custom_config(self):
        svc = ScholarSearchService(api_key="key", config={"max_results": 10, "timeout": 30})
        assert svc.default_max == 10
        assert svc.timeout == 30


# ============================================================
# 2. 单查询搜索
# ============================================================

class TestScholarSearch:
    def test_search_no_key(self):
        """无 API Key 时应返回失败"""
        svc = ScholarSearchService(api_key="")
        result = svc.search("transformer")
        assert result["success"] is False
        assert "未配置" in result["error"]
        assert result["results"] == []

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_search_success(self, mock_post):
        """正常搜索应返回结构化结果"""
        mock_post.return_value = _make_mock_resp(MOCK_SCHOLAR_RESPONSE)

        svc = ScholarSearchService(api_key="test-key")
        result = svc.search("transformer attention mechanism", max_results=5)

        assert result["success"] is True
        assert result["error"] is None
        assert len(result["results"]) == 2

        # 验证 API 调用参数
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["q"] == "transformer attention mechanism"
        assert call_kwargs["json"]["num"] == 5
        assert call_kwargs["headers"]["X-API-KEY"] == "test-key"

        # 验证请求 URL
        call_args = mock_post.call_args
        assert call_args[0][0] == ScholarSearchService.SCHOLAR_URL

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_search_empty_results(self, mock_post):
        """无结果时应返回空列表"""
        mock_post.return_value = _make_mock_resp(MOCK_EMPTY_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        result = svc.search("nonexistent topic xyz123")

        assert result["success"] is True
        assert result["results"] == []
        assert result["summary"] == ""

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_search_max_results_cap(self, mock_post):
        """max_results 不应超过 20"""
        mock_post.return_value = _make_mock_resp(MOCK_EMPTY_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        svc.search("test", max_results=50)

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["num"] == 20


# ============================================================
# 3. 学术元数据解析
# ============================================================

class TestScholarMetadataParsing:
    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_parse_all_fields(self, mock_post):
        """应正确解析所有学术元数据字段"""
        mock_post.return_value = _make_mock_resp(MOCK_SCHOLAR_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        result = svc.search("attention")

        paper = result["results"][0]
        assert paper["title"] == "Attention Is All You Need"
        assert paper["url"] == "https://arxiv.org/pdf/1706.03762"  # pdfUrl 优先
        assert paper["content"] == MOCK_SCHOLAR_RESPONSE["organic"][0]["snippet"]
        assert paper["source"] == "Google Scholar"
        assert paper["year"] == 2017
        assert paper["cited_by"] == 120000
        assert paper["publication"] == "Advances in Neural Information Processing Systems"

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_parse_no_pdf_url_fallback_to_link(self, mock_post):
        """无 pdfUrl 时应回退到 link"""
        mock_post.return_value = _make_mock_resp(MOCK_SCHOLAR_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        result = svc.search("BERT")

        # 第二条结果没有 pdfUrl
        paper = result["results"][1]
        assert paper["url"] == "https://arxiv.org/abs/1810.04805"

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_parse_missing_optional_fields(self, mock_post):
        """缺失可选字段时应有默认值"""
        mock_post.return_value = _make_mock_resp({
            "organic": [
                {
                    "title": "Minimal Paper",
                    # 无 link, pdfUrl, snippet, year, citedBy, publicationInfo
                }
            ]
        })

        svc = ScholarSearchService(api_key="key")
        result = svc.search("minimal")

        paper = result["results"][0]
        assert paper["title"] == "Minimal Paper"
        assert paper["url"] == ""
        assert paper["content"] == ""
        assert paper["year"] == ""
        assert paper["cited_by"] == 0
        assert paper["publication"] == ""


# ============================================================
# 4. 批量并行搜索 + 去重
# ============================================================

class TestScholarBatchSearch:
    def test_batch_search_no_key(self):
        """无 API Key 时批量搜索应返回失败"""
        svc = ScholarSearchService(api_key="")
        result = svc.batch_search(["q1", "q2"])
        assert result["success"] is False
        assert "未配置" in result["error"]

    def test_batch_search_empty_queries(self):
        """空查询列表应返回空结果"""
        svc = ScholarSearchService(api_key="key")
        result = svc.batch_search([])
        assert result["success"] is True
        assert result["results"] == []

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_batch_search_multiple_queries(self, mock_post):
        """多查询应并行执行并合并结果"""
        mock_post.side_effect = [
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE),
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE_2),
        ]

        svc = ScholarSearchService(api_key="key")
        result = svc.batch_search(["transformer", "GPT-4"], max_results_per_query=5)

        assert result["success"] is True
        assert mock_post.call_count == 2

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_batch_search_url_dedup(self, mock_post):
        """批量搜索应按 URL 去重"""
        mock_post.side_effect = [
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE),
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE_2),
        ]

        svc = ScholarSearchService(api_key="key")
        result = svc.batch_search(["transformer", "GPT-4"])

        # MOCK_SCHOLAR_RESPONSE: 2 条（pdfUrl: 1706.03762, link: 1810.04805）
        # MOCK_SCHOLAR_RESPONSE_2: 2 条（pdfUrl: 2303.08774, pdfUrl: 1706.03762 重复）
        # 去重后应为 3 条
        urls = [r["url"] for r in result["results"]]
        assert len(urls) == len(set(urls)), f"存在重复 URL: {urls}"
        assert len(result["results"]) == 3

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_batch_search_partial_failure(self, mock_post):
        """部分查询失败时应收集错误但不影响成功的结果"""
        import requests as req

        mock_post.side_effect = [
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE),
            req.exceptions.ConnectionError("timeout"),
            req.exceptions.ConnectionError("timeout"),
            req.exceptions.ConnectionError("timeout"),
        ]

        svc = ScholarSearchService(api_key="key")
        result = svc.batch_search(["good query", "bad query"])

        assert result["success"] is True
        assert len(result["results"]) >= 1  # 至少有第一个查询的结果
        assert result["error"] is not None  # 应记录错误

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_batch_search_max_workers(self, mock_post):
        """并行度应受 max_workers 限制"""
        mock_post.return_value = _make_mock_resp(MOCK_EMPTY_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        # 10 个查询，max_workers=2
        svc.batch_search([f"query_{i}" for i in range(10)], max_workers=2)

        # 所有查询都应被执行
        assert mock_post.call_count == 10


# ============================================================
# 5. 重试机制
# ============================================================

class TestScholarRetry:
    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    @patch("services.blog_generator.services.scholar_search_service.time.sleep")
    def test_retry_on_failure_then_success(self, mock_sleep, mock_post):
        """前 2 次失败、第 3 次成功应返回成功"""
        import requests as req

        mock_post.side_effect = [
            req.exceptions.ConnectionError("fail1"),
            req.exceptions.ConnectionError("fail2"),
            _make_mock_resp(MOCK_SCHOLAR_RESPONSE),
        ]

        svc = ScholarSearchService(api_key="key")
        result = svc.search("test")

        assert result["success"] is True
        assert mock_post.call_count == 3

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    @patch("services.blog_generator.services.scholar_search_service.time.sleep")
    def test_retry_all_fail(self, mock_sleep, mock_post):
        """所有重试都失败应返回错误"""
        import requests as req

        mock_post.side_effect = req.exceptions.ConnectionError("persistent failure")

        svc = ScholarSearchService(api_key="key")
        result = svc.search("test")

        assert result["success"] is False
        assert mock_post.call_count == ScholarSearchService.MAX_RETRIES
        assert "失败" in result["error"] or "persistent failure" in result["error"]

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    @patch("services.blog_generator.services.scholar_search_service.time.sleep")
    def test_retry_exponential_backoff(self, mock_sleep, mock_post):
        """重试间隔应为指数退避（2, 4 秒）"""
        import requests as req

        mock_post.side_effect = req.exceptions.ConnectionError("fail")

        svc = ScholarSearchService(api_key="key")
        svc.search("test")

        # MAX_RETRIES=3, 重试 2 次（第 1 次失败后等 2s，第 2 次失败后等 4s）
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)   # RETRY_BASE_WAIT * 2^0
        mock_sleep.assert_any_call(4)   # RETRY_BASE_WAIT * 2^1


# ============================================================
# 6. 摘要生成
# ============================================================

class TestScholarSummary:
    def test_generate_summary_empty(self):
        svc = ScholarSearchService(api_key="key")
        assert svc._generate_summary([]) == ""

    def test_generate_summary_with_metadata(self):
        svc = ScholarSearchService(api_key="key")
        results = [
            {
                "title": "Attention Is All You Need",
                "content": "The dominant sequence transduction models...",
                "year": 2017,
                "cited_by": 120000,
                "publication": "NeurIPS 2017",
            }
        ]
        summary = svc._generate_summary(results)

        assert "[Scholar]" in summary
        assert "Attention Is All You Need" in summary
        assert "(2017)" in summary
        assert "[cited: 120000]" in summary
        assert "NeurIPS 2017" in summary

    def test_generate_summary_missing_metadata(self):
        """缺失元数据时摘要不应包含空括号"""
        svc = ScholarSearchService(api_key="key")
        results = [
            {
                "title": "Paper Without Year",
                "content": "Some content",
                "year": "",
                "cited_by": 0,
                "publication": "",
            }
        ]
        summary = svc._generate_summary(results)

        assert "Paper Without Year" in summary
        assert "()" not in summary
        assert "[cited:" not in summary
        assert " — " not in summary

    @patch("services.blog_generator.services.scholar_search_service.requests.post")
    def test_search_result_includes_summary(self, mock_post):
        """搜索结果应包含摘要字段"""
        mock_post.return_value = _make_mock_resp(MOCK_SCHOLAR_RESPONSE)

        svc = ScholarSearchService(api_key="key")
        result = svc.search("attention")

        assert "summary" in result
        assert "Attention Is All You Need" in result["summary"]


# ============================================================
# 7. 全局实例管理
# ============================================================

class TestScholarGlobalInstance:
    def setup_method(self):
        """每个测试前重置全局实例"""
        import services.blog_generator.services.scholar_search_service as mod
        mod._scholar_service = None

    @patch.dict(os.environ, {"SERPER_API_KEY": "env-key"})
    def test_init_scholar_service(self):
        svc = init_scholar_service()
        assert svc is not None
        assert svc.api_key == "env-key"

    def test_init_scholar_service_with_config(self):
        svc = init_scholar_service(config={"SERPER_API_KEY": "config-key"})
        assert svc.api_key == "config-key"

    def test_init_scholar_service_no_key(self):
        svc = init_scholar_service(config={})
        assert svc is not None
        assert svc.is_available() is False

    @patch.dict(os.environ, {"SERPER_API_KEY": "lazy-key"})
    def test_get_scholar_service_lazy_init(self):
        """首次调用 get_scholar_service 应懒加载初始化"""
        svc = get_scholar_service()
        assert svc is not None
        assert svc.api_key == "lazy-key"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_scholar_service_no_key_returns_none(self):
        """无 API Key 时 get_scholar_service 应返回 None"""
        # 确保环境变量中没有 SERPER_API_KEY
        os.environ.pop("SERPER_API_KEY", None)
        svc = get_scholar_service()
        assert svc is None

    @patch.dict(os.environ, {"SERPER_API_KEY": "key"})
    def test_get_scholar_service_returns_same_instance(self):
        """多次调用应返回同一实例"""
        svc1 = get_scholar_service()
        svc2 = get_scholar_service()
        assert svc1 is svc2
