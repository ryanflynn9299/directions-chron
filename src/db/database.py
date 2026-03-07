import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base
from src.config.config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    """Encapsulates the database engine and session management."""
    def __init__(self, db_url: str = DATABASE_URL):
        try:
            self.engine = create_engine(db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self._init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database engine. App will start but database features will fail. Error: {e}")
            self.engine = None
            self.SessionLocal = None

    def _init_db(self):
        """Initializes the database and creates tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized and tables created.")
        except Exception as e:
            logger.error(f"Failed to connect to database during startup. App will start but database features may fail. Error: {e}")

    def get_session(self):
        """Returns a new SQLAlchemy session. Callers must close this when done (or use context dict)."""
        if self.SessionLocal is None:
            raise RuntimeError("Database connection was not established successfully during startup.")
        return self.SessionLocal()

# Global database instance
db = Database()

def get_db_session():
    """Dependency / helper for acquiring a session directly."""
    return db.get_session()
