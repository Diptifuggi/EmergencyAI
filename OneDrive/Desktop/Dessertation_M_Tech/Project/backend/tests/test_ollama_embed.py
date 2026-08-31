from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import OllamaUnavailableError
from app.services.ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_ollama_client_init_and_embed_success() -> None:
    # Test initialization default values
    client = OllamaClient()
    assert client.encoding_model == "kimi"
    assert client.model == "qwen2.5:0.5b"

    # Test custom initialization
    custom_client = OllamaClient(model="custom-decode", encoding_model="custom-encode")
    assert custom_client.model == "custom-decode"
    assert custom_client.encoding_model == "custom-encode"

    # Mock response from Ollama API
    mock_response = httpx.Response(
        status_code=200,
        json={"model": "custom-encode", "embeddings": [[0.1, 0.2, 0.3]]},
        request=httpx.Request("POST", "http://localhost:11434/api/embed"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        embeddings = await custom_client.embed("hello world")

        assert embeddings == [[0.1, 0.2, 0.3]]
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/embed"
        assert kwargs["json"] == {
            "model": "custom-encode",
            "input": "hello world",
        }


@pytest.mark.asyncio
async def test_ollama_client_embed_error() -> None:
    client = OllamaClient()
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("timeout")
        with pytest.raises(OllamaUnavailableError, match="Ollama request timed out"):
            await client.embed("test")
