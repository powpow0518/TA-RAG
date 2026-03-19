from sqlalchemy.orm import Session

from app.models.quiz import Quiz, QuizSubmission
from app.models.rag import SourceDocument


class QuizRepository:
    def list_source_document_names(self, db: Session, course_id: str) -> list[str]:
        results = (
            db.query(SourceDocument.file_name)
            .filter(SourceDocument.course_id == course_id)
            .distinct()
            .order_by(SourceDocument.file_name)
            .all()
        )
        return [row[0] for row in results]

    def access_code_exists(self, db: Session, access_code: str) -> bool:
        return db.query(Quiz).filter(Quiz.access_code == access_code).first() is not None

    def create_quiz(
        self,
        db: Session,
        *,
        course_id: str,
        title: str,
        source_files: list[str],
        questions_content: list[dict],
        access_code: str,
    ) -> Quiz:
        quiz = Quiz(
            course_id=course_id,
            title=title,
            source_files=source_files,
            questions_content=questions_content,
            access_code=access_code,
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        return quiz

    def get_by_access_code(self, db: Session, access_code: str) -> Quiz | None:
        return db.query(Quiz).filter(Quiz.access_code == access_code.upper()).first()

    def get_submission(self, db: Session, quiz_id: str, student_id: str) -> QuizSubmission | None:
        return (
            db.query(QuizSubmission)
            .filter(QuizSubmission.quiz_id == quiz_id, QuizSubmission.student_id == student_id)
            .first()
        )

    def create_submission(
        self,
        db: Session,
        *,
        quiz_id: str,
        student_id: str,
        student_answers: list[str],
        results: list[dict],
        passed_count: int,
        total_count: int,
    ) -> QuizSubmission:
        submission = QuizSubmission(
            quiz_id=quiz_id,
            student_id=student_id,
            student_answers=student_answers,
            results=results,
            passed_count=passed_count,
            total_count=total_count,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission


quiz_repository = QuizRepository()
