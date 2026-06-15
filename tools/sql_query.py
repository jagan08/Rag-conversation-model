"""SQL query function tools for the Employee Intelligence Agent."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any
from agents import function_tool, RunContextWrapper
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models import Employee, get_session, engine


@function_tool
def search_employees(
    first_name: str = "",
    last_name: str = "",
    department: str = "",
    office_location: str = "",
    job_title: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search employees by any combination of fields (case-insensitive partial match).
    Returns matching employee records. Use this for queries like:
    'find employees named John', 'who works in Engineering', 'employees in London'.
    """
    with get_session() as session:
        q = session.query(Employee)
        if first_name:
            q = q.filter(Employee.first_name.ilike(f"%{first_name}%"))
        if last_name:
            q = q.filter(Employee.last_name.ilike(f"%{last_name}%"))
        if department:
            q = q.filter(Employee.department.ilike(f"%{department}%"))
        if office_location:
            q = q.filter(Employee.office_location.ilike(f"%{office_location}%"))
        if job_title:
            q = q.filter(Employee.job_title.ilike(f"%{job_title}%"))

        rows = q.limit(min(limit, 50)).all()
        total = q.count()

        return {
            "employees": [
                {
                    "id": e.id,
                    "first_name": e.first_name,
                    "last_name": e.last_name,
                    "email": e.email,
                    "department": e.department,
                    "job_title": e.job_title,
                    "office_location": e.office_location,
                    "hire_date": e.hire_date,
                    "salary_band": e.salary_band,
                    "manager_id": e.manager_id,
                }
                for e in rows
            ],
            "total_matching": total,
            "returned": len(rows),
            "data_source": "employees table",
        }


@function_tool
def get_employee_by_id(employee_id: int) -> dict[str, Any]:
    """
    Retrieve a single employee record by their numeric ID.
    Use when you know the exact employee ID.
    """
    with get_session() as session:
        e = session.query(Employee).filter(Employee.id == employee_id).first()
        if not e:
            return {"error": f"No employee found with id={employee_id}"}
        return {
            "id": e.id,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "email": e.email,
            "department": e.department,
            "job_title": e.job_title,
            "office_location": e.office_location,
            "hire_date": e.hire_date,
            "salary_band": e.salary_band,
            "manager_id": e.manager_id,
            "data_source": "employees table",
        }


@function_tool
def aggregate_employees(
    group_by: str = "department",
    filter_department: str = "",
    filter_location: str = "",
) -> dict[str, Any]:
    """
    Aggregate employee counts grouped by a field.
    group_by must be one of: 'department', 'office_location', 'salary_band', 'job_title'.
    Optionally filter before aggregating.
    Use for: 'how many employees per department', 'headcount by location'.
    """
    allowed = {"department", "office_location", "salary_band", "job_title"}
    if group_by not in allowed:
        return {"error": f"group_by must be one of {allowed}"}

    col_map = {
        "department": Employee.department,
        "office_location": Employee.office_location,
        "salary_band": Employee.salary_band,
        "job_title": Employee.job_title,
    }
    col = col_map[group_by]

    with get_session() as session:
        from sqlalchemy import func
        q = session.query(col, func.count(Employee.id).label("count"))
        if filter_department:
            q = q.filter(Employee.department.ilike(f"%{filter_department}%"))
        if filter_location:
            q = q.filter(Employee.office_location.ilike(f"%{filter_location}%"))
        rows = q.group_by(col).order_by(func.count(Employee.id).desc()).all()
        return {
            "groups": [{"value": r[0], "count": r[1]} for r in rows],
            "total_groups": len(rows),
            "grouped_by": group_by,
            "data_source": "employees table",
        }


@function_tool(
    name_override="update_employee_location",
    description_override=(
        "Update an employee's office_location. "
        "CAUTION: this is a destructive write operation. "
        "Only call this when the user explicitly asks to update location data."
    ),
    needs_approval=True,
)
def update_employee_location(employee_id: int, new_location: str) -> dict[str, Any]:
    """
    Update the office_location for a specific employee.
    This is a WRITE operation — requires HITL approval via the needs_approval mechanism.
    """
    with get_session() as session:
        e = session.query(Employee).filter(Employee.id == employee_id).first()
        if not e:
            return {"error": f"No employee found with id={employee_id}"}
        old_location = e.office_location
        e.office_location = new_location
        session.commit()
        return {
            "success": True,
            "employee_id": employee_id,
            "name": f"{e.first_name} {e.last_name}",
            "old_location": old_location,
            "new_location": new_location,
        }
