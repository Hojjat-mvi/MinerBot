import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")  # Use your database URL here

# Create a SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Export the Base class for use in other models
Base.metadata.create_all(bind=engine)