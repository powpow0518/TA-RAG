from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/me")
def read_user_me(current_user: User = Depends(get_current_active_user)):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role
    }
