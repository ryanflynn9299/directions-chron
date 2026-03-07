import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base
from src.config.config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    """Encapsulates the database engine and session management."""
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_db()

    def _init_db(self):
        """Initializes the database and creates tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized and tables created.")

    def get_session(self):
        """Returns a new SQLAlchemy session. Callers must close this when done (or use context dict)."""
        return self.SessionLocal()

# Global database instance
db = Database()

def get_db_session():
    """Dependency / helper for acquiring a session directly."""
    return db.get_session()
