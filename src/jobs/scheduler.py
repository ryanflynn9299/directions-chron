import asyncio
import schedule
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any

from src.services.route_service import RouteService
from src.api.schemas import ScheduleConfig, RouteRequest

logger = logging.getLogger(__name__)

def parse_time(time_str: str):
    """Parses 'HH:MM' into (hour, minute)."""
    h, m = map(int, time_str.split(':'))
    return h, m

def is_within_peak(peak_start: str, peak_stop: str) -> bool:
    """Checks if the actual system time falls inside the configured peak window."""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    
    start_hour, start_min = parse_time(peak_start)
    end_hour, end_min = parse_time(peak_stop)
    
    start_total = start_hour * 60 + start_min
    end_total = end_hour * 60 + end_min

    # E.g. 06:00 to 20:00 vs overnight like 20:00 to 06:00
    if start_total > end_total:
        return current_minutes >= start_total or current_minutes < end_total
    else:
        return start_total <= current_minutes < end_total

class JobScheduler:
    """
    Scheduler class responsible for orchestrating dynamic, payload-driven application tasks.
    It encapsulates the event loop necessary to push jobs up to a limit of 10.
    """
    MAX_JOBS = 10

    def __init__(self):
        self._active_jobs: Dict[str, dict] = {}
        self._keep_running = False
        self._task = None

    async def start(self):
        """Starts the background scheduling loop asynchronously."""
        self._keep_running = True
        logger.info("Initializing dynamic JobScheduler queue...")
        # Note: Jobs are preserved only in-memory in this implementation.
        # Startup implies 0 jobs loaded. Later caching could reload these from DB.
        
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler loop started.")

    async def stop(self):
        """Stops the scheduler loop safely."""
        self._keep_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped.")

    def add_job(self, routes: list[RouteRequest], config: ScheduleConfig) -> str:
        """Registers a dynamic job into the execution loop if capacity is available."""
        if len(self._active_jobs) >= self.MAX_JOBS:
            raise ValueError(f"Maximum active jobs limit ({self.MAX_JOBS}) reached.")

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        
        # Parse Dates
        end_date_dt = None
        if config.end_date:
            try:
                # Naive ISO slice for comparisons
                end_date_dt = datetime.fromisoformat(config.end_date.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                raise ValueError("Invalid end_date format. Must be an ISO timestamp.")

        metadata = {
            "job_id": job_id,
            "config": config.model_dump() if hasattr(config, "model_dump") else config.dict(),
            "routes_count": len(routes),
            "end_date": end_date_dt,
            "last_executed": 0  # Timestamp epoch tracking for custom thunks
        }
        
        self._active_jobs[job_id] = metadata
        self._bind_schedule(job_id, routes, config)
        return job_id

    def get_jobs(self) -> dict:
        """Reads metadata for the /routes/schedule API return."""
        jobs_list = []
        for metadata in self._active_jobs.values():
            jobs_list.append({
                "job_id": metadata["job_id"],
                "schedule_type": metadata["config"].get("schedule_type"),
                "routes_count": metadata["routes_count"],
                # We can deduce next-run via the 'schedule' library inspection or placeholders
                "next_run": "See internal logs - trackably managed",
            })
            
        return {
            "active_jobs_count": len(jobs_list),
            "max_jobs_allowed": self.MAX_JOBS,
            "jobs": jobs_list
        }

    def _bind_schedule(self, job_id: str, routes: list[RouteRequest], config: ScheduleConfig):
        """Binds the configuration directly into the underlying `schedule` module mapped tightly to the job tag."""
        
        def execute_payload():
            """Closure passing the routes seamlessly to the bulk service method."""
            logger.info(f"Executing scheduled route payload for {job_id}.")
            RouteService.execute_routes_bulk(routes, job_id=job_id)

        t_type = config.schedule_type
        
        if t_type == "interval":
            interval = config.interval_minutes
            schedule.every(interval).minutes.do(execute_payload).tag(job_id)

        elif t_type == "exact_times":
            for t in config.times:
                schedule.every().day.at(t).do(execute_payload).tag(job_id)

        elif t_type == "peak_off_peak":
            # For complex overlapping rules, we schedule a 1-minute ticker thunk exclusively for this job.
            def peak_thunk():
                metadata = self._active_jobs.get(job_id)
                if not metadata: return
                
                cfg = metadata["config"]
                now_epoch = time.time()
                last_run = metadata["last_executed"]
                
                in_peak = is_within_peak(cfg.get('peak_start_time', '06:00'), cfg.get('peak_stop_time', '20:00'))
                target_gap = (cfg.get("peak_interval_minutes") if in_peak else cfg.get("off_peak_interval_minutes")) * 60
                
                # First run or crossed threshold
                if (now_epoch - last_run) >= target_gap:
                    metadata["last_executed"] = now_epoch
                    execute_payload()
            
            schedule.every(1).minutes.do(peak_thunk).tag(job_id)

    async def _run_loop(self):
        """Core asynchronous background loop safely dispatching scheduled requests."""
        while self._keep_running:
            # 1. Check expirations
            now = datetime.utcnow()
            expired_ids = []
            for jid, metadata in self._active_jobs.items():
                if metadata["end_date"] and now >= metadata["end_date"]:
                    expired_ids.append(jid)
            
            for jid in expired_ids:
                logger.info(f"Job {jid} expired naturally based on end_date boundary.")
                schedule.clear(jid)
                del self._active_jobs[jid]

            # 2. Dispatch available cadences
            if schedule.jobs:
                schedule.run_pending()
            
            await asyncio.sleep(1)

# Global singleton
scheduler = JobScheduler()
