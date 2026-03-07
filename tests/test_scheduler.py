import pytest
from datetime import datetime, timedelta
import asyncio
from unittest.mock import patch, MagicMock

from src.jobs.scheduler import JobScheduler
from src.api.schemas import ScheduleConfig, RouteRequest

@pytest.fixture
def scheduler():
    # Provide a clean instance for every test
    sched = JobScheduler()
    sched.MAX_JOBS = 2  # artificially lower for easier testing
    return sched

def test_add_job_success(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    config = ScheduleConfig(schedule_type="interval", interval_minutes=10)

    job_id = scheduler.add_job(routes, config)
    assert job_id.startswith("job-")
    assert len(scheduler._active_jobs) == 1
    
    metadata = scheduler._active_jobs[job_id]
    assert metadata["routes_count"] == 1
    assert metadata["config"]["interval_minutes"] == 10

def test_add_job_exceeds_limit(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    config = ScheduleConfig(schedule_type="interval", interval_minutes=10)

    # Fill capacity (MAX_JOBS = 2 from fixture)
    scheduler.add_job(routes, config)
    scheduler.add_job(routes, config)

    with pytest.raises(ValueError, match="Maximum active jobs limit .* reached."):
        scheduler.add_job(routes, config)

def test_get_jobs_format(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    config = ScheduleConfig(schedule_type="interval", interval_minutes=10)
    scheduler.add_job(routes, config)

    jobs_data = scheduler.get_jobs()
    
    assert jobs_data["active_jobs_count"] == 1
    assert jobs_data["max_jobs_allowed"] == 2
    assert len(jobs_data["jobs"]) == 1
    
    job = jobs_data["jobs"][0]
    assert "job_id" in job
    assert job["schedule_type"] == "interval"
    assert job["routes_count"] == 1

@pytest.mark.asyncio
async def test_scheduler_loop_clears_expired_jobs(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    
    # Create an expired job (end_date was yesterday)
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    config = ScheduleConfig(schedule_type="interval", interval_minutes=10, end_date=yesterday)
    
    job_id = scheduler.add_job(routes, config)
    assert len(scheduler._active_jobs) == 1

    # Spin the loop briefly
    scheduler._keep_running = True
    task = asyncio.create_task(scheduler._run_loop())
    await asyncio.sleep(0.1) # Let loop run
    
    await scheduler.stop()
    
    # The expired job should have been cleared out!
    assert len(scheduler._active_jobs) == 0

from src.jobs.scheduler import parse_time, is_within_peak

def test_parse_time():
    assert parse_time("06:30") == (6, 30)
    assert parse_time("23:59") == (23, 59)

@patch("src.jobs.scheduler.datetime")
def test_is_within_peak(mock_datetime):
    # Mock current time to 12:00 PM
    mock_now = datetime(2023, 1, 1, 12, 0)
    mock_datetime.now.return_value = mock_now

    # 06:00 to 20:00 - 12:00 is exactly in middle
    assert is_within_peak("06:00", "20:00") is True
    
    # 13:00 to 20:00 - 12:00 is before peak
    assert is_within_peak("13:00", "20:00") is False

@patch("src.jobs.scheduler.datetime")
def test_is_within_peak_overnight(mock_datetime):
    # Mock current time to 02:00 AM
    mock_now = datetime(2023, 1, 1, 2, 0)
    mock_datetime.now.return_value = mock_now

    # 20:00 to 06:00 (overnight) - 02:00 AM is inside
    assert is_within_peak("20:00", "06:00") is True

@pytest.mark.asyncio
async def test_scheduler_lifecycle(scheduler):
    # Just testing the start and stop loop mechanics don't crash and set flags
    await scheduler.start()
    assert scheduler._keep_running is True
    assert scheduler._task is not None
    
    await asyncio.sleep(0.1)
    
    await scheduler.stop()
    assert scheduler._keep_running is False

def test_bind_peak_off_peak(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    config = ScheduleConfig(
        schedule_type="peak_off_peak", 
        peak_interval_minutes=5, 
        off_peak_interval_minutes=15
    )
    job_id = scheduler.add_job(routes, config)
    
    assert job_id in scheduler._active_jobs

def test_bind_exact_times(scheduler):
    routes = [RouteRequest(source="A", destination="B")]
    config = ScheduleConfig(
        schedule_type="exact_times", 
        times=["12:00", "15:00"]
    )
    job_id = scheduler.add_job(routes, config)
    
    assert job_id in scheduler._active_jobs
