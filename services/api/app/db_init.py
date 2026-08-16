import sys
from pathlib import Path
from sqlalchemy import text
from app.db import engine, Base
import app.models  # noqa: F401 - ensure all models are registered with Base.metadata


def init_database() -> None:
    print(f"Initializing database schema on {engine.url.render_as_string(hide_password=True)}...")
    
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            try:
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                print("✓ PostgreSQL 'uuid-ossp' extension verified.")
            except Exception as e:
                print(f"Notice: could not create uuid-ossp extension: {e}")

    # Create tables defined in SQLAlchemy models
    Base.metadata.create_all(bind=engine)
    print("✓ All database tables created/verified successfully.")


if __name__ == "__main__":
    try:
        init_database()
        print("Database initialization complete.")
    except Exception as exc:
        print(f"Error initializing database: {exc}", file=sys.stderr)
        sys.exit(1)
