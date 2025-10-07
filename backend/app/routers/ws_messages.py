from fastapi import APIRouter, WebSocket, Query, HTTPException, status # <-- Add HTTPException and status
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import auth, crud
from ..ws_manager import manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# --- REPLACEMENT FUNCTION ---
def get_user_from_token(token: str) -> crud.User:
    """
    Verifies a JWT token and returns the corresponding user.
    Raises HTTPException if the token is invalid, expired, or the user is not found.
    """
    # This is the same exception used by get_current_user, ensuring consistent error handling.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = auth.verify_token(token, credentials_exception)
        if token_data is None:
            raise credentials_exception
    except Exception: # Catches JWTError from verify_token
        raise credentials_exception

    db = SessionLocal()
    try:
        user = crud.get_user_by_username(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    finally:
        db.close()


@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint expects an access token as query param `token`"""
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WebSocket connection attempt without a token.")
        return

    try:
        # This will now raise a detailed HTTPException on failure
        user = get_user_from_token(token)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    except HTTPException as e:
        # Log the specific reason for failure
        logger.error(f"WebSocket auth failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred during WebSocket auth: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    user_id = user.id
    await manager.connect(user_id, websocket)
    logger.info(f"User {user_id} connected to websocket")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"User {user_id} disconnected from websocket")

