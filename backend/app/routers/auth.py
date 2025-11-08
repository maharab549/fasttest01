from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    
    # Create user
    db_user = crud.create_user(db=db, user=user)
    
    # Create loyalty account with signup bonus
    crud.create_loyalty_account(db=db, user_id=db_user.id)
    
    # If user is a seller, create seller profile
    if user.is_seller:
        seller_data = schemas.SellerCreate(
            store_name=f"{user.full_name}'s Store",
            store_slug=user.username.lower().replace(" ", "-"),
            store_description=f"Welcome to {user.full_name}'s store!"
        )
        crud.create_seller(db=db, seller=seller_data, user_id=db_user.id)
    
    return db_user


@router.post("/login", response_model=schemas.Token)
async def login_user(request: Request, db: Session = Depends(get_db)):
    """Login user and return access token.

    Accepts either JSON body or form-encoded data (tests send form data).
    """
    username = None
    password = None
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    else:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            # Missing/invalid body
            raise HTTPException(status_code=422, detail="Invalid login payload")

    user = auth.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(auth.get_current_active_user)):
    """Get current user information"""
    return current_user


@router.get("/verify-token")
def verify_token(current_user: schemas.User = Depends(auth.get_current_active_user)):
    """Verify if token is valid"""
    return {"valid": True, "user_id": current_user.id, "username": current_user.username}



