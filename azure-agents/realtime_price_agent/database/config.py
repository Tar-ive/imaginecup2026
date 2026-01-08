"""
Database configuration for Postgres connection (Neon or other).
Loads connection details from environment variables.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables
load_dotenv()

# Database connection configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate required environment variables
if not DATABASE_URL:
    raise ValueError(
        "Missing required environment variable.\n"
        "Please ensure .env contains:\n"
        "  DATABASE_URL=postgresql://user:pass@host/dbname"
    )

# Ensure DATABASE_URL is not None for type safety
assert DATABASE_URL is not None


def get_db_engine():
    """Create SQLAlchemy engine for Postgres"""

    # Ensure we have a valid URL
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is required")

    # Create SQLAlchemy engine
    engine = create_engine(
        str(DATABASE_URL),
        echo=False,  # Set to True for SQL debugging
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    return engine


# Create SQLAlchemy engine
engine = get_db_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Database session generator for FastAPI dependency injection.
    Usage:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 AS test"))
            print(f"✅ Database connection successful!")
            if DATABASE_URL:
                print(
                    f"   URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'connected'}"
                )
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
