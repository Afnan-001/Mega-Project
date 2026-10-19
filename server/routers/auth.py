"""
server/routers/auth.py — Authentication router for user registration, login, and profile.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from server.core.dependencies import get_current_user
from server.core.security import create_access_token, hash_password, verify_password
from server.models.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from server.models.user import UserDocument

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Teacher or Student account",
)
async def register(req: UserRegisterRequest):
    # Check if email is already taken
    existing_user = await UserDocument.find_one(UserDocument.email == req.email.lower().strip())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    role = req.role.lower().strip()
    if role not in ("teacher", "student"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'teacher' or 'student'.",
        )

    hashed = hash_password(req.password)
    user = UserDocument(
        email=req.email.lower().strip(),
        hashed_password=hashed,
        full_name=req.full_name.strip(),
        role=role,
    )
    await user.insert()

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
        full_name=user.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password (supports JSON body or OAuth2 form)",
)
async def login(request: Request):
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form_data = await request.form()
            email = form_data.get("username") or form_data.get("email")
            password = form_data.get("password")
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email (or username) and password are required.",
        )

    email = str(email).lower().strip()
    password = str(password)

    user = await UserDocument.find_one(UserDocument.email == email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=str(user.id),
        full_name=user.full_name,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user's profile details",
)
async def get_me(current_user: UserDocument = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        created_at=current_user.created_at,
    )
