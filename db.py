import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import base # Import the declarative base from models.py

# Database configuration
# Define the path to the SQLite database file
db_path = os.path.join(os.path.dirname(__file__), 'app.db')

# Create a SQLAlchemy engine. echo=True logs all SQL statements.
# The f-string ensures the path is correctly formatted for SQLite.
engine = create_engine(f'sqlite:///{db_path}', echo=True)

# Create a sessionmaker to produce new Session objects.
# bind the session to the engine.
Session = sessionmaker(bind=engine)

# Create a scoped_session. This ensures that each request gets its own session,
# and that the session is thread-safe.
db_session = scoped_session(Session)

def init_db():
    """
    Initializes the database by creating all defined tables.
    This function should be called once when the application starts.
    """
    # base.metadata.create_all(engine) creates all tables that inherit from 'base'
    # and are linked to this engine.
    base.metadata.create_all(engine)
    print("Database initialized and tables created.")

def shutdown_session(exception=None):
    """
    Removes the current database session.
    This function is typically registered as a teardown handler for Flask requests.
    """
    db_session.remove()
    print("Database session removed.")

# You can optionally add a simple check to create the database file if it doesn't exist
# This is more for development convenience
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}. It will be created on init_db().")

