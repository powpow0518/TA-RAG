from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.models.base import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, unique=True, index=True, nullable=False)
    course_name = Column(String, nullable=False)
    semester = Column(String, nullable=True)
    course_code = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    teacher_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
