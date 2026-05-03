from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Dict, Any
from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=Dict[str, Any])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user and return an access token plus the user object"""
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
    
    # Create access token so frontend can auto-login
    access_token_expires = timedelta(minutes=auth.settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )

    # Return a JSON-serializable user object (avoid returning SQLAlchemy model directly)
    user_obj = {
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username,
        "full_name": db_user.full_name,
        "is_active": db_user.is_active,
        "is_seller": db_user.is_seller,
        "is_admin": db_user.is_admin,
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
    }

    return {"user": user_obj, "access_token": access_token, "token_type": "bearer"}


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


@router.post("/register-with-referral", response_model=Dict[str, Any])
def register_with_referral(
    user: schemas.UserCreate,
    referral_signup: schemas.ReferralSignup,
    db: Session = Depends(get_db)
):
    """Register a new user with a referral code and return an access token plus the user object"""
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
    
    # Create access token so frontend can auto-login
    access_token_expires = timedelta(minutes=auth.settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )

    # Return a JSON-serializable user object (avoid returning SQLAlchemy model directly)
    user_obj = {
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username,
        "full_name": db_user.full_name,
        "is_active": db_user.is_active,
        "is_seller": db_user.is_seller,
        "is_admin": db_user.is_admin,
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
    }

    return {"user": user_obj, "access_token": access_token, "token_type": "bearer"}

