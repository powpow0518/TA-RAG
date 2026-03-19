from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Feedback ---
class FeedbackRequest(BaseModel):
    course_id: str
    rating: int
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    message: str

# --- History ---
class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None # 轉成字串回傳比較單純

class HistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]

    model_config = ConfigDict(from_attributes=True)

# --- RAG Query (原本寫在 endpoint 裡的) ---
class QueryRequest(BaseModel):
    query: str
    course_id: str
    session_id: str
    force_regenerate: bool = False