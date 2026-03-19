from sqlalchemy.orm import Session

from app.models.course import Course


class CourseRepository:
    def list_all(self, db: Session) -> list[Course]:
        return db.query(Course).all()

    def get_by_course_id(self, db: Session, course_id: str) -> Course | None:
        return db.query(Course).filter(Course.course_id == course_id).first()

    def create(
        self,
        db: Session,
        *,
        course_id: str,
        course_name: str,
        teacher_id: str | None,
    ) -> Course:
        course = Course(course_id=course_id, course_name=course_name, teacher_id=teacher_id)
        db.add(course)
        db.commit()
        db.refresh(course)
        return course


course_repository = CourseRepository()
