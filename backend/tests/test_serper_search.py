"""
75.02 Serper Google 搜索集成 — 单元测试
"""
import json
from unittest.mock import patch, MagicMock

from services.blog_generator.services.serper_search_service import SerperSearchService
from services.blog_generator.services.recency_utils import normalize_recency_window_optional


class TestSerperSearchService:
    def test_is_available_with_key(self):
        svc = SerperSearchService(api_key="test-key")
        assert svc.is_available() is True

    def test_is_available_without_key(self):
        svc = SerperSearchService(api_key="")
        assert svc.is_available() is False

    def test_search_no_key(self):
        svc = SerperSearchService(api_key="")
        result = svc.search("test")
        assert result["success"] is False
        assert "未配置" in result["error"]

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "organic": [
                {"title": "Result 1", "link": "http://a.com", "snippet": "snippet 1"},
                {"title": "Result 2", "link": "http://b.com", "snippet": "snippet 2"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc = SerperSearchService(api_key="test-key")
        result = svc.search("AI tutorial", max_results=5)

        assert result["success"] is True
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Result 1"
        assert result["results"][0]["source"] == "Google"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_with_recency_1m_sets_tbs(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"organic": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc = SerperSearchService(api_key="test-key")
        svc.search("AI news", recency_window="1m")

        kwargs = mock_post.call_args.kwargs
        assert kwargs["json"]["tbs"] == "qdr:m"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_with_recency_3m_sets_tbs(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"organic": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc = SerperSearchService(api_key="test-key")
        svc.search("AI news", recency_window="3m")

        kwargs = mock_post.call_args.kwargs
        assert kwargs["json"]["tbs"] == "qdr:m3"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_with_knowledge_graph(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "knowledgeGraph": {
                "title": "Python",
                "description": "A programming language",
                "descriptionLink": "http://wiki.com",
                "attributes": {"Creator": "Guido", "Year": "1991"},
            },
            "organic": [
                {"title": "R1", "link": "http://a.com", "snippet": "s1"},
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc = SerperSearchService(api_key="key")
        result = svc.search("Python")

        assert result["success"] is True
        # knowledge graph + 1 organic
        assert len(result["results"]) == 2
        assert result["results"][0]["source"] == "Google Knowledge Graph"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_with_answer_box(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "answerBox": {
                "title": "What is AI",
                "answer": "Artificial Intelligence",
                "link": "http://wiki.com/ai",
            },
            "organic": [],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        svc = SerperSearchService(api_key="key")
        result = svc.search("what is AI")

        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["source"] == "Google Answer Box"

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_api_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("timeout")

        svc = SerperSearchService(api_key="key")
        result = svc.search("test")

        assert result["success"] is False
        assert "失败" in result["error"] or "timeout" in result["error"].lower()

    @patch("services.blog_generator.services.serper_search_service.requests.post")
    def test_search_retry_on_failure(self, mock_post):
        """失败时应重试"""
        import requests as req
        # 前 2 次失败，第 3 次成功
        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = {"organic": [{"title": "OK", "link": "http://ok.com", "snippet": "ok"}]}
        mock_resp_ok.raise_for_status = MagicMock()

        mock_post.side_effect = [
            req.exceptions.ConnectionError("fail1"),
            req.exceptions.ConnectionError("fail2"),
            mock_resp_ok,
        ]

        svc = SerperSearchService(api_key="key")
        result = svc.search("test")

        assert result["success"] is True
        assert mock_post.call_count == 3

    def test_detect_search_locale_chinese(self):
        gl, hl = SerperSearchService.detect_search_locale("LangGraph 入门教程")
        assert gl == "cn"
        assert hl == "zh-cn"

    def test_detect_search_locale_english(self):
        gl, hl = SerperSearchService.detect_search_locale("How to build RAG")
        assert gl == "us"
        assert hl == "en"

    def test_generate_summary(self):
        svc = SerperSearchService(api_key="key")
        results = [
            {"title": "T1", "content": "C1", "source": "Google"},
            {"title": "T2", "content": "C2", "source": "Google"},
        ]
        summary = svc._generate_summary(results)
        assert "T1" in summary
        assert "C1" in summary

    def test_normalize_recency_alias(self):
        assert normalize_recency_window_optional("30d") == "1m"
        assert normalize_recency_window_optional("three_month") == "3m"
        assert normalize_recency_window_optional("unknown") is None
