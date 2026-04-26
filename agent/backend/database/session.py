from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from backend.config import DATABASE_URL

# Configure SQLite for better concurrency
if DATABASE_URL.startswith("sqlite"):
    # Add WAL mode and shared cache parameters
    sqlite_url = DATABASE_URL
    if "?" not in sqlite_url:
        sqlite_url += "?cache=shared"
    else:
        sqlite_url += "&cache=shared"

    engine = create_engine(
        sqlite_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # Increase timeout for busy database
        },
        echo=False,
        poolclass=None,  # Use default pool for SQLite
        pool_pre_ping=True  # Check connection before using
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,  # Connection pool for other databases
        max_overflow=10,
        pool_pre_ping=True
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize database tables"""
    # For SQLite, enable WAL mode for better concurrency
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            # Enable WAL mode
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            # Increase busy timeout
            conn.execute(text("PRAGMA busy_timeout=30000;"))
            # Enable foreign keys
            conn.execute(text("PRAGMA foreign_keys=ON;"))
            conn.commit()
            print("SQLite WAL mode enabled")

    Base.metadata.create_all(bind=engine)
    print(f"Database tables created: {list(Base.metadata.tables.keys())}")

def get_db():
    """Dependency for FastAPI routes to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()