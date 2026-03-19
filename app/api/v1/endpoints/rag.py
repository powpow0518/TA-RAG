import json
import traceback
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.schemas.rag import QueryRequest, FeedbackRequest, HistoryResponse, HistoryMessage

# 引入同事的依賴與設定
from app.api.dependencies import get_current_active_user as get_current_user
from app.models.rag import ConversationHistory, CourseFeedback
from app.models.base import get_db
from app.models.user import User
from app.core.config import settings
from app.repositories.rag_repository import rag_repository

# 引入我們的 RAG 模組
from app.services import rag_service

router = APIRouter()

@router.post("/ask")
async def ask_question(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 問答接口
    邏輯移交給 rag_service.ask_stream 處理：
    1. 先搜尋 RAG
    2. 若無資料，才判斷意圖
    3. 若有關則 GPT 回答，無關則拒絕
    """

    return StreamingResponse(
        rag_service.rag_service.ask_stream( # 呼叫 service 裡的實例方法
            query=request.query,
            course_id=request.course_id,
            session_id=request.session_id,
            db_session=db,
            user=current_user,
            background_tasks=background_tasks
        ),
        media_type="text/event-stream"
    )


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rag_repository.add_feedback(
        db,
        user_id=current_user.user_id,
        course_id=request.course_id,
        rating=request.rating,
        comment=request.comment
    )
    return {"message": "Feedback submitted"}

@router.get("/history/{session_id}", response_model=HistoryResponse, tags=["RAG"])
def get_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """從資料庫讀取指定 Session 的對話紀錄"""
    logs = rag_repository.get_history(db, session_id)

    # 這裡使用的 HistoryMessage 和 HistoryResponse 已經變成從 schema 引入的了
    messages = [
        HistoryMessage(
            role=log.role,
            content=log.content,
            created_at=str(log.created_at)
        ) for log in logs
    ]

    return HistoryResponse(session_id=session_id, messages=messages)
