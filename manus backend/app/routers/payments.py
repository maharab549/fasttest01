from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/alipay/create")
def create_alipay_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create Alipay payment for order (test mode)"""
    # Get order
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this order")
    
    # Check if order is already paid
    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order is already paid")
    
    # For test mode, simulate payment creation
    payment_data = {
        "payment_id": f"alipay_test_{order.id}",
        "payment_url": f"https://test-alipay.com/pay/{order.id}",
        "amount": order.total_amount,
        "currency": "USD",
        "status": "pending"
    }
    
    # Update order payment info
    order.payment_method = "alipay"
    order.payment_id = payment_data["payment_id"]
    db.commit()
    
    return payment_data


@router.post("/wechat/create")
def create_wechat_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Create WeChat Pay payment for order (test mode)"""
    # Get order
    order = crud.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this order")
    
    # Check if order is already paid
    if order.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Order is already paid")
    
    # For test mode, simulate payment creation
    payment_data = {
        "payment_id": f"wechat_test_{order.id}",
        "payment_url": f"https://test-wechatpay.com/pay/{order.id}",
        "amount": order.total_amount,
        "currency": "USD",
        "status": "pending"
    }
    
    # Update order payment info
    order.payment_method = "wechat"
    order.payment_id = payment_data["payment_id"]
    db.commit()
    
    return payment_data


@router.post("/test/complete")
def complete_test_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Complete test payment (for testing purposes only)"""
    # Find order by payment_id
    order = db.query(crud.models.Order).filter(
        crud.models.Order.payment_id == payment_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if order belongs to current user
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update payment status
    order.payment_status = "paid"
    order.status = "confirmed"
    db.commit()
    
    return {
        "message": "Payment completed successfully",
        "order_id": order.id,
        "payment_id": payment_id,
        "status": "paid"
    }


@router.get("/methods")
def get_payment_methods():
    """Get available payment methods"""
    return {
        "methods": [
            {
                "id": "alipay",
                "name": "Alipay",
                "description": "Pay with Alipay",
                "enabled": True,
                "test_mode": True
            },
            {
                "id": "wechat",
                "name": "WeChat Pay",
                "description": "Pay with WeChat Pay",
                "enabled": True,
                "test_mode": True
            }
        ]
    }

