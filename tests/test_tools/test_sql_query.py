"""Unit tests for tools/sql_query.py employee search functions."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.sql_query import search_employees, get_employee_by_id, aggregate_employees, update_employee_location
from db.models import Employee


class TestSearchEmployees:
    """Tests for search_employees function."""

    def test_search_by_first_name(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search employees by first name (case-insensitive partial match)."""
        # Monkeypatch module-level get_session
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(first_name="Alice")

        assert result["returned"] == 1
        assert result["total_matching"] == 1
        assert result["employees"][0]["first_name"] == "Alice"
        assert result["data_source"] == "employees table"

    def test_search_by_last_name(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search employees by last name."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(last_name="Johnson")

        assert result["returned"] == 1
        assert result["employees"][0]["last_name"] == "Johnson"

    def test_search_by_department(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search employees by department."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(department="Engineering")

        assert result["total_matching"] == 2
        assert all(e["department"] == "Engineering" for e in result["employees"])

    def test_search_by_location(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search employees by office location."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(office_location="San Francisco")

        assert result["returned"] == 1
        assert result["employees"][0]["office_location"] == "San Francisco, CA, USA"

    def test_search_case_insensitive(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search is case-insensitive."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(first_name="ALICE")

        assert result["returned"] == 1
        assert result["employees"][0]["first_name"] == "Alice"

    def test_search_partial_match(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search supports partial name matches."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(first_name="Ali")

        assert result["returned"] == 1
        assert result["employees"][0]["first_name"] == "Alice"

    def test_search_multiple_filters(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search with multiple filters (AND logic)."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(department="Engineering", office_location="Austin")

        assert result["returned"] == 1
        assert result["employees"][0]["first_name"] == "Charlie"

    def test_search_no_matches(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search with no matching results."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(first_name="Nonexistent")

        assert result["returned"] == 0
        assert result["total_matching"] == 0
        assert result["employees"] == []

    def test_search_limit(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search respects limit parameter (max 50)."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(limit=2)

        assert result["returned"] <= 2
        assert result["total_matching"] >= result["returned"]

    def test_search_limit_capped_at_50(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Search limit is capped at 50."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = search_employees(limit=100)

        # Should be capped at 50
        assert len(result["employees"]) <= 50


class TestGetEmployeeById:
    """Tests for get_employee_by_id function."""

    def test_get_valid_employee(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Retrieve employee by valid ID."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        emp_id = sample_employees[0].id
        result = get_employee_by_id(emp_id)

        assert "error" not in result
        assert result["id"] == emp_id
        assert result["first_name"] == "Alice"
        assert result["data_source"] == "employees table"

    def test_get_invalid_employee_id(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Retrieve with invalid ID returns error."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = get_employee_by_id(99999)

        assert "error" in result
        assert "No employee found" in result["error"]

    def test_get_employee_returns_all_fields(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Retrieved employee includes all expected fields."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        emp_id = sample_employees[1].id
        result = get_employee_by_id(emp_id)

        required_fields = ["id", "first_name", "last_name", "email", "department",
                          "job_title", "office_location", "hire_date", "salary_band", "manager_id"]
        for field in required_fields:
            assert field in result


class TestAggregateEmployees:
    """Tests for aggregate_employees function."""

    def test_aggregate_by_department(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregate employees by department."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="department")

        assert "groups" in result
        assert result["grouped_by"] == "department"
        assert len(result["groups"]) > 0
        # Should have Engineering (2), Sales (2), Product (1)
        departments = {g["value"]: g["count"] for g in result["groups"]}
        assert departments.get("Engineering") == 2
        assert departments.get("Sales") == 2

    def test_aggregate_by_location(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregate employees by office location."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="office_location")

        assert result["grouped_by"] == "office_location"
        assert len(result["groups"]) == 5  # 5 different locations

    def test_aggregate_by_salary_band(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregate employees by salary band."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="salary_band")

        assert result["grouped_by"] == "salary_band"
        salary_bands = {g["value"]: g["count"] for g in result["groups"]}
        assert salary_bands.get("L3") == 2
        assert salary_bands.get("L4") == 2
        assert salary_bands.get("L5") == 1

    def test_aggregate_by_job_title(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregate employees by job title."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="job_title")

        assert result["grouped_by"] == "job_title"
        assert len(result["groups"]) > 0

    def test_aggregate_invalid_group_by(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Invalid group_by parameter returns error."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="invalid_field")

        assert "error" in result
        assert "group_by must be one of" in result["error"]

    def test_aggregate_with_filter(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregate with department filter."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="office_location", filter_department="Engineering")

        # Should only include Engineering employees
        assert len(result["groups"]) == 2  # SF and Austin

    def test_aggregate_sorted_by_count(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Aggregation results are sorted by count descending."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = aggregate_employees(group_by="department")

        counts = [g["count"] for g in result["groups"]]
        assert counts == sorted(counts, reverse=True)


class TestUpdateEmployeeLocation:
    """Tests for update_employee_location function."""

    def test_update_valid_employee(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Update employee location successfully."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        emp_id = sample_employees[0].id
        old_location = sample_employees[0].office_location
        new_location = "London, UK"

        result = update_employee_location(emp_id, new_location)

        assert result["success"] is True
        assert result["employee_id"] == emp_id
        assert result["old_location"] == old_location
        assert result["new_location"] == new_location

    def test_update_persists_to_db(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Updated location is persisted to database."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        emp_id = sample_employees[0].id
        new_location = "Tokyo, Japan"

        update_employee_location(emp_id, new_location)

        # Verify change persisted
        result = get_employee_by_id(emp_id)
        assert result["office_location"] == new_location

    def test_update_invalid_employee(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Update with invalid ID returns error."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        result = update_employee_location(99999, "New Location")

        assert "error" in result
        assert "No employee found" in result["error"]

    def test_update_includes_name(self, monkeypatch_db_session, test_db_session, sample_employees):
        """Update response includes employee name."""
        from tools import sql_query
        sql_query.get_session = lambda: test_db_session

        emp_id = sample_employees[0].id
        result = update_employee_location(emp_id, "New Location")

        assert "name" in result
        assert result["name"] == "Alice Smith"
