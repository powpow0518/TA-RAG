import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# 讓腳本能找到 app 資料夾內的 model
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings
from app.models.user import User

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

# 使用 localhost 進行連線 (假設資料庫在 docker 中執行且 port mapping 5432)
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "change-me-before-use")

def add_admin():
    db = SessionLocal()
    try:
        # 檢查是否已存在 admin
        admin = db.query(User).filter(User.user_id == "admin").first()
        if admin:
            print("Admin user already exists.")
            return

        new_admin = User(
            user_id="admin",
            username="Administrator",
            hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        print("Admin user 'admin' added successfully.")
        print("Password source: ADMIN_BOOTSTRAP_PASSWORD or fallback demo value.")
    except Exception as e:
        db.rollback()
        print(f"Error adding admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_admin()
