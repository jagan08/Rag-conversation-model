"""Seed 500 mock employees into the ARIA database."""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from db.models import Employee, create_tables, engine

fake = Faker()
Faker.seed(42)
random.seed(42)

DEPARTMENTS = [
    "Engineering", "Product", "Design", "Data Science", "Marketing",
    "Sales", "Finance", "Legal", "HR", "Customer Success", "Operations",
]

JOB_TITLES = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Staff Engineer", "Engineering Manager"],
    "Product": ["Product Manager", "Senior PM", "Director of Product"],
    "Design": ["UI Designer", "UX Researcher", "Senior Designer", "Design Lead"],
    "Data Science": ["Data Scientist", "ML Engineer", "Analytics Engineer", "Research Scientist"],
    "Marketing": ["Marketing Manager", "Content Strategist", "Growth Lead"],
    "Sales": ["Account Executive", "Sales Engineer", "VP Sales"],
    "Finance": ["Financial Analyst", "Controller", "CFO Staff"],
    "Legal": ["Legal Counsel", "Paralegal", "Compliance Officer"],
    "HR": ["HR Business Partner", "Recruiter", "Total Rewards Analyst"],
    "Customer Success": ["Customer Success Manager", "Support Engineer", "VP Customer Success"],
    "Operations": ["Operations Manager", "IT Admin", "Chief of Staff"],
}

OFFICE_LOCATIONS = [
    "San Francisco, CA, USA", "New York, NY, USA", "Austin, TX, USA",
    "Seattle, WA, USA", "Boston, MA, USA", "Chicago, IL, USA",
    "London, UK", "Berlin, Germany", "Amsterdam, Netherlands",
    "Paris, France", "Toronto, Canada", "Singapore",
    "Sydney, Australia", "Tokyo, Japan", "Bangalore, India",
    "Dublin, Ireland", "Stockholm, Sweden", "Zurich, Switzerland",
]

SALARY_BANDS = ["L2", "L3", "L4", "L5", "L6", "IC4", "IC5", "M1", "M2", "M3"]


def _random_hire_date() -> str:
    start = date(2015, 1, 1)
    end = date(2024, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def seed(n: int = 500, confirm: bool = True) -> None:
    if confirm:
        print(f"\nARIA HITL: About to insert {n} employee records into the database.")
        answer = input("   Type 'yes' to proceed: ").strip().lower()
        if answer != "yes":
            print("   Seed cancelled.")
            sys.exit(0)

    create_tables()

    employees: list[Employee] = []
    emails_seen: set[str] = set()

    for i in range(1, n + 1):
        dept = random.choice(DEPARTMENTS)
        title = random.choice(JOB_TITLES[dept])
        email = fake.unique.email()
        while email in emails_seen:
            email = fake.unique.email()
        emails_seen.add(email)

        employees.append(Employee(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            department=dept,
            job_title=title,
            office_location=random.choice(OFFICE_LOCATIONS),
            hire_date=_random_hire_date(),
            salary_band=random.choice(SALARY_BANDS),
            manager_id=random.randint(1, i - 1) if i > 10 else None,
        ))

    with Session(engine) as session:
        session.add_all(employees)
        session.commit()

    print(f"   OK: Seeded {n} employees successfully.")


if __name__ == "__main__":
    seed()
