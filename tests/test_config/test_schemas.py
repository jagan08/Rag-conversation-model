"""Unit tests for config/schemas.py Pydantic models."""
import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config.schemas import (
    EmployeeRecord,
    LocationMatch,
    WeatherResult,
    NewsItem,
    CriticVerdict,
    CitationRef,
    EmployeeResult,
    WeatherNewsBundle,
    RAGDocument,
    RAGResult,
)
from pydantic import ValidationError


class TestEmployeeRecord:
    """Tests for EmployeeRecord schema."""

    def test_valid_employee_record(self):
        """Create valid employee record."""
        emp = EmployeeRecord(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            department="Engineering",
            job_title="Software Engineer",
            office_location="San Francisco",
            hire_date="2022-01-15",
            salary_band="L4",
        )

        assert emp.id == 1
        assert emp.first_name == "John"
        assert emp.email == "john@example.com"

    def test_employee_with_manager_id(self):
        """Employee record with manager_id."""
        emp = EmployeeRecord(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            department="Engineering",
            job_title="Software Engineer",
            office_location="San Francisco",
            hire_date="2022-01-15",
            salary_band="L4",
            manager_id=5,
        )

        assert emp.manager_id == 5

    def test_employee_missing_required_field(self):
        """Missing required field raises validation error."""
        with pytest.raises(ValidationError):
            EmployeeRecord(
                id=1,
                first_name="John",
                # Missing other required fields
            )

    def test_employee_invalid_id_type(self):
        """Invalid ID type raises validation error."""
        with pytest.raises(ValidationError):
            EmployeeRecord(
                id="not-an-int",
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                department="Engineering",
                job_title="Engineer",
                office_location="SF",
                hire_date="2022-01-15",
                salary_band="L4",
            )


class TestLocationMatch:
    """Tests for LocationMatch schema."""

    def test_valid_location_match(self):
        """Create valid location match."""
        loc = LocationMatch(
            original="san francisco",
            normalized="San Francisco, California",
            confidence=0.95,
            country="United States",
            search_query="San Francisco weather",
        )

        assert loc.confidence == 0.95
        assert loc.country == "United States"

    def test_location_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            LocationMatch(
                original="sf",
                normalized="San Francisco",
                confidence=1.5,  # Invalid: > 1.0
            )

    def test_location_confidence_zero(self):
        """Confidence can be 0."""
        loc = LocationMatch(
            original="unknown",
            normalized="Unknown",
            confidence=0.0,
        )

        assert loc.confidence == 0.0

    def test_location_defaults(self):
        """Location has sensible defaults."""
        loc = LocationMatch(
            original="NYC",
            normalized="New York City",
            confidence=0.5,
        )

        assert loc.confidence == 0.5
        assert loc.country == ""
        assert loc.search_query == ""


class TestWeatherResult:
    """Tests for WeatherResult schema."""

    def test_valid_weather_result(self):
        """Create valid weather result."""
        weather = WeatherResult(
            location="San Francisco",
            query_used="San Francisco weather",
            summary="Sunny, 72°F",
            temperature_c=22.2,
            condition="sunny",
            retrieved_at="2024-01-15T10:00:00Z",
        )

        assert weather.temperature_c == 22.2
        assert weather.is_fresh is True

    def test_weather_temperature_none(self):
        """Temperature can be None."""
        weather = WeatherResult(
            location="Unknown",
            query_used="weather",
            summary="No data",
            temperature_c=None,
        )

        assert weather.temperature_c is None

    def test_weather_defaults(self):
        """Weather has sensible defaults."""
        weather = WeatherResult(
            location="NYC",
            query_used="NYC weather",
            summary="Data",
        )

        assert weather.is_fresh is True
        assert weather.source_url is None
        assert weather.raw_content == ""


class TestNewsItem:
    """Tests for NewsItem schema."""

    def test_valid_news_item(self):
        """Create valid news item."""
        news = NewsItem(
            title="Tech Company Launches New Product",
            summary="A leading tech company announced...",
            url="https://example.com/article",
            published_at="2024-01-15",
            source="TechNews",
        )

        assert news.title == "Tech Company Launches New Product"
        assert news.relevance_score == 1.0

    def test_news_defaults(self):
        """News has sensible defaults."""
        news = NewsItem(
            title="Breaking News",
            summary="Summary of news",
            url="https://example.com",
        )

        assert news.published_at is None
        assert news.relevance_score == 1.0
        assert news.source == ""

    def test_news_missing_required_fields(self):
        """Missing required fields raises error."""
        with pytest.raises(ValidationError):
            NewsItem(
                title="News",
                # Missing summary and url
            )


