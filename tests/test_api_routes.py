import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.api.schemas import RouteRequest, ScheduleConfig

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch("src.services.route_service.RouteService.execute_routes_bulk")
def test_execute_query_endpoint(mock_execute_bulk):
    mock_execute_bulk.return_value = [{"source": "A", "destination": "B", "status": "success", "duration_seconds": 500}]

    payload = {
        "routes": [
            {"source": "A", "destination": "B", "bidirectional": False}
        ]
    }

    response = client.post("/routes/query", json=payload)
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert len(json_data["results"]) == 1
    assert json_data["results"][0]["duration_seconds"] == 500
    
    mock_execute_bulk.assert_called_once()

@patch("src.jobs.scheduler.JobScheduler.add_job")
def test_create_schedule_endpoint_success(mock_add_job):
    mock_add_job.return_value = "job-123"

    payload = {
        "routes": [
            {"source": "A", "destination": "B"}
        ],
        "schedule": {
            "schedule_type": "interval",
            "interval_minutes": 5
        }
    }

    response = client.post("/routes/schedule", json=payload)
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["job_id"] == "job-123"
    
    mock_add_job.assert_called_once()


@patch("src.jobs.scheduler.JobScheduler.add_job")
def test_create_schedule_endpoint_failure(mock_add_job):
    # Simulate a raised ValueError from inside add_job limit breach
    mock_add_job.side_effect = ValueError("Maximum active jobs limit (10) reached.")

    payload = {
        "routes": [
            {"source": "A", "destination": "B"}
        ],
        "schedule": {
            "schedule_type": "interval",
            "interval_minutes": 5
        }
    }

    response = client.post("/routes/schedule", json=payload)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Maximum active jobs limit (10) reached."


@patch("src.jobs.scheduler.JobScheduler.get_jobs")
def test_list_schedules_endpoint(mock_get_jobs):
    mock_get_jobs.return_value = {
        "active_jobs_count": 1,
        "max_jobs_allowed": 10,
        "jobs": [{"job_id": "job-123"}]
    }

    response = client.get("/routes/schedule")
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["active_jobs_count"] == 1
    assert json_data["jobs"][0]["job_id"] == "job-123"
