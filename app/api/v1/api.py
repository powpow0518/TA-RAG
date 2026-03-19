from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, courses, questions, student_questions, quiz, rag

api_router = APIRouter()

# register router
api_router.include_router(auth, prefix="/auth", tags=["authentication"])
api_router.include_router(users, prefix="/users", tags=["users"])
api_router.include_router(courses, prefix="/courses", tags=["courses"])
api_router.include_router(questions, prefix="/questions", tags=["questions"])
api_router.include_router(student_questions, prefix="/student/questions", tags=["student-questions"])
api_router.include_router(quiz, prefix="/quiz", tags=["quiz"])
api_router.include_router(rag, prefix="/rag", tags=["RAG"])
