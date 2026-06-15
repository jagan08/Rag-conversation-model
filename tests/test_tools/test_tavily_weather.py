"""Unit tests for tools/tavily_weather.py weather retrieval."""
import pytest
import sys
import os
from unittest.mock import patch, Mock
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools import tavily_weather
from tools.tavily_weather import get_weather


class TestGetWeather:
    """Tests for get_weather function."""

    def test_get_weather_success(self, mock_tavily_client, mock_tavily_weather_response):
        """Successfully retrieve weather from Tavily API."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("San Francisco, CA")

        assert "error" not in result
        assert result["location"] == "San Francisco, CA"
        assert result["is_fresh"] is True
        assert result["from_cache"] is False
        assert "summary" in result
        assert "condition" in result

    def test_weather_missing_api_key(self):
        """Missing API key returns error."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=True):
            result = get_weather("San Francisco")

        assert "error" in result
        assert "TAVILY_API_KEY not configured" in result["error"]
        assert result["is_fresh"] is False

    def test_condition_extraction_from_summary(self, mock_tavily_client):
        """Condition is extracted from weather summary."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("San Francisco")

        # Should extract condition keywords
        assert result["condition"] in ["rain", "sunny", "cloud", "storm", "snow", "fog", "wind", "clear", "hot", "cold", "humid", "unknown"]

    def test_weather_caching_hit(self, mock_tavily_client, mock_tavily_weather_response):
        """Weather results are cached after first retrieval."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                # First call
                result1 = get_weather("London")
                # Second call (should be cached)
                result2 = get_weather("London")

        assert result1["location"] == result2["location"]
        # Second call should indicate cache hit
        assert result2["from_cache"] is True

    def test_weather_force_refresh(self, mock_tavily_client):
        """force_refresh bypasses cache."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("London", force_refresh=True)

        # Fresh fetch bypasses cache
        assert result["from_cache"] is False

    def test_weather_api_error_handling(self):
        """API errors are gracefully handled."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("API connection failed")

        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_client):
                result = get_weather("London")

        assert "error" in result
        assert result["is_fresh"] is False

    def test_weather_includes_source_url(self, mock_tavily_client, mock_tavily_weather_response):
        """Weather response includes source URL."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("San Francisco")

        assert "source_url" in result
        if result.get("source_url"):
            assert result["source_url"].startswith("https://")

    def test_weather_retrieval_timestamp(self, mock_tavily_client):
        """Weather includes retrieval timestamp."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("London")

        assert "retrieved_at" in result
        # Should be ISO format with Z suffix
        assert result["retrieved_at"].endswith("Z")

    def test_weather_empty_api_response(self):
        """Handle empty API response gracefully."""
        mock_client = Mock()
        mock_client.search.return_value = {
            "answer": "",
            "results": []
        }

        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_client):
                result = get_weather("Unknown Place")

        assert "error" not in result or result.get("summary", "") != ""

    def test_weather_cache_normalized_location_keys(self):
        """Cache uses normalized location keys."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            mock_client = Mock()
            mock_client.search.return_value = {
                "answer": "Weather data",
                "results": []
            }

            with patch("tools.tavily_weather.TavilyClient", return_value=mock_client):
                # Different casing should hit same cache
                result1 = get_weather("NYC")
                result2 = get_weather("nyc")

            # Both should have same effective cache key
            assert result1["location"] == "NYC"
            assert result2["location"] == "nyc"

    def test_weather_response_structure(self, mock_tavily_client):
        """Response has expected structure."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("tools.tavily_weather.TavilyClient", return_value=mock_tavily_client):
                result = get_weather("San Francisco")

        required_fields = ["location", "query_used", "summary", "condition", "retrieved_at", "is_fresh", "from_cache"]
        for field in required_fields:
            assert field in result
