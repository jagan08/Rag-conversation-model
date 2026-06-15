"""Shared test fixtures for ARIA unit tests."""
import pytest
import os
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Setup test database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

# Import after creating engine to avoid duplicate engine creation
from db.models import Base, Employee


@pytest.fixture(scope="function")
def test_db_session():
    """Create a fresh in-memory SQLite database for each test."""
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_employee_factory(test_db_session):
    """Factory fixture to create test employees."""
    def create_employee(
        first_name: str = "John",
        last_name: str = "Doe",
        email: str = None,
        department: str = "Engineering",
        job_title: str = "Software Engineer",
        office_location: str = "San Francisco, CA, USA",
        hire_date: str = "2022-01-15",
        salary_band: str = "L4",
        manager_id: int = None,
    ) -> Employee:
        if email is None:
            email = f"{first_name.lower()}.{last_name.lower()}@example.com"

        emp = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            department=department,
            job_title=job_title,
            office_location=office_location,
            hire_date=hire_date,
            salary_band=salary_band,
            manager_id=manager_id,
        )
        test_db_session.add(emp)
        test_db_session.commit()
        return emp

    return create_employee


@pytest.fixture
def sample_employees(test_employee_factory):
    """Create a set of sample employees for testing."""
    employees = [
        test_employee_factory(
            first_name="Alice", last_name="Smith", department="Engineering",
            office_location="San Francisco, CA, USA", salary_band="L5"
        ),
        test_employee_factory(
            first_name="Bob", last_name="Johnson", department="Sales",
            office_location="New York, NY, USA", salary_band="L3"
        ),
        test_employee_factory(
            first_name="Charlie", last_name="Brown", department="Engineering",
            office_location="Austin, TX, USA", salary_band="L4"
        ),
        test_employee_factory(
            first_name="Diana", last_name="Prince", department="Product",
            office_location="London, UK", salary_band="L4"
        ),
        test_employee_factory(
            first_name="Eve", last_name="Wilson", department="Sales",
            office_location="Singapore", salary_band="L3"
        ),
    ]
    return employees


@pytest.fixture
def mock_tavily_weather_response():
    """Mock Tavily weather API response."""
    return {
        "answer": "Currently sunny with a high of 72°F and a low of 65°F. Light winds from the west.",
        "results": [
            {
                "title": "San Francisco Weather",
                "content": "San Francisco, CA weather today: sunny, 72°F, winds 5-10 mph",
                "url": "https://example.com/sf-weather",
            }
        ]
    }


@pytest.fixture
def mock_tavily_news_response():
    """Mock Tavily news API response."""
    return {
        "answer": "Recent tech news from San Francisco area",
        "results": [
            {
                "title": "Tech Company Announces New Product",
                "content": "A major tech company in San Francisco announced a new product today.",
                "url": "https://example.com/news1",
                "published_date": "2024-01-15",
            },
            {
                "title": "Startup Raises $50M Funding",
                "content": "A local startup raised $50 million in Series B funding.",
                "url": "https://example.com/news2",
                "published_date": "2024-01-14",
            }
        ]
    }


@pytest.fixture
def mock_tavily_client(mock_tavily_weather_response, mock_tavily_news_response):
    """Mock TavilyClient for API calls."""
    client = Mock()

    def search_side_effect(query: str, **kwargs):
        if "weather" in query.lower():
            return mock_tavily_weather_response
        else:
            return mock_tavily_news_response

    client.search = Mock(side_effect=search_side_effect)
    return client


@pytest.fixture
def mock_embedding_function():
    """Mock embedding function that returns deterministic vectors."""
    import numpy as np

    def embed(text: str) -> list:
        # Simple deterministic hash-based embedding
        hash_val = hash(text) % 1000
        np.random.seed(hash_val)
        return np.random.randn(1536).tolist()  # OpenAI embedding size

    return embed


@pytest.fixture
def monkeypatch_db_session(test_db_session, monkeypatch):
    """Monkeypatch get_session() to return test database."""
    def mock_get_session():
        return test_db_session

    monkeypatch.setattr("db.models.get_session", mock_get_session)
    yield
    # All session cleanup is handled by test_db_session fixture


@pytest.fixture
def mock_litelyf_config(monkeypatch):
    """Mock LiteLLM configuration."""
    config_mock = Mock()
    config_mock.orchestrator_model = "claude-opus"
    config_mock.specialist_model = "claude-sonnet"
    config_mock.lightweight_model = "claude-haiku"
    config_mock.critic_model = "gpt-4"
    config_mock.weather_ttl_seconds = 7200  # 2 hours
    config_mock.news_ttl_seconds = 86400    # 24 hours

    return config_mock
