from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.models.base import get_db
from app.repositories.question_repository import question_repository

router = APIRouter()


@router.get("/")
def get_student_questions(db: Session = Depends(get_db), current_user=Depends(get_current_active_user)):
    return question_repository.list_all(db)