class TestCriticVerdict:
    """Tests for CriticVerdict schema."""

    def test_valid_grounded_verdict(self):
        """Create valid GROUNDED verdict."""
        verdict = CriticVerdict(
            verdict="GROUNDED",
            confidence=0.95,
        )

        assert verdict.verdict == "GROUNDED"
        assert verdict.confidence == 0.95

    def test_partial_verdict(self):
        """Create PARTIAL verdict."""
        verdict = CriticVerdict(
            verdict="PARTIAL",
            confidence=0.6,
            issues=["Missing source", "Incomplete coverage"],
        )

        assert verdict.verdict == "PARTIAL"
        assert len(verdict.issues) == 2

    def test_ungrounded_verdict(self):
        """Create UNGROUNDED verdict."""
        verdict = CriticVerdict(
            verdict="UNGROUNDED",
            confidence=0.1,
        )

        assert verdict.verdict == "UNGROUNDED"

    def test_verdict_with_citations(self):
        """Verdict with source citations."""
        citation = CitationRef(
            text="Evidence text",
            source="Wikipedia",
            relevance=0.9,
        )
        verdict = CriticVerdict(
            verdict="GROUNDED",
            citations=[citation],
        )

        assert len(verdict.citations) == 1
        assert verdict.citations[0].source == "Wikipedia"

    def test_verdict_defaults(self):
        """Verdict has sensible defaults."""
        verdict = CriticVerdict()

        assert verdict.verdict == "GROUNDED"
        assert verdict.confidence == 1.0
        assert verdict.citations == []
        assert verdict.issues == []

    def test_confidence_bounds(self):
        """Confidence must be 0-1."""
        with pytest.raises(ValidationError):
            CriticVerdict(confidence=1.5)


class TestCitationRef:
    """Tests for CitationRef schema."""

    def test_valid_citation(self):
        """Create valid citation reference."""
        citation = CitationRef(
            text="Evidence from source",
            source="Database",
            relevance=0.85,
        )

        assert citation.text == "Evidence from source"
        assert citation.relevance == 0.85

    def test_citation_defaults(self):
        """Citation has sensible defaults."""
        citation = CitationRef(text="Evidence")

        assert citation.source == ""
        assert citation.relevance == 1.0

    def test_citation_relevance_bounds(self):
        """Relevance must be 0-1."""
        with pytest.raises(ValidationError):
            CitationRef(text="Text", relevance=-0.1)


class TestRAGResult:
    """Tests for RAGResult schema."""

    def test_valid_rag_result(self):
        """Create valid RAG result."""
        doc = RAGDocument(
            id="doc1",
            content="Document content",
            collection="weather_history",
        )
        result = RAGResult(
            documents=[doc],
            collection="weather_history",
            query="San Francisco weather",
            search_type="semantic",
        )

        assert result.total_found == 0  # Default
        assert result.from_cache is False

    def test_rag_defaults(self):
        """RAG result has sensible defaults."""
        result = RAGResult()

        assert result.documents == []
        assert result.search_type == "semantic"
        assert result.from_cache is False

    def test_rag_document_with_distance(self):
        """RAG document with similarity distance."""
        doc = RAGDocument(
            id="doc1",
            content="Content",
            distance=0.15,  # Low = similar
        )

        assert doc.distance == 0.15


class TestEmployeeResult:
    """Tests for EmployeeResult schema."""

    def test_valid_employee_result(self):
        """Create valid employee result."""
        result = EmployeeResult(
            employees=[],
            total_count=0,
            query_description="Find engineers",
            answer_text="Found 5 engineers",
        )

        assert result.total_count == 0
        assert result.requires_hitl is False

    def test_employee_result_with_hitl(self):
        """Employee result requiring HITL approval."""
        result = EmployeeResult(
            employees=[],
            requires_hitl=True,
            hitl_reason="Sensitive operation",
        )

        assert result.requires_hitl is True
        assert result.hitl_reason == "Sensitive operation"

    def test_employee_result_defaults(self):
        """Employee result defaults."""
        result = EmployeeResult()

        assert result.employees == []
        assert result.total_count == 0
        assert result.requires_hitl is False
        assert result.hitl_reason is None


class TestWeatherNewsBundle:
    """Tests for WeatherNewsBundle schema."""

    def test_valid_bundle(self):
        """Create valid weather/news bundle."""
        weather = WeatherResult(
            location="NYC",
            query_used="NYC weather",
            summary="Data",
        )
        news = NewsItem(
            title="News",
            summary="Summary",
            url="https://example.com",
        )
        bundle = WeatherNewsBundle(
            weather=[weather],
            news=[news],
            locations_queried=["NYC"],
        )

        assert len(bundle.weather) == 1
        assert len(bundle.news) == 1

    def test_bundle_defaults(self):
        """Bundle has sensible defaults."""
        bundle = WeatherNewsBundle()

        assert bundle.weather == []
        assert bundle.news == []
        assert bundle.locations_queried == []
        assert bundle.retrieval_timestamp == ""
