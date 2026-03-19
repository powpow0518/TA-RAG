from sqlalchemy.orm import Session

from app.models.question import Question


class QuestionRepository:
    def list_by_course_id(self, db: Session, course_id: str) -> list[Question]:
        return db.query(Question).filter(Question.course_id == course_id).all()

    def list_all(self, db: Session) -> list[Question]:
        return db.query(Question).all()


question_repository = QuestionRepository()
