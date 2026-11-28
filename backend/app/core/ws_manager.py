from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """In-memory WebSocket channel manager for TrackMe and Operator live events."""

    def __init__(self) -> None:
        self._channels: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels[channel].add(websocket)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                self._channels.pop(channel, None)

    async def broadcast(self, channel: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._channels.get(channel, set()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._channels[channel].discard(ws)


ws_manager = ConnectionManager()
