"""
75.08 批量多查询并行搜索 — 单元测试（TDD）

覆盖两层改动：
  A. SerperSearchService.batch_search()
     1. 无 Key / 空查询 边界条件
     2. 多查询并行执行
     3. URL 去重
     4. 部分查询失败（错误收集 + 成功结果不丢）
     5. max_workers 限制
     6. recency_window 透传
     7. 摘要生成
  B. ResearcherAgent._try_batch_search() + search() 降级
     8. Serper 可用 → 走并行路径
     9. Serper 不可用 → 降级串行
    10. batch_search 异常 → 降级串行
    11. batch_search 返回空 → 降级串行
"""
import os
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from services.blog_generator.services.serper_search_service import SerperSearchService


# ============================================================
# Fixtures
# ============================================================

MOCK_ORGANIC_A = {
    "organic": [
        {"title": "Result A1", "link": "http://a1.com", "snippet": "snippet a1"},
        {"title": "Result A2", "link": "http://a2.com", "snippet": "snippet a2"},
    ]
}

MOCK_ORGANIC_B = {
    "organic": [
        {"title": "Result B1", "link": "http://b1.com", "snippet": "snippet b1"},
        {"title": "Result B2", "link": "http://a1.com", "snippet": "duplicate of a1"},  # 与 A1 重复
    ]
}

MOCK_ORGANIC_C = {
    "organic": [
        {"title": "Result C1", "link": "http://c1.com", "snippet": "snippet c1"},
    ]
}

MOCK_EMPTY = {"organic": []}


