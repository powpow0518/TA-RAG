from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# --- 基礎題目結構 ---
class QuestionItem(BaseModel):
    question: str              # 題目
    grading_criteria: Optional[str] = None # 評分標準/關鍵字 (例如：提到XX得2分)

# --- Endpoint 1: 取得文件列表 Response ---
class DocListResponse(BaseModel):
    files: List[str]

# --- Endpoint 2: 生成 Request ---
class QuizGenerateRequest(BaseModel):
    course_id: str
    selected_files: List[str]
    topic: str
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"

# --- Endpoint 2: 生成 Response ---
class QuizGenerateResponse(BaseModel):
    # 回傳 5 題問答題的列表
    questions: List[QuestionItem]

# --- Endpoint 3: 儲存題目 Request & Response ---
class QuizCreateRequest(BaseModel):
    course_id: str
    title: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d 測驗")
    )

    source_files: List[str]
    questions: List[QuestionItem]

class QuizCreateResponse(BaseModel):
    quiz_id: str
    access_code: str          # 回傳代碼給老師顯示

# --- Endpoint 4: quiz code Input ---

class StudentQuestionItem(BaseModel):
    question: str

class QuizAccessResponse(BaseModel):
    quiz_id: str
    course_id: str
    title: str
    questions: List[StudentQuestionItem]
    created_at: datetime

# --- Endpoint 5: submit student answer ---
class QuizSubmitRequest(BaseModel):
    access_code: str
    student_id: str     # 學號
    answers: List[str]  # student answer list

class QuestionGradeResult(BaseModel):
    question: str
    student_answer: str
    result: str  # "pass" 或 "not pass"

class QuizSubmitResponse(BaseModel):
    quiz_id: str
    title: str
    results: List[QuestionGradeResult]