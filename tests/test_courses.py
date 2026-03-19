import pytest
from httpx import AsyncClient

async def test_course_list_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/courses/")
    assert response.status_code == 401

async def test_create_course_flow(client: AsyncClient):
    # 1. 註冊老師
    await client.post("/api/v1/auth/register", json={
        "user_id": "teacher_bob",
        "password": "password",
        "role": "teacher"
    })
    
    # 2. 登入
    login_res = await client.post("/api/v1/auth/login", data={
        "username": "teacher_bob",
        "password": "password"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. 建立課程 (直接傳 query string 參數，因為 API 是這樣設計的)
    response = await client.post(
        "/api/v1/courses/?course_id=PY101&course_name=Python基礎",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["course_id"] == "PY101"
