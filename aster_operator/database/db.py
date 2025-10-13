from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from aster_operator.config.settings import settings
from aster_operator.database.models import Base
from contextlib import contextmanager
from loguru import logger

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized: {settings.db_path}")

@contextmanager
def get_db() -> Session:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

