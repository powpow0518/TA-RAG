from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.models.user import User
from app.api.dependencies import get_current_teacher, get_current_active_user
from app.repositories.course_repository import course_repository

router = APIRouter()

@router.get("/")
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return course_repository.list_all(db)

@router.post("/")
def create_course(
    course_id: str, 
    course_name: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_teacher)
):
    return course_repository.create(
        db,
        course_id=course_id,
        course_name=course_name,
        teacher_id=current_user.user_id,
    )
