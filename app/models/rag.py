import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.models.base import Base # 引用 Auth 系統原本的 Base

# 對話歷史 (整合原本的 ConversationHistory)
class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True) # 對應 User.user_id
    session_id = Column(String, index=True, nullable=False)
    course_id = Column(String, index=True, nullable=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    follow_up_question = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# QA 快取 (注意：Voyage 3 的向量是 1024 維)
class QACache(Base):
    __tablename__ = "qa_cache"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, index=True, nullable=False)
    question = Column(Text, nullable=False)
    question_vector = Column(Vector(1024), nullable=False)
    answer = Column(Text, nullable=False)
    follow_up_question = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 課程回饋
class CourseFeedback(Base):
    __tablename__ = "course_feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    course_id = Column(String, index=True, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 來源文件紀錄 (用於比對檔案是否更新)
class SourceDocument(Base):
    __tablename__ = "source_documents"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    last_modified = Column(DateTime, nullable=False)
    content_hash = Column(String, nullable=False, index=True)

# 問答紀錄表 (專門用於教師分析與關鍵字統計)
class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    course_id = Column(String, index=True, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(String, nullable=True)
    is_useful = Column(Boolean, default=None, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())