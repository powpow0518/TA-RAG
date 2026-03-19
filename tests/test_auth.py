import pytest
from httpx import AsyncClient
from app.api.v1.endpoints.auth import hash_password
from app.models.user import User

async def test_register_and_login(client: AsyncClient):
    # 1. 測試正常註冊
    register_data = {
        "user_id": "test_user_001",
        "password": "password123",
        "username": "tester",
        "role": "student"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 200

async def test_malicious_admin_registration(client: AsyncClient):
    # 2. 測試試圖註冊為 admin (應被禁止)
    malicious_data = {
        "user_id": "hacker_01",
        "password": "password123",
        "role": "admin" 
    }
    response = await client.post("/api/v1/auth/register", json=malicious_data)
    
    # 由於 Pydantic Literal 限制，會回傳 422
    assert response.status_code == 422
    
    # 驗證是否真的沒註冊成功
    login_data = {"username": "hacker_01", "password": "password123"}
    login_res = await client.post("/api/v1/auth/login", data=login_data)
    assert login_res.status_code == 401

async def test_powpow_login_logic(client: AsyncClient, db_session):
    # 3. 測試 powpow 登入邏輯
    # 直接在 db_session (測試用的 sqlite) 插入資料
    powpow = User(
        user_id="powpow", 
        hashed_password=hash_password("123456780000"), 
        role="admin",
        username="powpow"
    )
    db_session.add(powpow)
    db_session.commit()
    
    login_data = {
        "username": "powpow",
        "password": "123456780000"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
