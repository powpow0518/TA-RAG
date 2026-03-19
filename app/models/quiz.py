from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base
import uuid

class Quiz(Base):
    __tablename__ = "quizzes"

    # 使用 String 儲存 UUID，方便與前端 JSON 互動
    quiz_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    course_id = Column(String, index=True, nullable=False)
    teacher_id = Column(String, nullable=True)

    # 標題 (例如 "2024-05-20 測驗")
    title = Column(String, nullable=False)

    # 來源檔案列表 (存成 JSON Array: ["file1.pdf", "file2.pdf"])
    source_files = Column(JSON, default=list)

    # 🔥 核心內容：存入整份考卷的題目結構
    # 格式包含: [{id, question, reference_answer, grading_criteria}, ...]
    questions_content = Column(JSON, nullable=False)

    # 學生進入用的 6 碼代碼
    access_code = Column(String, unique=True, index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

# quiz submit model
class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"

    submission_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String, ForeignKey("quizzes.quiz_id"), nullable=False, index=True)
    student_id = Column(String, nullable=False, index=True)  # 學號

    # 學生原始答案列表 (JSON Array: ["答案1", "答案2", ...])
    student_answers = Column(JSON, nullable=False)

    # 每題批改結果
    results = Column(JSON, nullable=False)

    passed_count = Column(Integer, nullable=False) # 通過題數
    total_count = Column(Integer, nullable=False) # 總題數

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())