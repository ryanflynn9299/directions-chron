import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.db.models import DestinationBatch

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    with patch("src.api.destinations.get_db_session") as m_db:
        session_mock = MagicMock()
        m_db.return_value.__enter__.return_value = session_mock
        yield session_mock

def test_create_destination_batch_new(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    payload = {
        "alias": "my_batch",
        "destinations": ["Work", "Gym"]
    }
    
    response = client.post("/destinations/batch", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["alias"] == "my_batch"
    assert data["destinations"] == ["Work", "Gym"]
    
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_create_destination_batch_update(mock_db_session):
    existing = DestinationBatch(alias="my_batch", destinations_json='["OldDest"]')
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing
    
    payload = {
        "alias": "my_batch",
        "destinations": ["NewDest"]
    }
    
    response = client.post("/destinations/batch", json=payload)
    
    assert response.status_code == 200
    assert existing.destinations_json == '["NewDest"]'
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()
    
def test_create_destination_batch_error(mock_db_session):
    mock_db_session.commit.side_effect = Exception("DB Error")
    
    payload = {
        "alias": "my_batch",
        "destinations": ["Work"]
    }
    
    response = client.post("/destinations/batch", json=payload)
    
    assert response.status_code == 500
    assert "Failed to save" in response.json()["detail"]
    mock_db_session.rollback.assert_called_once()

def test_get_batch_success(mock_db_session):
    batch = DestinationBatch(alias="my_batch", destinations_json='["Work", "Home"]')
    mock_db_session.query.return_value.filter.return_value.first.return_value = batch
    
    response = client.get("/destinations/batch/my_batch")
    
    assert response.status_code == 200
    data = response.json()
    assert data["alias"] == "my_batch"
    assert data["destinations"] == ["Work", "Home"]

def test_get_batch_not_found(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/destinations/batch/unknown")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_list_batches(mock_db_session):
    batch1 = DestinationBatch(alias="batch1", destinations_json='["A"]')
    batch2 = DestinationBatch(alias="batch2", destinations_json='["B"]')
    mock_db_session.query.return_value.all.return_value = [batch1, batch2]
    
    response = client.get("/destinations/batch")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["alias"] == "batch1"
    assert data[1]["alias"] == "batch2"

def test_delete_batch_success(mock_db_session):
    batch = DestinationBatch(alias="my_batch", destinations_json='["Work"]')
    mock_db_session.query.return_value.filter.return_value.first.return_value = batch
    
    response = client.delete("/destinations/batch/my_batch")
    
    assert response.status_code == 200
    mock_db_session.delete.assert_called_once_with(batch)
    mock_db_session.commit.assert_called_once()

def test_delete_batch_not_found(mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    response = client.delete("/destinations/batch/unknown")
    
    assert response.status_code == 404
    mock_db_session.delete.assert_not_called()

def test_delete_batch_error(mock_db_session):
    batch = DestinationBatch(alias="my_batch", destinations_json='["Work"]')
    mock_db_session.query.return_value.filter.return_value.first.return_value = batch
    mock_db_session.commit.side_effect = Exception("DB Error")
    
    response = client.delete("/destinations/batch/my_batch")
    
    assert response.status_code == 500
    assert "Failed to delete" in response.json()["detail"]
    mock_db_session.rollback.assert_called_once()
