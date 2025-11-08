from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from .. import crud, schemas, auth, models
from ..database import get_db
from .notifications import create_notification

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/", response_model=schemas.Message)
def send_message(
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Send a message to another user"""
    # Check if receiver exists
    receiver = crud.get_user(db=db, user_id=message.receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Create message
    db_message = models.Message(
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        subject=message.subject,
        content=message.content,
        related_order_id=message.related_order_id,
        related_product_id=message.related_product_id
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Create notification for the receiver
    create_notification(
        db=db,
        user_id=message.receiver_id,
        title=f"New message from {current_user.full_name}",
        message=f"Subject: {message.subject or 'No subject'}",
        notification_type="message"
    )
    
    return db_message


@router.get("/")
def get_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    conversation_with: Optional[int] = Query(None),
    conversation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get messages for current user"""
    query = db.query(models.Message).filter(
        or_(
            models.Message.sender_id == current_user.id,
            models.Message.receiver_id == current_user.id
        )
    )
    
    # Filter by conversation partner
    if conversation_with:
        query = query.filter(
            or_(
                and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == conversation_with),
                and_(models.Message.sender_id == conversation_with, models.Message.receiver_id == current_user.id)
            )
        )
    
    # Order by created_at ascending for proper chat display (oldest first)
    messages = query.order_by(models.Message.created_at.asc()).offset(skip).limit(limit).all()
    
    # Mark messages as read if they are received by current user
    if conversation_with:
        unread_messages = db.query(models.Message).filter(
            models.Message.sender_id == conversation_with,
            models.Message.receiver_id == current_user.id,
            models.Message.is_read == False
        ).all()
        
        for msg in unread_messages:
            msg.is_read = True
        
        if unread_messages:
            db.commit()
    
    # Return in the expected format with data wrapper
    return {
        "data": messages,
        "total": query.count(),
        "skip": skip,
        "limit": limit
    }


@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get list of conversations for current user with improved logic"""
    
    # Get all unique conversation partners
    # Subquery for users current user sent messages to
    sent_to_subquery = db.query(models.Message.receiver_id.label('user_id')).filter(
        models.Message.sender_id == current_user.id
    ).distinct().subquery()
    
    # Subquery for users who sent messages to current user
    received_from_subquery = db.query(models.Message.sender_id.label('user_id')).filter(
        models.Message.receiver_id == current_user.id
    ).distinct().subquery()
    
    # Union both subqueries to get all conversation partners
    conversation_partners_query = db.query(sent_to_subquery.c.user_id).union(
        db.query(received_from_subquery.c.user_id)
    )
    
    conversations = []
    
    for partner_result in conversation_partners_query.all():
        partner_id = partner_result[0]
        
        # Get user details
        partner_user = db.query(models.User).filter(models.User.id == partner_id).first()
        if not partner_user:
            continue
            
        # Get latest message in conversation
        latest_message = db.query(models.Message).filter(
            or_(
                and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == partner_id),
                and_(models.Message.sender_id == partner_id, models.Message.receiver_id == current_user.id)
            )
        ).order_by(models.Message.created_at.desc()).first()
        
        # Count unread messages from this partner
        unread_count = db.query(models.Message).filter(
            models.Message.sender_id == partner_id,
            models.Message.receiver_id == current_user.id,
            models.Message.is_read == False
        ).count()
        
        conversation_data = {
            "id": f"conv_{partner_id}",
            "other_user": {
                "id": partner_user.id,
                "full_name": partner_user.full_name,
                "username": partner_user.username,
                "email": partner_user.email,
                "avatar": None,  # Add avatar 
                "is_seller": partner_user.is_seller
            },
            "last_message": {
                "id": latest_message.id,
                "content": latest_message.content,
                "created_at": latest_message.created_at,
                "sender_id": latest_message.sender_id,
                "is_read": latest_message.is_read
            } if latest_message else None,
            "unread_count": unread_count,
            "related_product": None  # will add later
        }
        
        conversations.append(conversation_data)
    
    # Sort conversations by latest message timestamp (most recent first)
    conversations.sort(
        key=lambda x: x["last_message"]["created_at"] if x["last_message"] else "1970-01-01",
        reverse=True
    )
    
    return {
        "data": conversations
    }


@router.put("/{message_id}/read")
def mark_message_as_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Mark a message as read"""
    message = db.query(models.Message).filter(
        models.Message.id == message_id,
        models.Message.receiver_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    
    return {"message": "Message marked as read"}


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get count of unread messages"""
    count = db.query(models.Message).filter(
        models.Message.receiver_id == current_user.id,
        models.Message.is_read == False
    ).count()
    
    return {"unread_count": count}


@router.post("/start-conversation")
def start_conversation(
    receiver_id: int,
    subject: Optional[str] = None,
    initial_message: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Start a new conversation or get existing one"""
    
    # Check if receiver exists
    receiver = crud.get_user(db=db, user_id=receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if conversation already exists
    existing_conversation = db.query(models.Message).filter(
        or_(
            and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == receiver_id),
            and_(models.Message.sender_id == receiver_id, models.Message.receiver_id == current_user.id)
        )
    ).first()
    
    conversation_data = {
        "id": f"conv_{receiver_id}",
        "other_user": {
            "id": receiver.id,
            "full_name": receiver.full_name,
            "username": receiver.username,
            "email": receiver.email,
            "avatar": None,
            "is_seller": receiver.is_seller
        },
        "exists": existing_conversation is not None
    }
    
    # If initial message provided, send it
    if initial_message and initial_message.strip():
        message_data = schemas.MessageCreate(
            receiver_id=receiver_id,
            subject=subject or f"Message from {current_user.full_name}",
            content=initial_message.strip(),
            related_product_id=product_id
        )
        
        new_message = send_message(message_data, db, current_user)
        conversation_data["initial_message"] = new_message
    
    return conversation_data
