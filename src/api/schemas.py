from pydantic import BaseModel, Field, root_validator, validator
from typing import Optional, List, Dict, Any

class RouteRequest(BaseModel):
    alias: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    destinations: Optional[List[str]] = Field(default=None, max_items=100)
    bidirectional: bool = True

    @root_validator(pre=True)
    def check_mutually_exclusive_destinations(cls, values):
        alias = values.get('alias')
        has_source = bool(values.get('source'))
        has_dest = bool(values.get('destination'))
        has_dests = bool(values.get('destinations'))

        if alias and not has_source and not has_dest and not has_dests:
            # It's an alias-only resolution request
            return values

        if not has_source:
             raise ValueError("'source' is required unless submitting an alias-only resolution request.")
             
        if has_dest and has_dests:
            raise ValueError("Fields 'destination' and 'destinations' are mutually exclusive.")
        if not has_dest and not has_dests:
            raise ValueError("Either 'destination' or 'destinations' must be provided.")
            
        return values

class SavedRouteResponse(BaseModel):
    alias: str
    source: str
    destinations: List[str]
    bidirectional: bool

class QueryPayload(BaseModel):
    routes: List[RouteRequest]

class ScheduleConfig(BaseModel):
    schedule_type: str = Field(..., description="Must be 'interval', 'exact_times', or 'peak_off_peak'")
    
    # Optional fields depending on the type
    interval_minutes: Optional[int] = None
    times: Optional[List[str]] = None
    peak_interval_minutes: Optional[int] = None
    off_peak_interval_minutes: Optional[int] = None
    peak_start_time: Optional[str] = "06:00"
    peak_stop_time: Optional[str] = "20:00"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @validator('schedule_type')
    def validate_schedule_type(cls, v):
        allowed = {'interval', 'exact_times', 'peak_off_peak'}
        if v not in allowed:
            raise ValueError(f"schedule_type must be one of {allowed}")
        return v

    @root_validator(pre=True)
    def validate_type_fields(cls, values):
        st = values.get('schedule_type')
        if st == 'interval':
            if values.get('interval_minutes') is None:
                raise ValueError("interval_minutes is required for 'interval' schedule_type")
        elif st == 'exact_times':
            if not values.get('times'):
                raise ValueError("times array is required for 'exact_times' schedule_type")
        elif st == 'peak_off_peak':
            if values.get('peak_interval_minutes') is None or values.get('off_peak_interval_minutes') is None:
                raise ValueError("peak_interval_minutes and off_peak_interval_minutes require for 'peak_off_peak' schedule_type")
        return values

class SchedulePayload(BaseModel):
    routes: List[RouteRequest]
    schedule: ScheduleConfig
