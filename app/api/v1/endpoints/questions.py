from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.api.dependencies import get_current_teacher
from app.repositories.question_repository import question_repository

router = APIRouter()

@router.get("/{course_id}")
def get_questions(course_id: str, db: Session = Depends(get_db)):
    return question_repository.list_by_course_id(db, course_id)
