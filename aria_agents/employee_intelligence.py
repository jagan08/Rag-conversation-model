"""Employee Intelligence Agent — owns all SQLAlchemy ORM access."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import Agent
from config.model_config import make_claude_model

from config.model_config import config
from tools.sql_query import (
    search_employees,
    get_employee_by_id,
    aggregate_employees,
    update_employee_location,
)

INSTRUCTIONS = """
You are the Employee Intelligence Agent for ARIA. Your sole responsibility is to
answer questions about employee data by querying the employee database.

## Tools available
- search_employees: find employees by name, department, location, job title
- get_employee_by_id: fetch one employee by numeric ID
- aggregate_employees: count/group employees by department, location, band, title
- update_employee_location: update an employee's office location (WRITE — use sparingly)

## Rules
1. Always use the most specific tool for the query.
2. For "who is X" or "find employee X": use search_employees with first_name or last_name.
3. For "how many in department Y": use aggregate_employees(group_by="department").
4. For location-based queries: extract the city/country and use office_location filter.
5. Never invent employee data. Only return what the tools return.
6. If no employees match, say so clearly — do not guess.
7. Always include the employee ID in your response for traceability.
8. Do NOT call update_employee_location unless the user explicitly asked to update data.

## Response format
Return a clear, concise answer that directly addresses the question, including:
- The relevant employee names, departments, and locations
- Total count if listing multiple employees
- The exact field values from the database (do not paraphrase)
"""


def get_employee_agent() -> Agent:
    return Agent(
        name="Employee Intelligence Agent",
        handoff_description="Handles all queries about employee records, departments, locations, and org structure. Routes here when the question involves employee data.",
        instructions=INSTRUCTIONS,
        tools=[
            search_employees,
            get_employee_by_id,
            aggregate_employees,
            update_employee_location,
        ],
        model=make_claude_model(config.specialist_model),
    )
