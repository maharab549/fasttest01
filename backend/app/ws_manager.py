import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # map user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        conns = self.active_connections.setdefault(user_id, set())
        conns.add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.active_connections.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self.active_connections[user_id]

    async def send_personal_message(self, user_id: int, message: dict):
        conns = self.active_connections.get(user_id, set())
        text = json.dumps(message, default=str)
        for ws in list(conns):
            try:
                await ws.send_text(text)
            except Exception:
                # remove broken connections
                conns.discard(ws)

    async def broadcast(self, message: dict):
        text = json.dumps(message, default=str)
        for conns in list(self.active_connections.values()):
            for ws in list(conns):
                try:
                    await ws.send_text(text)
                except Exception:
                    conns.discard(ws)


manager = ConnectionManager()