def _mock_resp(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


# ============================================================
# A. SerperSearchService.batch_search()
# ============================================================

class TestBatchSearchEdgeCases:
    """边界条件"""

    def test_batch_search_no_key(self):
        svc = SerperSearchService(api_key="")
        result = svc.batch_search(["q1", "q2"])
        assert result["success"] is False
        assert "未配置" in result["error"]
        assert result["results"] == []

    def test_batch_search_empty_queries(self):
        svc = SerperSearchService(api_key="key")
        result = svc.batch_search([])
        assert result["success"] is True
        assert result["results"] == []
        assert result["error"] is None

    def test_batch_search_single_query(self):
        """单查询应退化为普通搜索"""
        svc = SerperSearchService(api_key="key")
        with patch.object(svc, "search", return_value={
            "success": True, "results": [{"title": "T", "url": "http://t.com", "content": "c", "source": "Google"}]
        }) as mock_search:
            result = svc.batch_search(["only one"])
            assert result["success"] is True
            assert len(result["results"]) == 1
            mock_search.assert_called_once()


class TestBatchSearchParallel:
    """并行执行 + 合并"""

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_multiple_queries_all_called(self, mock_post):
        """多查询应全部执行"""
        mock_post.side_effect = [_mock_resp(MOCK_ORGANIC_A), _mock_resp(MOCK_ORGANIC_C)]

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"], max_results_per_query=5)

        assert result["success"] is True
        assert mock_post.call_count == 2

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_results_merged(self, mock_post):
        """不同查询的结果应合并"""
        mock_post.side_effect = [_mock_resp(MOCK_ORGANIC_A), _mock_resp(MOCK_ORGANIC_C)]

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"])

        # A: 2 条 + C: 1 条 = 3 条（无重复）
        assert len(result["results"]) == 3

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_max_workers_respected(self, mock_post):
        """10 个查询 max_workers=2 应全部执行"""
        mock_post.return_value = _mock_resp(MOCK_EMPTY)

        svc = SerperSearchService(api_key="key")
        svc.batch_search([f"q{i}" for i in range(10)], max_workers=2)

        assert mock_post.call_count == 10


class TestBatchSearchDedup:
    """URL 去重"""

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_url_dedup(self, mock_post):
        """相同 URL 应去重"""
        mock_post.side_effect = [_mock_resp(MOCK_ORGANIC_A), _mock_resp(MOCK_ORGANIC_B)]

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"])

        # A: a1.com, a2.com  B: b1.com, a1.com(重复)
        urls = [r["url"] for r in result["results"]]
        assert len(urls) == len(set(urls)), f"存在重复 URL: {urls}"
        assert len(result["results"]) == 3  # a1, a2, b1

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_dedup_preserves_first_occurrence(self, mock_post):
        """去重应保留第一次出现的条目"""
        mock_post.side_effect = [_mock_resp(MOCK_ORGANIC_A), _mock_resp(MOCK_ORGANIC_B)]

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"])

        # a1.com 的第一次出现是 "Result A1"（来自 MOCK_ORGANIC_A）
        a1_entries = [r for r in result["results"] if r["url"] == "http://a1.com"]
        assert len(a1_entries) == 1
        assert a1_entries[0]["title"] == "Result A1"


class TestBatchSearchPartialFailure:
    """部分失败"""

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    @patch("services.blog_generator.services.serper_search_service.time.sleep")
    def test_partial_failure_collects_errors(self, mock_sleep, mock_post):
        """部分查询失败时应收集错误但不丢失成功结果"""
        import requests as req

        # q1 成功，q2 全部重试失败
        mock_post.side_effect = [
            _mock_resp(MOCK_ORGANIC_A),
            req.exceptions.ConnectionError("fail"),
            req.exceptions.ConnectionError("fail"),
            req.exceptions.ConnectionError("fail"),
        ]

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"])

        assert result["success"] is True
        assert len(result["results"]) >= 1  # q1 的结果不丢
        assert result["error"] is not None  # q2 的错误被记录

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    @patch("services.blog_generator.services.serper_search_service.time.sleep")
    def test_all_queries_fail(self, mock_sleep, mock_post):
        """所有查询都失败时应返回空结果 + 错误"""
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("all fail")

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1", "q2"])

        assert result["success"] is True  # batch_search 本身不失败
        assert result["results"] == []
        assert result["error"] is not None


class TestBatchSearchRecency:
    """recency_window 透传"""

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_recency_window_passed_to_search(self, mock_post):
        """recency_window 应透传到每个子搜索"""
        mock_post.return_value = _mock_resp(MOCK_EMPTY)

        svc = SerperSearchService(api_key="key")
        svc.batch_search(["q1"], recency_window="1m")

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"].get("tbs") == "qdr:m"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_no_recency_no_tbs(self, mock_post):
        """不传 recency_window 时不应有 tbs"""
        mock_post.return_value = _mock_resp(MOCK_EMPTY)

        svc = SerperSearchService(api_key="key")
        svc.batch_search(["q1"])

        call_kwargs = mock_post.call_args.kwargs
        assert "tbs" not in call_kwargs["json"]


class TestBatchSearchSummary:
    """摘要生成"""

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_summary_included(self, mock_post):
        mock_post.return_value = _mock_resp(MOCK_ORGANIC_A)

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1"])

        assert "summary" in result
        assert "Result A1" in result["summary"]

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_empty_results_empty_summary(self, mock_post):
        mock_post.return_value = _mock_resp(MOCK_EMPTY)

        svc = SerperSearchService(api_key="key")
        result = svc.batch_search(["q1"])

        assert result["summary"] == ""


# ============================================================
# B. ResearcherAgent._try_batch_search() + search() 降级
# ============================================================

class TestResearcherBatchSearchIntegration:
    """Researcher 层的并行/降级逻辑"""

    def _make_researcher(self, search_service=None):
        """构造一个最小化的 ResearcherAgent"""
        from services.blog_generator.agents.researcher import ResearcherAgent
        mock_llm = MagicMock()
        mock_llm.chat.return_value = '["query1", "query2", "query3"]'
        return ResearcherAgent(
            llm_client=mock_llm,
            search_service=search_service,
        )

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_batch_path_when_serper_available(self, mock_get_serper):
        """Serper 可用时应走并行路径"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.return_value = {
            "success": True,
            "results": [
                {"title": "R1", "url": "http://r1.com", "content": "c1", "source": "Google"},
                {"title": "R2", "url": "http://r2.com", "content": "c2", "source": "Google"},
            ],
        }
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1", "q2"], max_results=10)

        assert result is not None
        assert len(result) == 2
        mock_serper.batch_search.assert_called_once()

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_fallback_when_serper_none(self, mock_get_serper):
        """get_serper_service() 返回 None 时应降级"""
        mock_get_serper.return_value = None

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1"], max_results=10)

        assert result is None

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_fallback_when_serper_unavailable(self, mock_get_serper):
        """Serper 实例存在但 is_available=False 时应降级"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = False
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1"], max_results=10)

        assert result is None

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_fallback_when_batch_search_exception(self, mock_get_serper):
        """batch_search 抛异常时应降级（不崩溃）"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.side_effect = RuntimeError("API down")
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1"], max_results=10)

        assert result is None

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_fallback_when_batch_search_returns_failure(self, mock_get_serper):
        """batch_search 返回 success=False 时应降级"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.return_value = {
            "success": False, "results": [], "error": "some error"
        }
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1"], max_results=10)

        assert result is None

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_fallback_when_batch_search_returns_empty(self, mock_get_serper):
        """batch_search 返回空结果时应降级"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.return_value = {
            "success": True, "results": [], "error": None
        }
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        result = researcher._try_batch_search(["q1"], max_results=10)

        assert result is None

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_max_results_per_query_calculation(self, mock_get_serper):
        """max_results_per_query 应为 max_results // len(queries)"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.return_value = {
            "success": True,
            "results": [{"title": "R", "url": "http://r.com", "content": "c", "source": "G"}],
        }
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        researcher._try_batch_search(["q1", "q2", "q3"], max_results=9)

        call_kwargs = mock_serper.batch_search.call_args.kwargs
        assert call_kwargs["max_results_per_query"] == 3  # 9 // 3

    @patch("services.blog_generator.services.serper_search_service.get_serper_service")
    def test_max_results_per_query_at_least_one(self, mock_get_serper):
        """max_results_per_query 至少为 1"""
        mock_serper = MagicMock()
        mock_serper.is_available.return_value = True
        mock_serper.batch_search.return_value = {
            "success": True,
            "results": [{"title": "R", "url": "http://r.com", "content": "c", "source": "G"}],
        }
        mock_get_serper.return_value = mock_serper

        researcher = self._make_researcher()
        # max_results=1, queries=3 → 1//3=0 → max(1,0)=1
        researcher._try_batch_search(["q1", "q2", "q3"], max_results=1)

        call_kwargs = mock_serper.batch_search.call_args.kwargs
        assert call_kwargs["max_results_per_query"] == 1
