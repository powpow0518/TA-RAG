import pytest
from httpx import AsyncClient

async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

async def test_rag_ask_requires_auth(client: AsyncClient):
    # 不帶 Token 應該報錯
    query_data = {
        "query": "你好",
        "course_id": "CS101",
        "session_id": "test_session"
    }
    response = await client.post("/api/v1/rag/ask", json=query_data)
    assert response.status_code == 401
