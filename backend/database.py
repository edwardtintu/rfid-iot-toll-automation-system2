from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///backend/storage/toll_data.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

class TollRecord(Base):
    __tablename__ = "toll_records"
    id = Column(Integer, primary_key=True, index=True)
    tagUID = Column(String, index=True)
    vehicle_type = Column(String)
    amount = Column(Float)
    speed = Column(Float)
    decision = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tx_hash = Column(String)

Base.metadata.create_all(engine)
