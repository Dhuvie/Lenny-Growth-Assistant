import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_info(async_client: AsyncClient):
    res = await async_client.get("/api/info")
    assert res.status_code == 200
    data = res.json()
    assert data["app_name"] == "The Lenny Growth Assistant"
    assert "active_provider" in data
    assert "providers_supported" in data
    assert "ollama" in data["providers_supported"]
    assert "gemini" in data["providers_supported"]
    assert "available_models" in data
    assert "gemini" in data["available_models"]
    assert "gemini-3.5-flash-lite" in data["available_models"]["gemini"]
    assert "gemini-3.8-flash" in data["available_models"]["gemini"]
    assert "gemini-3.7-flash" in data["available_models"]["gemini"]
    assert "gemini-2.5-flash" in data["available_models"]["gemini"]


@pytest.mark.asyncio
async def test_session_lifecycle(async_client: AsyncClient):
    # 1. Create session
    create_res = await async_client.post("/api/sessions", json={"title": "Test Growth Session"})
    assert create_res.status_code == 201
    created_session = create_res.json()
    session_id = created_session["id"]
    assert created_session["title"] == "Test Growth Session"

    # 2. List sessions
    list_res = await async_client.get("/api/sessions")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["id"] == session_id for s in sessions)

    # 3. Get session detail
    detail_res = await async_client.get(f"/api/sessions/{session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == session_id
    assert "messages" in detail

    # 4. Patch session
    patch_res = await async_client.patch(f"/api/sessions/{session_id}", json={"title": "Renamed Session"})
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Renamed Session"

    # 5. Delete session
    del_res = await async_client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_res = await async_client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 404
    err_data = get_res.json()
    assert err_data["error"] == "HTTP_ERROR"


@pytest.mark.asyncio
async def test_structured_validation_error(async_client: AsyncClient):
    # Sending invalid payload to trigger 422
    res = await async_client.post("/api/chat", json={})
    assert res.status_code == 422
    data = res.json()
    assert data["error"] == "VALIDATION_ERROR"
    assert "details" in data
