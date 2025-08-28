# app/database.py
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

    def __repr__(self):
        return (
            f"<TrafficData(id={self.id}, timestamp='{self.timestamp}', "
            f"duration_seconds={self.duration_seconds})>"
        )


def get_db_engine():
    """Creates and returns a SQLAlchemy database engine."""
    return create_engine(config.DATABASE_URL)


def init_db():
    """Initializes the database and creates tables if they don't exist."""
    engine = get_db_engine()
    Base.metadata.create_all(engine)
    logging.info("Database initialized and tables created.")


def get_db_session():
    """Creates and returns a new database session."""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def add_traffic_entry(duration_seconds: int):
    """Adds a new traffic data entry to the database."""
    session = get_db_session()
    try:
        now = datetime.utcnow()
        new_entry = TrafficData(
            timestamp=now,
            day_of_week=now.strftime('%A'),  # e.g., "Monday"
            duration_seconds=duration_seconds,
            origin=config.START_POINT,
            destination=config.END_POINT
        )
        session.add(new_entry)
        session.commit()
        logging.info(f"Successfully added new traffic entry: {duration_seconds} seconds.")
    except Exception as e:
        logging.error(f"Failed to add database entry: {e}")
        session.rollback()
    finally:
        session.close()
