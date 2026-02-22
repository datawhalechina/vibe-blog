"""
Google Scholar search integration -- unit tests

Tests for:
- SerperScholarService: core scholar search via Serper /scholar endpoint
- ScholarSearchTool: BaseSearchTool adapter
- ScholarRetriever: RetrieverRegistry adapter
"""
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_scholar_response():
    """Mock Serper Scholar API response"""
    return {
        "organic": [
            {
                "title": "Attention Is All You Need",
                "link": "https://arxiv.org/abs/1706.03762",
                "snippet": "The dominant sequence transduction models are based on complex recurrent...",
                "publicationInfo": "Advances in Neural Information Processing Systems, 2017",
                "year": 2017,
                "citedBy": 95000,
                "pdfUrl": "https://arxiv.org/pdf/1706.03762.pdf",
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "link": "https://arxiv.org/abs/1810.04805",
                "snippet": "We introduce a new language representation model called BERT...",
                "publicationInfo": "NAACL 2019",
                "year": 2019,
                "citedBy": 75000,
            },
        ]
    }


@pytest.fixture
def scholar_service():
    """SerperScholarService instance with test key"""
    from services.blog_generator.services.serper_scholar_service import SerperScholarService
    return SerperScholarService(api_key="test-key", timeout=5)


class TestSerperScholarService:
    """SerperScholarService unit tests"""

    def test_is_available_with_key(self):
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        assert svc.is_available() is True

    def test_is_available_without_key(self):
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="")
        assert svc.is_available() is False

    def test_search_no_key(self):
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="")
        result = svc.search("test")
        assert result["success"] is False
        assert "not configured" in result["error"].lower()

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_success(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search("transformer attention")
        assert result["success"] is True
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Attention Is All You Need"
        assert result["results"][0]["cited_by"] == 95000
        assert result["results"][0]["year"] == 2017
        assert result["results"][0]["pdf_url"] == "https://arxiv.org/pdf/1706.03762.pdf"
        assert result["results"][0]["publication_info"] == "Advances in Neural Information Processing Systems, 2017"

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_no_organic(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"searchParameters": {"q": "xyz"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search("nonexistent query xyz")
        assert result["success"] is True
        assert len(result["results"]) == 0

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_api_error_with_retry(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("timeout")
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search("test")
        assert result["success"] is False
        assert mock_post.call_count == 3  # MAX_RETRIES

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_retry_then_success(self, mock_post, mock_scholar_response):
        import requests as req
        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = mock_scholar_response
        mock_resp_ok.raise_for_status = MagicMock()
        mock_post.side_effect = [req.exceptions.ConnectionError("fail"), mock_resp_ok]
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search("test")
        assert result["success"] is True
        assert mock_post.call_count == 2

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_uses_scholar_endpoint(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        svc.search("test")
        call_args = mock_post.call_args
        assert "scholar" in call_args[0][0]

    def test_parse_scholar_results_partial_metadata(self, scholar_service):
        data = {"organic": [
            {"title": "Paper A", "link": "http://a.com"},
            {"title": "Paper B", "link": "http://b.com", "year": 2023},
        ]}
        results = scholar_service._parse_scholar_results(data)
        assert len(results) == 2
        assert results[0]["title"] == "Paper A"
        assert results[0]["year"] == ""
        assert results[0]["cited_by"] == 0
        assert results[0]["pdf_url"] == ""
        assert results[1]["year"] == 2023

    def test_generate_summary(self, scholar_service):
        results = [
            {"title": "Paper A", "year": 2023, "cited_by": 100, "snippet": "Abstract A"},
            {"title": "Paper B", "year": "", "cited_by": 0, "snippet": ""},
        ]
        summary = scholar_service._generate_summary(results)
        assert "Paper A" in summary
        assert "2023" in summary
        assert "cited: 100" in summary


class TestSerperScholarBatch:
    """Batch search tests"""

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_batch_parallel(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search_batch(["query1", "query2"])
        assert result["success"] is True
        assert len(result["results"]) == 4  # 2 queries x 2 results each
        assert mock_post.call_count == 2

    def test_search_batch_empty_queries(self):
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search_batch([])
        assert result["success"] is True
        assert len(result["results"]) == 0

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_batch_partial_failure(self, mock_post, mock_scholar_response):
        import requests as req
        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = mock_scholar_response
        mock_resp_ok.raise_for_status = MagicMock()
        mock_post.side_effect = [
            mock_resp_ok,
            req.exceptions.ConnectionError("fail"),
            req.exceptions.ConnectionError("fail"),
            req.exceptions.ConnectionError("fail"),
        ]
        from services.blog_generator.services.serper_scholar_service import SerperScholarService
        svc = SerperScholarService(api_key="test-key")
        result = svc.search_batch(["query1", "query2"])
        assert result["success"] is True
        assert len(result["results"]) == 2  # only query1 results


class TestScholarSearchTool:
    """ScholarSearchTool adapter tests"""

    def test_is_available_with_key(self):
        from services.blog_generator.tools.scholar import ScholarSearchTool
        tool = ScholarSearchTool(api_key="test-key")
        assert tool.is_available() is True

    def test_is_available_without_key(self):
        from services.blog_generator.tools.scholar import ScholarSearchTool
        tool = ScholarSearchTool(api_key="")
        assert tool.is_available() is False

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_returns_search_response(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.tools.scholar import ScholarSearchTool
        tool = ScholarSearchTool(api_key="test-key")
        response = tool.search("transformer")
        assert response.success is True
        assert len(response.results) == 2
        assert response.results[0].source == "scholar"
        assert response.results[0].source_type == "scholar"
        assert "Attention Is All You Need" in response.results[0].title

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    def test_search_result_content_includes_metadata(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.tools.scholar import ScholarSearchTool
        tool = ScholarSearchTool(api_key="test-key")
        response = tool.search("transformer")
        content = response.results[0].content
        assert "2017" in content or "Year" in content
        assert "95000" in content or "Cited" in content

    def test_format_scholar_content(self):
        from services.blog_generator.tools.scholar import ScholarSearchTool
        r = {
            "snippet": "A great paper",
            "publication_info": "NeurIPS 2017",
            "year": 2017,
            "cited_by": 95000,
            "pdf_url": "https://example.com/paper.pdf",
        }
        content = ScholarSearchTool._format_scholar_content(r)
        assert "A great paper" in content
        assert "NeurIPS 2017" in content
        assert "2017" in content
        assert "95000" in content
        assert "https://example.com/paper.pdf" in content

    def test_format_scholar_content_minimal(self):
        from services.blog_generator.tools.scholar import ScholarSearchTool
        r = {"snippet": "Just a snippet"}
        content = ScholarSearchTool._format_scholar_content(r)
        assert "Just a snippet" in content


class TestScholarRetriever:
    """ScholarRetriever integration with RetrieverRegistry"""

    def test_scholar_registered(self):
        from services.blog_generator.retriever_registry import RetrieverRegistry
        assert "scholar" in RetrieverRegistry.list_registered()

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"})
    def test_scholar_retriever_available(self):
        from services.blog_generator.retriever_registry import RetrieverRegistry, ScholarRetriever
        RetrieverRegistry._reset()
        retriever = ScholarRetriever()
        assert retriever.is_available() is True
        assert retriever.name == "scholar"

    @patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False)
    def test_scholar_retriever_unavailable_without_key(self):
        from services.blog_generator.retriever_registry import RetrieverRegistry, ScholarRetriever
        RetrieverRegistry._reset()
        retriever = ScholarRetriever()
        assert retriever.is_available() is False

    @patch("services.blog_generator.services.serper_scholar_service.requests.post")
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"})
    def test_scholar_retriever_search(self, mock_post, mock_scholar_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_scholar_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        from services.blog_generator.retriever_registry import ScholarRetriever
        retriever = ScholarRetriever()
        results = retriever.search("transformer")
        assert len(results) == 2
        assert results[0].title == "Attention Is All You Need"
        assert results[0].source == "scholar"
        assert "2017" in results[0].body
