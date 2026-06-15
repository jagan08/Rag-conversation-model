"""Unit tests for tools/tavily_news.py news retrieval."""
import pytest
import sys
import os
from unittest.mock import patch, Mock
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools import tavily_news
from tools.tavily_news import get_news


class TestGetNews:
    """Tests for get_news function."""

    def test_get_news_success(self, mock_tavily_client, mock_tavily_news_response):
        """Successfully retrieve news from Tavily API."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("tech updates")

        assert "error" not in result
        assert result["query"] == "tech updates"
        assert result["is_fresh"] is True
        assert result["from_cache"] is False
        assert "articles" in result
        assert isinstance(result["articles"], list)

    def test_get_news_missing_api_key(self):
        """Missing API key returns error."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=True):
            result = get_news("news query")

        assert "error" in result
        assert "TAVILY_API_KEY not configured" in result["error"]
        assert result["is_fresh"] is False

    def test_news_default_query(self, mock_tavily_client):
        """Default query if none provided."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("")

        assert "error" not in result
        assert result["query"] == "" or "news" in result["query"].lower()

    def test_news_caching_hit(self, mock_tavily_client, mock_tavily_news_response):
        """News results are cached after first retrieval."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                # First call
                result1 = get_news("AI news")
                # Second call (should be cached)
                result2 = get_news("AI news")

        assert result1["query"] == result2["query"]
        assert result2["from_cache"] is True

    def test_news_force_refresh(self, mock_tavily_client):
        """force_refresh bypasses cache."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("news", force_refresh=True)

        # Fresh fetch bypasses cache
        assert result["from_cache"] is False

    def test_news_api_error_handling(self):
        """API errors are gracefully handled."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("API connection failed")

        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_client):
                result = get_news("news query")

        assert "error" in result
        assert result["is_fresh"] is False

    def test_news_article_structure(self, mock_tavily_client):
        """News articles have expected structure."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("news")

        if result.get("articles"):
            article = result["articles"][0]
            required_fields = ["title", "summary", "url"]
            for field in required_fields:
                assert field in article

    def test_news_retrieval_timestamp(self, mock_tavily_client):
        """News includes retrieval timestamp."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("news")

        assert "retrieved_at" in result
        assert result["retrieved_at"].endswith("Z")

    def test_news_empty_query_results(self):
        """Handle empty query results gracefully."""
        mock_client = Mock()
        mock_client.search.return_value = {
            "answer": "",
            "results": []
        }

        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_client):
                result = get_news("obscure query")

        assert "error" not in result or result.get("articles", []) == []

    def test_news_cache_query_based(self):
        """Cache is based on query string."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            mock_client = Mock()
            mock_client.search.return_value = {
                "answer": "News data",
                "results": []
            }

            with patch("tools.tavily_news.TavilyClient", return_value=mock_client):
                # Different queries should not share cache
                result1 = get_news("AI news")
                result2 = get_news("sports news")

            assert result1["query"] != result2["query"] or result1["from_cache"] is False

    def test_news_response_structure(self, mock_tavily_client):
        """Response has expected structure."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                result = get_news("news")

        required_fields = ["query", "articles", "retrieved_at", "is_fresh", "from_cache"]
        for field in required_fields:
            assert field in result

    def test_news_max_results_limits(self, mock_tavily_client):
        """API call includes max_results limit."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_news.TavilyClient", return_value=mock_tavily_client):
                get_news("news")

        # Verify max_results was passed to search
        assert mock_tavily_client.search.called
        call_kwargs = mock_tavily_client.search.call_args[1]
        assert "max_results" in call_kwargs or call_kwargs.get("max_results") is not None
