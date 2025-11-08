"""Pytest configuration and fixtures for web_service tests."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from web_service.app import app
    return TestClient(app)


@pytest.fixture
def sample_save_data():
    """Provide sample player data for testing."""
    return {
        "players": [
            {
                "guid": "00000000000000000000000000000001",
                "name": "Player 1",
                "guild_id": "99e60934-44f3-e515-2001-e7b71"
            },
            {
                "guid": "1B31C53D000000000000000000000000",
                "name": "Player 2",
                "guild_id": "99e60934-44f3-e515-2001-e7b71"
            }
        ]
    }


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"
