"""
Notification system for order updates and customer notifications
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models, schemas
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling notifications"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        related_order_id: Optional[int] = None
    ) -> models.Notification:
        """Create a new notification for a user"""
        try:
            notification = models.Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                related_order_id=related_order_id,
                is_read=False
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            logger.info(f"Created notification for user {user_id}: {title}")
            return notification
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create notification: {e}")
            raise
    
    def notify_order_status_change(self, order_id: int, new_status: str):
        """Send notification when order status changes"""
        try:
            # Get the order
            order = self.db.query(models.Order).filter(models.Order.id == order_id).first()
            if not order:
                logger.warning(f"Order {order_id} not found for notification")
                return
            
            # Create notification based on status
            status_messages = {
                "confirmed": {
                    "title": "Order Confirmed",
                    "message": f"Your order #{order.id} has been confirmed and is being prepared for shipment."
                },
                "processing": {
                    "title": "Order Processing",
                    "message": f"Your order #{order.id} is now being processed and will be shipped soon."
                },
                "shipped": {
                    "title": "Order Shipped",
                    "message": f"Great news! Your order #{order.id} has been shipped and is on its way to you."
                },
                "delivered": {
                    "title": "Order Delivered",
                    "message": f"Your order #{order.id} has been delivered successfully. We hope you enjoy your purchase!"
                }
            }
            
            if new_status in status_messages:
                notification_data = status_messages[new_status]
                self.create_notification(
                    user_id=order.user_id,
                    title=notification_data["title"],
                    message=notification_data["message"],
                    notification_type="order_update",
                    related_order_id=order.id
                )
                
                # Also notify sellers when order is placed
                if new_status == "confirmed":
                    self.notify_sellers_new_order(order)
                    
        except Exception as e:
            logger.error(f"Failed to send order status notification: {e}")
    
    def notify_sellers_new_order(self, order: models.Order):
        """Notify sellers when they receive a new order"""
        try:
            # Get all sellers involved in this order
            seller_ids = set()
            for item in order.items:
                if item.product and item.product.seller_id:
                    seller_ids.add(item.product.seller_id)
            
            # Create notifications for each seller
            for seller_id in seller_ids:
                seller = self.db.query(models.Seller).filter(models.Seller.id == seller_id).first()
                if seller and seller.user_id:
                    self.create_notification(
                        user_id=seller.user_id,
                        title="New Order Received",
                        message=f"You have received a new order #{order.id}. Please review and confirm the order.",
                        notification_type="new_order",
                        related_order_id=order.id
                    )
                    
        except Exception as e:
            logger.error(f"Failed to notify sellers of new order: {e}")
    
    def get_user_notifications(
        self, 
        user_id: int, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[models.Notification]:
        """Get notifications for a user"""
        try:
            query = self.db.query(models.Notification).filter(
                models.Notification.user_id == user_id
            )
            
            if unread_only:
                query = query.filter(models.Notification.is_read == False)
            
            notifications = query.order_by(
                models.Notification.created_at.desc()
            ).limit(limit).all()
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read"""
        try:
            notification = self.db.query(models.Notification).filter(
                models.Notification.id == notification_id,
                models.Notification.user_id == user_id
            ).first()
            
            if notification:
                notification.is_read = True
                self.db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            self.db.rollback()
            return False
    
    def mark_all_notifications_read(self, user_id: int) -> bool:
        """Mark all notifications as read for a user"""
        try:
            self.db.query(models.Notification).filter(
                models.Notification.user_id == user_id,
                models.Notification.is_read == False
            ).update({"is_read": True})
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            self.db.rollback()
            return False

def get_notification_service(db: Session) -> NotificationService:
    """Get notification service instance"""
    return NotificationService(db)

