from fastapi import APIRouter, WebSocket, Query
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import auth, crud
from ..ws_manager import manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_user_from_token(token: str):
    """Decode token to username and fetch user from DB (synchronous helper)."""
    credentials_exception = Exception("Invalid token")
    token_data = auth.verify_token(token, credentials_exception)
    db = SessionLocal()
    try:
        user = crud.get_user_by_username(db, token_data.username)
        return user
    finally:
        db.close()


@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint expects an access token as query param `token`"""
    if not token:
        await websocket.close(code=1008)
        return

    try:
        user = get_user_from_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    if not user:
        await websocket.close(code=1008)
        return

    user_id = user.id
    await manager.connect(user_id, websocket)
    logger.info(f"User {user_id} connected to websocket")
    try:
        while True:
            # Keep the connection alive and optionally receive messages
            data = await websocket.receive_text()
            # Optionally handle client-sent events (typing, read receipts)
            logger.debug(f"WS received from {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"User {user_id} disconnected from websocket")
