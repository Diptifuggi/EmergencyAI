from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.emergency_calls import _validated_idempotency_key
from app.models.emergency_call import EmergencyCall
from app.services import emergency_call_analysis_runner as runner


def test_valid_idempotency_key_is_preserved() -> None:
    key = "a4c2f9b7d8104e4b9a55c38c2c3e1f00"
    assert _validated_idempotency_key(key) == key
    assert _validated_idempotency_key(None) is None


@pytest.mark.parametrize("key", ["", "contains spaces", "a" * 129, "κλειδί"])
def test_invalid_idempotency_key_is_rejected(key: str) -> None:
    with pytest.raises(HTTPException) as error:
        _validated_idempotency_key(key)
    assert error.value.status_code == 400


def test_emergency_retry_key_index_is_unique() -> None:
    index = next(
        index
        for index in EmergencyCall.__table__.indexes
        if index.name == "uq_emergency_calls_idempotency_key"
    )
    assert index.unique is True


@pytest.mark.asyncio
async def test_background_analysis_uses_independent_session(monkeypatch) -> None:
    emergency = SimpleNamespace(id=uuid.uuid4())
    analysis = AsyncMock()

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, model, emergency_id):
            assert model is EmergencyCall
            assert emergency_id == emergency.id
            return emergency

    monkeypatch.setattr(runner, "async_session", Session)
    monkeypatch.setattr(runner, "run_post_create_analysis", analysis)

    await runner.run_post_create_analysis_in_background(emergency.id)

    analysis.assert_awaited_once()
