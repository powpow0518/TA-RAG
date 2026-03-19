from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.base import get_db
from app.services.quiz_service import quiz_service
from app.api.dependencies import get_current_teacher, get_current_student
from app.models.user import User
from app.repositories.quiz_repository import quiz_repository

from app.schemas.quiz import (
    DocListResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizCreateRequest,
    QuizCreateResponse,
    QuizAccessResponse,
    StudentQuestionItem,
    QuizSubmitRequest,
    QuizSubmitResponse
)

router = APIRouter()

# =========================================================
# 1. 調用 RAG 文件列表 (讓老師選)
# =========================================================
@router.get("/documents", response_model=DocListResponse)
def get_documents(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    """
    獲取該課程已上傳的「所有」文件清單 (不重複的檔名)。
    """
    try:
        return {"files": quiz_repository.list_source_document_names(db, course_id)}

    except Exception as e:
        print(f"❌ 撈取文件列表失敗: {e}")
        return {"files": []}


# =========================================================
# 2. 生成題目 (AI Draft) - 委託給 QuizService
# =========================================================
@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz_draft(
    req: QuizGenerateRequest,
    current_user: User = Depends(get_current_teacher)
):
    """
    1. 呼叫 Service 進行指定檔案搜尋。
    2. 呼叫 Service 讓 GPT 生成 5 題問答題 JSON。
    """
    try:
        # 防呆
        if not req.selected_files:
            raise HTTPException(status_code=400, detail="請至少選擇一個檔案")

        # 🔥 全部交給 Service 處理，這裡變得很乾淨
        result_json = quiz_service.generate_quiz_draft(
            topic=req.topic,
            course_id=req.course_id,
            selected_files=req.selected_files,
            difficulty=req.difficulty
        )

        # result_json 格式已經是 {"questions": [...]}，Pydantic 會自動驗證轉換
        return result_json

    except Exception as e:
        print(f"❌ 生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"生成題目失敗: {str(e)}")


# =========================================================
# 3. 儲存題目 (Finalize) - 委託給 QuizService
# =========================================================
@router.post("/create", response_model=QuizCreateResponse)
def create_quiz(
    req: QuizCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    """
    老師修改完後，將最終版本 (含標題、5題問答題) 存入 DB。
    """
    try:
        # 🔥 呼叫 Service 存檔 (包含生成 Access Code 的邏輯都在裡面了)
        new_quiz = quiz_service.create_quiz(db, req)

        return QuizCreateResponse(
            quiz_id=new_quiz.quiz_id,
            access_code=new_quiz.access_code
        )

    except Exception as e:
        print(f"❌ 建立測驗失敗: {e}")
        raise HTTPException(status_code=500, detail=f"建立測驗失敗: {str(e)}")


# 4. 學生通過代碼進入測驗

@router.get("/code/{access_code}", response_model=QuizAccessResponse)
def access_quiz_by_code(
    access_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    """
    Student input six quiz code

    ### 參數
    - **access_code**: six quiz code

    ### 返回
    - 測驗標題,course ID,題目

    ### 錯誤
    - 404: quiz code not exist
    """
    try:
        # 查詢測驗
        quiz = quiz_repository.get_by_access_code(db, access_code)

        if not quiz:
            raise HTTPException(
                status_code=404,
                detail=f"測驗代碼'{access_code}'不存在或已過期"
            )

        # 過濾評分標準
        student_questions = [
            StudentQuestionItem(question=q["question"])
            for q in quiz.questions_content
        ]

        return QuizAccessResponse(
            quiz_id=quiz.quiz_id,
            course_id=quiz.course_id,
            title=quiz.title,
            questions=student_questions,
            created_at=quiz.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"獲取測驗失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取測驗失敗: {str(e)}")


# 5. 批改學生答案
@router.post("/submit", response_model=QuizSubmitResponse)
def submit_quiz_answers(
    req: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_student)
):
    """
    student submit answer and GPT check answer

    ### parameter
    - **access_code**: quiz code
    - **answers**: student quiz ans

    ### respone
    - anser list

    ### error code
    - 404: quiz code error
    - 400: ans num not equal
    """
    try:
        result = quiz_service.grade_quiz(
            access_code=req.access_code,
            student_id=req.student_id,
            student_answers=req.answers,
            db=db
        )

        return QuizSubmitResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"批改失敗: {e}")
        raise HTTPException(status_code=500, detail=f"批改失敗: {str(e)}")
