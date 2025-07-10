from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False)

# SQLite setup
DATABASE_URL = "sqlite:///files.db"
engine = create_engine(DATABASE_URL, echo=False)

# Call this function to get a session
SessionLocal = sessionmaker(bind=engine)


# Create tables
Base.metadata.create_all(bind=engine)
