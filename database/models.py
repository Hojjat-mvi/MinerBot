import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import relationship
from .base import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer,primary_key= True)
    name = Column(String)
    phoneNumber = Column(String)

class FAQ(Base):
    __tablename__ = 'faq'

    id = Column(Integer,primary_key=True)
    title = Column(String)
    description = Column(String)