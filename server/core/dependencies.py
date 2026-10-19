"""
server/core/dependencies.py — FastAPI dependency injection guards for JWT authentication and RBAC.
"""
from __future__ import annotations

import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from server.core.security import decode_access_token
from server.models.user import UserDocument

# OAuth2 bearer token extractor
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
) -> UserDocument:
    """Validate Bearer JWT token and return authenticated UserDocument."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    # Find user by ObjectId or string representation
    user = None
    if ObjectId.is_valid(user_id):
        user = await UserDocument.get(ObjectId(user_id))
    if not user:
        user = await UserDocument.find_one(UserDocument.email == user_id)

    if not user:
        raise credentials_exception

    return user


async def require_teacher(
    current_user: UserDocument = Depends(get_current_user),
) -> UserDocument:
    """Enforce Teacher role permission guard."""
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Teacher role permission is required for this operation.",
        )
    return current_user


async def require_student(
    current_user: UserDocument = Depends(get_current_user),
) -> UserDocument:
    """Enforce Student role permission guard."""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Student role permission is required for this operation.",
        )
    return current_user
