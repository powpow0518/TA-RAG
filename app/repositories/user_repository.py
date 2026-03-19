from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get_by_user_id(self, db: Session, user_id: str) -> User | None:
        return db.query(User).filter(User.user_id == user_id).first()

    def create(
        self,
        db: Session,
        *,
        user_id: str,
        username: str,
        hashed_password: str,
        role: str,
    ) -> User:
        user = User(
            user_id=user_id,
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


user_repository = UserRepository()