@router.put("/profile", response_model=schemas.User)
def update_profile(
    profile_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    """Update current user profile"""
    # Check if email is being changed and if it's already taken
    if profile_data.email and profile_data.email != current_user.email:
        existing_user = crud.get_user_by_email(db, email=profile_data.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # Check if username is being changed and if it's already taken
    if profile_data.username and profile_data.username != current_user.username:
        existing_user = crud.get_user_by_username(db, username=profile_data.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
    
    # Update user profile
    updated_user = crud.update_user(db=db, user_id=current_user.id, user_update=profile_data)
    
    # If the user is updated to be a seller, ensure a seller profile exists
    if updated_user.is_seller and not crud.get_seller_by_user_id(db, updated_user.id):
        seller_data = schemas.SellerCreate(
            store_name=f"{updated_user.full_name}\'s Store",
            store_slug=updated_user.username.lower().replace(" ", "-"),
            store_description=f"Welcome to {updated_user.full_name}\'s store!"
        )
        crud.create_seller(db=db, seller=seller_data, user_id=updated_user.id)
    
    return updated_user


@router.post("/register-with-referral", response_model=schemas.User)
def register_with_referral(
    user: schemas.UserCreate,
    referral_signup: schemas.ReferralSignup,
    db: Session = Depends(get_db)
):
    """Register a new user with a referral code"""
    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Validate referral code
    referrer_account = crud.get_loyalty_account_by_referral_code(db, referral_signup.referral_code)
    if not referrer_account:
        raise HTTPException(status_code=400, detail="Invalid referral code")
    
    # Create user
    db_user = crud.create_user(db=db, user=user)
    
    # Create loyalty account with signup bonus
    crud.create_loyalty_account(db=db, user_id=db_user.id)
    
    # Process referral (awards points to both referrer and new user)
    crud.process_referral(db, referral_signup.referral_code, db_user.id)
    
    # If user is a seller, create seller profile
    if user.is_seller:
        seller_data = schemas.SellerCreate(
            store_name=f"{user.full_name}'s Store",
            store_slug=user.username.lower().replace(" ", "-"),
            store_description=f"Welcome to {user.full_name}'s store!"
        )
        crud.create_seller(db=db, seller=seller_data, user_id=db_user.id)
    
    return db_user

    return updated_user


# ==================== PASSWORD RESET ====================

@router.post("/forgot-password", response_model=None)
def forgot_password(
    request: Request,
    email_request: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset token and send email
    
    Features:
    - Rate limiting (prevent abuse and brute force)
    - Email validation (checks if user exists)
    - Secure token generation (256-bit tokens)
    - Professional email templates
    - Comprehensive logging and monitoring
    """
    import secrets
    import logging
    from datetime import datetime, timedelta
    from ..services.email_service_enhanced import email_service
    from .. import models
    from ..config import settings
    
    logger = logging.getLogger(__name__)
    
    # Get client IP for rate limiting
    client_ip = None
    if request and request.client:
        client_ip = request.client.host
    
    # 1. SECURITY: Check rate limiting FIRST (before checking if email exists)
    # This prevents attackers from discovering valid emails
    email = email_request.email.lower().strip()
    rate_limited, rate_limit_msg = email_service.check_rate_limit(email, client_ip or "unknown")
    
    if not rate_limited:
        logger.warning(f"🚫 Rate limit exceeded: {rate_limit_msg}")
        # Don't reveal it's rate limited, use generic message
        return {
            "message": "If an account exists with this email, you will receive a password reset link.",
            "email_sent": False,
            "rate_limited": True
        }
    
    # 2. Find user by email
    user = crud.get_user_by_email(db, email=email)
    if not user:
        # User doesn't exist - don't reveal this, just return generic message
        logger.info(f"⚠️ Password reset requested for non-existent email: {email}")
        return {
            "message": "If an account exists with this email, you will receive a password reset link.",
            "email_sent": False,
            "user_found": False
        }
    
    # 3. User exists - INVALIDATE any previous reset tokens (security best practice)
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.is_used == False
    ).update({"is_used": True})
    db.commit()
    logger.debug(f"Invalidated previous reset tokens for user {user.id}")
    
    # 4. Generate new secure reset token
    token = secrets.token_urlsafe(32)  # 256-bit secure random token
    expires_at = datetime.utcnow() + timedelta(hours=24)  # 24-hour expiration
    
    reset_token = models.PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    logger.debug(f"Generated new reset token for user {user.id}: expires at {expires_at}")
    
    # 5. Build reset URL
    frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:5173"
    reset_url = f"{frontend_url}/reset-password?token={token}"
    
    # 6. Extract user's name for personalization
    user_full_name = getattr(user, 'full_name', None) or user.username
    if isinstance(user_full_name, str) and user_full_name.strip():
        user_name = user_full_name.split()[0]
    else:
        user_name = str(user.username)
    
    # 7. Try to send professional email
    email_result = email_service.send_password_reset_email(
        recipient_email=str(user.email),
        reset_url=reset_url,
        user_name=user_name,
        user_email=str(user.email),
        ip_address=client_ip or "unknown",
        db_session=db
    )
    
    email_sent = email_result.get("success", False)
    
    # 8. Log to console for development/debugging
    logger.info(
        f"\n{'='*60}\n"
        f"🔐 PASSWORD RESET REQUEST\n"
        f"{'='*60}\n"
        f"User: {user.username} ({user.email})\n"
        f"User ID: {user.id}\n"
        f"Token: {token[:16]}...{token[-16:]}\n"
        f"Expires: {expires_at}\n"
        f"Reset URL: {reset_url}\n"
        f"Email Sent: {email_sent}\n"
        f"Email Message: {email_result.get('message', 'Unknown')}\n"
        f"Client IP: {client_ip}\n"
        f"{'='*60}\n"
    )
    
    # Print to console for development
    print(f"\n{'='*60}")
    print(f"🔐 PASSWORD RESET REQUEST")
    print(f"{'='*60}")
    print(f"User: {user.username} ({user.email})")
    print(f"Token: {token[:16]}...{token[-16:]}")
    print(f"Expires: {expires_at}")
    print(f"Reset URL: {reset_url}")
    print(f"Email Sent: {email_sent}")
    print(f"Email Status: {email_result.get('message', 'Unknown')}")
    print(f"Client IP: {client_ip}")
    print(f"{'='*60}\n")
    
    # 9. Return professional response
    return {
        "message": "If an account exists with this email, you will receive a password reset link.",
        "email_sent": email_sent,
        "user_found": True,
        "token_expires_in_hours": 24,
        "rate_limited": False
    }


@router.post("/reset-password")
def reset_password(
    reset_request: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using reset token"""
    from .. import models
    from datetime import datetime
    
    # Find valid reset token
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == reset_request.token,
        models.PasswordResetToken.is_used == False,
        models.PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate new password
    if len(reset_request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password
    hashed_password = auth.get_password_hash(reset_request.new_password)
    user.hashed_password = hashed_password
    
    # Mark token as used
    reset_token.is_used = True
    reset_token.used_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Password has been reset successfully"}


@router.get("/reset-token/{token}")
def validate_reset_token(token: str, db: Session = Depends(get_db)):
    """Validate if a reset token is valid"""
    from .. import models
    from datetime import datetime
    
    reset_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token,
        models.PasswordResetToken.is_used == False,
        models.PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {
        "valid": True,
        "token": token,
        "user_id": reset_token.user_id
    }
