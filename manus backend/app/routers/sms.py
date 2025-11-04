from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from .. import schemas, auth, models
from ..database import get_db
from ..sms_service import sms_service, send_message_via_sms
from pydantic import BaseModel

router = APIRouter(prefix="/sms", tags=["sms"])


class SMSMessageRequest(BaseModel):
    receiver_phone: str
    message: str


class SMSWebhookData(BaseModel):
    from_phone: str = None
    to_phone: str = None
    body: str = ""
    message_id: str = None


@router.post("/send")
def send_sms_message(
    sms_request: SMSMessageRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Send SMS message to a phone number"""
    try:
        result = send_message_via_sms(
            sender_id=current_user.id,
            receiver_phone=sms_request.receiver_phone,
            message=sms_request.message,
            db=db
        )
        
        if result["success"]:
            return {
                "message": "SMS sent successfully",
                "sms_id": result["message_id"],
                "status": "sent"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@router.post("/webhook")
async def sms_webhook(request: Request):
    """Handle incoming SMS webhook from SMS provider"""
    try:
        # Get webhook data
        webhook_data = await request.json()
        
        # Process the webhook
        result = sms_service.receive_sms_webhook(webhook_data)
        
        if result["success"]:
            return {"status": "ok", "message": "Webhook processed successfully"}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/messages")
def get_sms_messages(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get SMS messages sent by current user"""
    messages = db.query(models.SMSMessage).filter(
        models.SMSMessage.sender_id == current_user.id
    ).order_by(models.SMSMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "data": messages,
        "total": db.query(models.SMSMessage).filter(
            models.SMSMessage.sender_id == current_user.id
        ).count()
    }


@router.get("/status/{sms_id}")
def get_sms_status(
    sms_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get SMS message status"""
    sms_message = db.query(models.SMSMessage).filter(
        models.SMSMessage.id == sms_id,
        models.SMSMessage.sender_id == current_user.id
    ).first()
    
    if not sms_message:
        raise HTTPException(status_code=404, detail="SMS message not found")
    
    return {
        "id": sms_message.id,
        "receiver_phone": sms_message.receiver_phone,
        "status": sms_message.status,
        "created_at": sms_message.created_at,
        "sms_message_id": sms_message.sms_message_id
    }


@router.post("/test")
def test_sms_service(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Test SMS service functionality (for development/testing)"""
    test_phone = "+1234567890"
    test_message = f"Test SMS from {current_user.full_name} - Marketplace SMS Service is working!"
    
    result = send_message_via_sms(
        sender_id=current_user.id,
        receiver_phone=test_phone,
        message=test_message,
        db=db
    )
    
    return {
        "message": "SMS test completed",
        "result": result,
        "note": "This is a test SMS - no actual SMS was sent in demo mode"
    }

