import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.api.schemas import RouteRequest
from src.db.models import SavedRoute
from src.services.alias_resolver import resolve_aliases

client = TestClient(app)

# ==== DUMMY DATABASE MOCKING ====
@pytest.fixture
def mock_db_session():
    with patch("src.api.aliases.get_db_session") as m_db_aliases, \
         patch("src.services.alias_resolver.get_db_session") as m_db_resolver:
        
        session_mock = MagicMock()
        
        m_db_aliases.return_value.__enter__.return_value = session_mock
        m_db_resolver.return_value.__enter__.return_value = session_mock
        
        yield session_mock

def test_create_alias(mock_db_session):
    # Mocking that it doesn't exist yet
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    payload = {
        "alias": "my_commute",
        "source": "A",
        "destination": "B",
        "bidirectional": True
    }
    
    response = client.post("/aliases", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["alias"] == "my_commute"
    assert "B" in data["destinations"]
    
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_alias_resolver_success(mock_db_session):
    # Mock finding a saved route
    saved_route = SavedRoute(
        alias="my_commute",
        source="Point A",
        destinations_json='["Point B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_route
    
    requests = [RouteRequest(alias="my_commute")]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 1
    assert resolved[0].source == "Point A"
    assert resolved[0].destinations == ["Point B"]

def test_alias_resolver_missing(mock_db_session):
    # Mock NOT finding a saved route
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    requests = [RouteRequest(alias="unknown_commute")]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 1
    assert isinstance(resolved[0], dict)
    assert resolved[0]["status"] == "error"
    assert resolved[0]["alias"] == "unknown_commute"

def test_alias_resolver_mixed_arrays(mock_db_session):
    # Mock finding a saved route
    saved_route = SavedRoute(
        alias="my_commute",
        source="Point A",
        destinations_json='["Point B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_route
    
    # Passing both a raw configuration AND a lightweight alias reference
    requests = [
        RouteRequest(source="Raw A", destination="Raw B"),
        RouteRequest(alias="my_commute")
    ]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 2
    # First should pass through cleanly
    assert resolved[0].source == "Raw A"
    
    # Second should inflate
    assert resolved[1].source == "Point A"
    assert resolved[1].destinations == ["Point B"]

def test_get_aliases(mock_db_session):
    saved_route = SavedRoute(
        alias="my_commute",
        source="Point A",
        destinations_json='["Point B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.all.return_value = [saved_route]
    
    response = client.get("/aliases")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["alias"] == "my_commute"

def test_delete_alias(mock_db_session):
    saved_route = SavedRoute(
        alias="my_commute",
        source="Point A",
        destinations_json='["Point B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_route
    
    response = client.delete("/aliases/my_commute")
    assert response.status_code == 200
    assert response.json()["message"] == "Alias 'my_commute' deleted successfully."
    mock_db_session.delete.assert_called_once_with(saved_route)

