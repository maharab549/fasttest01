from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from .. import crud, schemas, auth, models
from ..database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get notifications for current user with improved filtering"""
    try:
        query = db.query(models.Notification).filter(
            models.Notification.user_id == current_user.id
        )
        
        if unread_only:
            query = query.filter(models.Notification.is_read == False)
        
        if notification_type:
            query = query.filter(models.Notification.type == notification_type)
        
        # Order by created_at descending (newest first)
        notifications = query.order_by(desc(models.Notification.created_at)).offset(skip).limit(limit).all()
        
        # Get total count for pagination
        total_count = query.count()
        
        # Return in the expected format with data wrapper
        return {
            "data": notifications,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notifications: {str(e)}")


@router.put("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Mark a notification as read"""
    try:
        notification = db.query(models.Notification).filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if not notification.is_read:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
        
        return {
            "message": "Notification marked as read",
            "notification": notification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking notification as read: {str(e)}")


@router.put("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Mark all notifications as read for current user"""
    try:
        # Update all unread notifications for the current user
        updated_count = db.query(models.Notification).filter(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False
        ).update({"is_read": True})
        
        db.commit()
        
        return {
            "message": f"Marked {updated_count} notifications as read",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking all notifications as read: {str(e)}")


@router.get("/unread-count")
def get_unread_notifications_count(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get count of unread notifications"""
    try:
        count = db.query(models.Notification).filter(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False
        ).count()
        
        return {"unread_count": count}
        
    except Exception as e:
        # Return 0 on error to prevent UI breaking
        return {"unread_count": 0}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Delete a notification"""
    try:
        notification = db.query(models.Notification).filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        db.delete(notification)
        db.commit()
        
        return {"message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting notification: {str(e)}")


@router.get("/types")
def get_notification_types(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Get available notification types for filtering"""
    try:
        types = db.query(models.Notification.type).filter(
            models.Notification.user_id == current_user.id
        ).distinct().all()
        
        return {
            "types": [t[0] for t in types if t[0]]
        }
        
    except Exception as e:
        return {"types": []}


def create_notification(
    db: Session, 
    user_id: int, 
    title: str, 
    message: str, 
    notification_type: str = "info", 
    related_order_id: int = None
):
    """Helper function to create notifications with better error handling"""
    try:
        # Validate user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        notification = models.Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            related_order_id=related_order_id
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
        
    except Exception as e:
        db.rollback()
        print(f"Error creating notification: {str(e)}")
        return None


def create_bulk_notifications(
    db: Session,
    notifications_data: List[dict]
):
    """Create multiple notifications at once"""
    try:
        notifications = []
        for data in notifications_data:
            notification = models.Notification(**data)
            notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        
        return notifications
        
    except Exception as e:
        db.rollback()
        print(f"Error creating bulk notifications: {str(e)}")
        return []
