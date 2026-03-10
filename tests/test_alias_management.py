import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.main import app
from src.api.schemas import RouteRequest
from src.db.models import SavedRoute, DestinationBatch
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

def test_create_alias_update_existing(mock_db_session):
    existing = SavedRoute(
        alias="my_commute",
        source="Old A",
        destinations_json='["Old B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing
    
    payload = {
        "alias": "my_commute",
        "source": "New A",
        "destinations": ["New B"]
    }
    
    response = client.post("/aliases", json=payload)
    
    assert response.status_code == 200
    assert existing.source == "New A"
    assert existing.destinations_json == '["New B"]'
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()

def test_create_alias_missing_fields(mock_db_session):
    # Validation error from pydantic will handle this if it's completely missing,
    # but based on the code in `aliases.py`, it expects RouteRequest which makes fields optional.
    # Missing source:
    payload = {"alias": "test", "destination": "B"}
    response = client.post("/aliases", json=payload)
    assert response.status_code in [400, 422] # fastAPI validation might catch it first
    
    # Missing destinations:
    payload2 = {"alias": "test", "source": "A"}
    response2 = client.post("/aliases", json=payload2)
    assert response2.status_code in [400, 422]
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

def test_get_alias_specific(mock_db_session):
    saved_route = SavedRoute(
        alias="my_commute",
        source="Point A",
        destinations_json='["Point B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_route
    
    response = client.get("/aliases/my_commute")
    assert response.status_code == 200
    assert response.json()["alias"] == "my_commute"

def test_get_alias_specific_not_found(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/aliases/unknown")
    assert response.status_code == 404

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

def test_delete_alias_not_found(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.delete("/aliases/unknown")
    assert response.status_code == 404
    mock_db_session.delete.assert_not_called()

def test_alias_resolver_destination_batch_success(mock_db_session):
    # Mock finding a destination batch
    batch = DestinationBatch(
        alias="my_batch",
        destinations_json='["Dest1", "Dest2"]'
    )
    # The first query in resolve_aliases is for DestinationBatch, when `destination_batch_alias` is set.
    mock_db_session.query.return_value.filter.return_value.first.return_value = batch
    
    requests = [RouteRequest(source="Source A", destination_batch_alias="my_batch")]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 1
    assert resolved[0].source == "Source A"
    assert resolved[0].destinations == ["Dest1", "Dest2"]
    assert resolved[0].destination_batch_alias is None

def test_alias_resolver_destination_batch_not_found(mock_db_session):
    # Mock NOT finding a destination batch
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    requests = [RouteRequest(source="Source A", destination_batch_alias="unknown_batch")]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 1
    assert isinstance(resolved[0], dict)
    assert resolved[0]["status"] == "error"
    assert resolved[0]["error_message"] == "Destination batch 'unknown_batch' not found"

def test_alias_resolver_implicit_create(mock_db_session):
    # Mock finding NO saved route, triggering implicit creation
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    requests = [RouteRequest(alias="new_implicit_alias", source="A", destination="B")]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 2
    assert resolved[0]["status"] == "alias_created"
    assert getattr(resolved[1], "source") == "A"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_alias_resolver_implicit_update(mock_db_session):
    saved_route = SavedRoute(
        alias="existing_implicit_alias",
        source="Old A",
        destinations_json='["Old B"]',
        bidirectional=1
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_route
    
    requests = [RouteRequest(alias="existing_implicit_alias", source="New A", destinations=["New B"])]
    resolved = resolve_aliases(requests)
    
    assert len(resolved) == 2
    assert resolved[0]["status"] == "alias_updated"
    assert saved_route.source == "New A"
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()

