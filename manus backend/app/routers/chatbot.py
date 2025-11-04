from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .. import schemas, auth
from ..database import get_db
from ..ai_chatbot import get_chatbot_response

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/ask", response_model=schemas.ChatbotResponse)
def ask_chatbot(
    query: schemas.ChatbotQuery,
    request: Request, # To get client IP as a simple session ID
    db: Session = Depends(get_db)
):
    """Send a query to the AI chatbot and get a response."""
    # Use the client's IP address as a simple, anonymous session ID for conversation history
    # In a real application, this would be the authenticated user's ID.
    session_id = request.client.host if request.client else "anonymous_user"

    try:
        response_text = get_chatbot_response(query.message, session_id=session_id)
        return schemas.ChatbotResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

