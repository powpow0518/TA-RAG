from contextlib import contextmanager

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.models.course import Course
from app.models.rag import ConversationHistory, CourseFeedback, QACache, QARecord


class RAGRepository:
    @contextmanager
    def session_scope(self):
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_course(self, db: Session, course_id: str) -> Course | None:
        return db.query(Course).filter(Course.course_id == course_id).first()

    def get_recent_history(self, db: Session, session_id: str, limit: int = 2) -> list[ConversationHistory]:
        return (
            db.query(ConversationHistory)
            .filter(ConversationHistory.session_id == session_id)
            .order_by(desc(ConversationHistory.created_at))
            .limit(limit)
            .all()
        )

    def get_history(self, db: Session, session_id: str) -> list[ConversationHistory]:
        return (
            db.query(ConversationHistory)
            .filter(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at.asc())
            .all()
        )

    def get_exact_cache(self, db: Session, course_id: str, question: str) -> QACache | None:
        return (
            db.query(QACache)
            .filter(QACache.course_id == course_id, QACache.question == question)
            .first()
        )

    def get_semantic_cache_hit(self, db: Session, course_id: str, query_vector) -> tuple[QACache | None, float | None]:
        distance_expr = QACache.question_vector.l2_distance(query_vector)
        hit = (
            db.query(QACache, distance_expr)
            .filter(QACache.course_id == course_id)
            .order_by(distance_expr)
            .first()
        )
        if not hit:
            return None, None
        cache_obj, distance = hit
        return cache_obj, float(distance)

    def save_conversation_bundle(
        self,
        db: Session,
        *,
        session_id: str,
        course_id: str,
        user_id: str,
        query: str,
        answer: str,
        keywords: str,
        follow_up_question: str | None,
        refined_query: str | None,
        cache_vector,
    ) -> None:
        db.add(
            ConversationHistory(
                session_id=session_id,
                course_id=course_id,
                user_id=user_id,
                role="user",
                content=query,
            )
        )
        db.add(
            ConversationHistory(
                session_id=session_id,
                course_id=course_id,
                user_id=user_id,
                role="assistant",
                content=answer,
                follow_up_question=follow_up_question,
            )
        )
        db.add(
            QARecord(
                session_id=session_id,
                course_id=course_id,
                question=query,
                answer=answer,
                keywords=keywords,
            )
        )

        if refined_query and cache_vector is not None:
            db.add(
                QACache(
                    course_id=course_id,
                    question=refined_query,
                    question_vector=cache_vector,
                    answer=answer,
                    follow_up_question=follow_up_question,
                )
            )

    def add_feedback(
        self,
        db: Session,
        *,
        user_id: str,
        course_id: str,
        rating: int,
        comment: str | None,
    ) -> None:
        db.add(
            CourseFeedback(
                user_id=user_id,
                course_id=course_id,
                rating=rating,
                comment=comment,
            )
        )
        db.commit()


rag_repository = RAGRepository()
