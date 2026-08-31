from __future__ import annotations

import httpx

from ..core.config import settings
from ..core.exceptions import OllamaUnavailableError
from ..core.logger import get_logger

logger = get_logger("app.services.ollama_client")

DEFAULT_TIMEOUT_SECONDS = 60.0


class OllamaClient:
    """Thin HTTP client for local Ollama generate API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        encoding_model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_DECODING_MODEL", None) or settings.OLLAMA_MODEL
        self.encoding_model = encoding_model or getattr(settings, "OLLAMA_ENCODING_MODEL", None) or "kimi"
        self.timeout = timeout

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Ollama /api/chat with JSON response format.

        Returns the assistant message content string (expected JSON).
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Ollama request timed out after %.0fs", self.timeout)
            raise OllamaUnavailableError("Ollama request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("Ollama HTTP error: %s", exc)
            raise OllamaUnavailableError("Ollama backend is unavailable") from exc

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning("Ollama returned non-JSON HTTP body")
            raise OllamaUnavailableError("Ollama returned an invalid response") from exc

        message = body.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaUnavailableError("Ollama returned empty analysis content")

        return content.strip()

    async def embed(self, input_text: str | list[str]) -> list[list[float]]:
        """
        Call Ollama /api/embed to generate embeddings.

        Returns a list of embedding vectors (list of floats).
        """
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.encoding_model,
            "input": input_text,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Ollama request timed out after %.0fs", self.timeout)
            raise OllamaUnavailableError("Ollama request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("Ollama HTTP error: %s", exc)
            raise OllamaUnavailableError("Ollama backend is unavailable") from exc

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning("Ollama returned non-JSON HTTP body")
            raise OllamaUnavailableError("Ollama returned an invalid response") from exc

        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list):
            raise OllamaUnavailableError("Ollama returned empty or invalid embeddings")

        return embeddings
