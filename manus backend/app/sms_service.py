"""
SMS Service for Marketplace Application
Provides SMS functionality for messaging between users
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from . import models
from .database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSService:
    """SMS Service for sending and receiving SMS messages"""
    
    def __init__(self):
        # In a real implementation, you would use services like Twilio, AWS SNS, etc.
        # For demo purposes, we'll simulate SMS functionality
        self.api_key = os.getenv("SMS_API_KEY", "demo_key")
        self.api_url = os.getenv("SMS_API_URL", "https://api.sms-service.com")
        self.phone_number = os.getenv("SMS_PHONE_NUMBER", "+1234567890")
        
    def send_sms(self, to_phone: str, message: str, user_id: int = None) -> Dict[str, Any]:
        """
        Send SMS message to a phone number
        
        Args:
            to_phone: Recipient phone number
            message: SMS message content
            user_id: Optional user ID for tracking
            
        Returns:
            Dict with success status and message ID
        """
        try:
            # Validate phone number format
            if not self._validate_phone_number(to_phone):
                return {
                    "success": False,
                    "error": "Invalid phone number format",
                    "message_id": None
                }
            
            # In a real implementation, you would make an API call to SMS provider
            # For demo purposes, we'll simulate the SMS sending
            logger.info(f"Sending SMS to {to_phone}: {message}")
            
            # Simulate API call
            sms_data = {
                "to": to_phone,
                "from": self.phone_number,
                "body": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Simulate successful response
            message_id = f"sms_{datetime.utcnow().timestamp()}"
            
            # Log SMS for tracking (in real app, this would be stored in database)
            self._log_sms_message(
                to_phone=to_phone,
                message=message,
                message_id=message_id,
                user_id=user_id,
                direction="outbound"
            )
            
            return {
                "success": True,
                "message_id": message_id,
                "status": "sent",
                "to": to_phone
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message_id": None
            }
    
    def receive_sms_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming SMS webhook from SMS provider
        
        Args:
            webhook_data: Webhook payload from SMS provider
            
        Returns:
            Dict with processing status
        """
        try:
            from_phone = webhook_data.get("from")
            message_body = webhook_data.get("body", "")
            message_id = webhook_data.get("message_id")
            
            if not from_phone or not message_body:
                return {
                    "success": False,
                    "error": "Missing required fields in webhook data"
                }
            
            # Log incoming SMS
            self._log_sms_message(
                to_phone=self.phone_number,
                from_phone=from_phone,
                message=message_body,
                message_id=message_id,
                direction="inbound"
            )
            
            # Process the incoming message (e.g., create internal message, notify user)
            self._process_incoming_sms(from_phone, message_body)
            
            return {
                "success": True,
                "status": "processed",
                "message_id": message_id
            }
            
        except Exception as e:
            logger.error(f"Failed to process incoming SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_message_via_sms(self, sender_id: int, receiver_phone: str, message: str, db: Session) -> Dict[str, Any]:
        """
        Send a marketplace message via SMS
        
        Args:
            sender_id: ID of the user sending the message
            receiver_phone: Phone number of the recipient
            message: Message content
            db: Database session
            
        Returns:
            Dict with sending status
        """
        try:
            # Get sender information
            sender = db.query(models.User).filter(models.User.id == sender_id).first()
            if not sender:
                return {
                    "success": False,
                    "error": "Sender not found"
                }
            
            # Format SMS message
            sms_content = f"Message from {sender.full_name} on Marketplace: {message}"
            
            # Send SMS
            result = self.send_sms(
                to_phone=receiver_phone,
                message=sms_content,
                user_id=sender_id
            )
            
            if result["success"]:
                # Create SMS message record in database
                sms_message = models.SMSMessage(
                    sender_id=sender_id,
                    receiver_phone=receiver_phone,
                    message_content=message,
                    sms_message_id=result["message_id"],
                    status="sent"
                )
                db.add(sms_message)
                db.commit()
                
                logger.info(f"SMS sent successfully to {receiver_phone}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send message via SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        import re
        # Basic phone number validation (E.164 format)
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    def _log_sms_message(self, to_phone: str, message: str, message_id: str, 
                        user_id: int = None, direction: str = "outbound", 
                        from_phone: str = None):
        """Log SMS message for tracking and debugging"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
            "to": to_phone,
            "from": from_phone or self.phone_number,
            "message": message,
            "message_id": message_id,
            "user_id": user_id
        }
        
        logger.info(f"SMS Log: {log_entry}")
    
    def _process_incoming_sms(self, from_phone: str, message: str):
        """Process incoming SMS message"""
        # In a real implementation, you might:
        # 1. Look up user by phone number
        # 2. Create internal message
        # 3. Send notification
        # 4. Auto-reply with instructions
        
        logger.info(f"Processing incoming SMS from {from_phone}: {message}")
        
        # Auto-reply with instructions
        auto_reply = ("Thank you for your message! To continue the conversation, "
                     "please log in to our marketplace at marketplace.com/messages")
        
        self.send_sms(
            to_phone=from_phone,
            message=auto_reply
        )

# Global SMS service instance
sms_service = SMSService()

def send_sms_message(to_phone: str, message: str, user_id: int = None) -> Dict[str, Any]:
    """Convenience function to send SMS"""
    return sms_service.send_sms(to_phone, message, user_id)

def send_message_via_sms(sender_id: int, receiver_phone: str, message: str, db: Session) -> Dict[str, Any]:
    """Convenience function to send marketplace message via SMS"""
    return sms_service.send_message_via_sms(sender_id, receiver_phone, message, db)

