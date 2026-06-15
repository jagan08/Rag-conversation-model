"""Unit tests for tools/location_matcher.py location normalization."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.location_matcher import normalize_location, batch_normalize_locations


class TestNormalizeLocation:
    """Tests for normalize_location function."""

    def test_exact_match_san_francisco(self):
        """Exact match returns high confidence."""
        result = normalize_location("san francisco, ca, usa")

        assert result["normalized"] == "San Francisco, California"
        assert result["country"] == "United States"
        assert result["confidence"] == 1.0
        assert result["match_type"] == "exact"
        assert "San Francisco" in result["search_query"]

    def test_exact_match_london(self):
        """Exact match for London location."""
        result = normalize_location("london, uk")

        assert result["normalized"] == "London, England"
        assert result["country"] == "United Kingdom"
        assert result["confidence"] == 1.0
        assert result["match_type"] == "exact"

    def test_exact_match_case_insensitive(self):
        """Exact matching is case-insensitive."""
        result = normalize_location("LONDON, UK")

        assert result["normalized"] == "London, England"
        assert result["confidence"] == 1.0

    def test_empty_whitespace_trim(self):
        """Leading/trailing whitespace is trimmed."""
        result = normalize_location("  london, uk  ")

        assert result["normalized"] == "London, England"
        assert result["confidence"] == 1.0

    def test_fuzzy_match_partial(self):
        """Fuzzy match for partial location strings."""
        result = normalize_location("san fran")

        assert result["normalized"] == "San Francisco, California"
        assert 0.4 <= result["confidence"] <= 1.0
        assert result["match_type"] == "fuzzy"

    def test_fuzzy_match_with_typo(self):
        """Fuzzy match handles token-based similarity."""
        result = normalize_location("san francisco california")

        # Should still match based on token overlap
        assert result["confidence"] >= 0.4

    def test_fallback_unknown_location(self):
        """Unknown location falls back to direct normalization."""
        result = normalize_location("Smallville, USA")

        assert result["normalized"] == "Smallville"
        assert result["confidence"] == 0.5  # Fallback confidence
        assert result["match_type"] == "fallback"
        assert result["search_query"] == "Smallville weather"

    def test_original_preserved(self):
        """Original input is always preserved."""
        original = "new york, ny, usa"
        result = normalize_location(original)

        assert result["original"] == original

    def test_search_query_generated(self):
        """Search query is generated for API calls."""
        result = normalize_location("san francisco, ca, usa")

        assert "search_query" in result
        assert isinstance(result["search_query"], str)
        assert len(result["search_query"]) > 0


class TestBatchNormalizeLocations:
    """Tests for batch_normalize_locations function."""

    def test_batch_process_multiple_locations(self):
        """Process multiple locations in batch."""
        locations = ["san francisco, ca, usa", "london, uk", "tokyo, japan"]
        result = batch_normalize_locations(locations)

        assert "locations" in result
        assert len(result["locations"]) == 3
        assert result["total"] == 3

    def test_batch_exact_matches(self):
        """Batch processing recognizes exact matches."""
        locations = ["san francisco, ca, usa", "london, uk"]
        result = batch_normalize_locations(locations)

        assert result["locations"]["san francisco, ca, usa"]["confidence"] == 1.0
        assert result["locations"]["london, uk"]["confidence"] == 1.0

    def test_batch_mixed_matches(self):
        """Batch handles mix of exact and fallback matches."""
        locations = ["london, uk", "unknown place xyz"]
        result = batch_normalize_locations(locations)

        assert result["locations"]["london, uk"]["confidence"] == 1.0
        assert result["locations"]["unknown place xyz"]["confidence"] == 0.5

    def test_batch_search_queries_generated(self):
        """All items in batch have search queries."""
        locations = ["san francisco, ca, usa", "london, uk"]
        result = batch_normalize_locations(locations)

        for loc, norm_data in result["locations"].items():
            assert "search_query" in norm_data
            assert isinstance(norm_data["search_query"], str)

    def test_batch_cap_at_20(self):
        """Batch processing is capped at 20 locations."""
        # Create list of 30 locations
        locations = [f"city{i}" for i in range(30)]
        result = batch_normalize_locations(locations)

        assert result["total"] == 20  # Capped at 20

    def test_batch_with_duplicates(self):
        """Batch handles duplicate locations."""
        locations = ["london, uk", "london, uk", "san francisco, ca, usa"]
        result = batch_normalize_locations(locations)

        # Both London entries should be present
        assert result["total"] == 3

    def test_batch_normalized_format(self):
        """Batch response has normalized format for each location."""
        locations = ["san francisco, ca, usa"]
        result = batch_normalize_locations(locations)

        loc_data = result["locations"]["san francisco, ca, usa"]
        assert "normalized" in loc_data
        assert "search_query" in loc_data
        assert "confidence" in loc_data
