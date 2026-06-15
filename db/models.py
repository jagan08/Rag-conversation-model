from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, Integer, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

load_dotenv()

DB_URL = os.getenv("DB_URL", "sqlite:///aria.db")
engine = create_engine(DB_URL, echo=False)


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128), unique=True)
    department: Mapped[str] = mapped_column(String(64))
    job_title: Mapped[str] = mapped_column(String(128))
    office_location: Mapped[str] = mapped_column(String(128))  # plain English city/country
    hire_date: Mapped[str] = mapped_column(String(20))
    salary_band: Mapped[str] = mapped_column(String(16))       # e.g. "L3", "IC5"
    manager_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Employee {self.first_name} {self.last_name} @ {self.office_location}>"


def get_session() -> Session:
    return Session(engine)


def create_tables() -> None:
    Base.metadata.create_all(engine)
