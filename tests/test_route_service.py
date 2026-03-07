import pytest
from unittest.mock import patch, MagicMock

from src.services.route_service import RouteService
from src.api.schemas import RouteRequest

@pytest.fixture
def mock_db_session():
    with patch('src.services.route_service.get_db_session') as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        yield mock_session

@pytest.fixture
def mock_maps_api():
    with patch('src.services.route_service.get_route_duration_seconds') as mock_api:
        yield mock_api

def test_execute_single_route_forward_only(mock_db_session, mock_maps_api):
    # Setup mock behavior
    mock_maps_api.return_value = 600

    results = RouteService.execute_single_route("Origin A", "Dest B", bidirectional=False)

    assert len(results) == 1
    assert results[0]["source"] == "Origin A"
    assert results[0]["destination"] == "Dest B"
    assert results[0]["status"] == "success"
    assert results[0]["duration_seconds"] == 600
    
    # DB persistence check
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.close.assert_called_once()
    
    # API check
    mock_maps_api.assert_called_once_with(api_key=None, origin="Origin A", destination="Dest B")


def test_execute_single_route_bidirectional(mock_db_session, mock_maps_api):
    # Setup mock behavior to return different values for different directions
    def mock_api_side_effect(api_key, origin, destination):
        if origin == "Origin A":
            return 600
        return 750

    mock_maps_api.side_effect = mock_api_side_effect

    results = RouteService.execute_single_route("Origin A", "Dest B", bidirectional=True)

    assert len(results) == 2
    
    # Check forward
    assert results[0]["source"] == "Origin A"
    assert results[0]["destination"] == "Dest B"
    assert results[0]["duration_seconds"] == 600

    # Check reverse
    assert results[1]["source"] == "Dest B"
    assert results[1]["destination"] == "Origin A"
    assert results[1]["duration_seconds"] == 750
    
    assert mock_db_session.add.call_count == 2
    assert mock_maps_api.call_count == 2


def test_execute_single_route_api_failure(mock_db_session, mock_maps_api):
    mock_maps_api.return_value = None

    results = RouteService.execute_single_route("Origin A", "Dest B", bidirectional=False)

    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "error_message" in results[0]
    
    # If API fails, DB should not be written to
    mock_db_session.add.assert_not_called()


def test_execute_routes_bulk(mock_db_session, mock_maps_api):
    mock_maps_api.return_value = 300
    
    # Create two requests to pass in bulk
    req1 = RouteRequest(source="Source 1", destination="Single Dest", bidirectional=False)
    req2 = RouteRequest(source="Source 2", destinations=["Multi Dest 1", "Multi Dest 2"], bidirectional=True)
    
    results = RouteService.execute_routes_bulk([req1, req2])
    
    # req1 creates 1 result
    # req2 creates 2 destinations * 2 directions = 4 results
    # Total = 5
    assert len(results) == 5
    
    sources = [r["source"] for r in results]
    assert "Source 1" in sources
    assert "Source 2" in sources
    # Direction flipped source
    assert "Multi Dest 1" in sources
    assert "Multi Dest 2" in sources
