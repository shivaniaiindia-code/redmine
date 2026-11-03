import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_ai_grounded_chat(client: AsyncClient):
    """
    Validates OpenRouter AI integration with Qwen3.5-Flash model:
    Verifies that conversational queries are answered using verified database ground truth.
    """
    prompt = "Which projects are currently at risk or have overdue tasks?"
    resp = await client.post(
        "/api/v1/ai/chat",
        json={"prompt": prompt}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 20
    assert data["grounded"] is True
    print("\nAI Response Preview:", data["response"][:150])

