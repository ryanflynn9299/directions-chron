import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException

from src.services.maps_client import get_route_duration_seconds

@patch("src.services.maps_client.MOCK_API_CALLS", False)
@patch("src.services.maps_client.requests.post")
def test_get_route_duration_success(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "routes": [
            {"duration": "1450s"}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    duration = get_route_duration_seconds("fake_key", "Origin A", "Dest B")

    assert duration == 1450
    mock_post.assert_called_once()

@patch("src.services.maps_client.MOCK_API_CALLS", False)
@patch("src.services.maps_client.requests.post")
def test_get_route_duration_no_routes_found(mock_post):
    mock_response = MagicMock()
    # Mocking what happens when Google returns a 200 OK but no routes match
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    duration = get_route_duration_seconds("fake_key", "Origin A", "Dest B")

    assert duration is None

@patch("src.services.maps_client.MOCK_API_CALLS", False)
@patch("src.services.maps_client.requests.post")
def test_get_route_duration_request_exception(mock_post):
    # Mock a network failure or 401 Unauthorized
    mock_post.side_effect = RequestException("Network Error")

    duration = get_route_duration_seconds("fake_key", "Origin A", "Dest B")

    assert duration is None

@patch("src.services.maps_client.MOCK_API_CALLS", False)
@patch("src.services.maps_client.requests.post")
def test_get_route_duration_parse_error(mock_post):
    mock_response = MagicMock()
    # Mess up the JSON structure to cause a TypeError or KeyError
    mock_response.json.return_value = {"routes": [{"wrong_key": "data"}]}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    duration = get_route_duration_seconds("fake_key", "Origin A", "Dest B")
    
    # It attempts to get('duration', '0s'), stripping 's' returns 0 instead of crashing
    assert duration == 0

@patch("src.services.maps_client.MOCK_API_CALLS", True)
@patch("src.services.maps_client.requests.post")
def test_get_route_duration_mocked(mock_post):
    # This should not call post at all
    duration = get_route_duration_seconds("fake_key", "Origin A", "Dest B")

    assert 1200 <= duration <= 3600
    mock_post.assert_not_called()
