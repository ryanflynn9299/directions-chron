from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

# Define the base class for declarative models
Base = declarative_base()

class TrafficData(Base):
    """SQLAlchemy model for storing traffic data entries."""
    __tablename__ = 'traffic_data'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    day_of_week = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    
    route_group_id = Column(String, index=True, nullable=False)
    job_id = Column(String, index=True, nullable=True)
    alias = Column(String, index=True, nullable=True)

    def __repr__(self):
        return (
            f"<TrafficData(id={self.id}, timestamp='{self.timestamp}', "
            f"duration_seconds={self.duration_seconds})>"
        )
