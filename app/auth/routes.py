"""
Authentication API routes for Clarity Local Runner.
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from .dependencies import get_auth_handler, get_current_user
from .exceptions import AuthenticationError
from .models import (
    AuthResponse,
    LoginRequest,
    PasswordResetRequest,
    PasswordUpdateRequest,
    TokenRefreshRequest,
    UserContext,
    UserProfileUpdate,
)
from .supabase_auth import SupabaseJWTAuth

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.get("/health", tags=["auth"])
async def auth_health():
    """
    Auth service health endpoint for tests.
    Returns simple top-level status as expected by tests.
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0",
    }


@router.post("/login", response_model=AuthResponse)
async def login(
    login_request: LoginRequest,
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> AuthResponse:
    """
    Authenticate user with email and password.

    This endpoint uses Supabase Auth to authenticate users and returns
    a JWT token for subsequent API calls.
    """
    try:
        # Use Supabase client to sign in user
        response = auth_handler.supabase.auth.sign_in_with_password(
            {"email": login_request.email, "password": login_request.password}
        )

        if response.user and response.session:
            # Validate the token to get user context
            user_context = await auth_handler.validate_token(
                response.session.access_token
            )

            return AuthResponse(
                success=True,
                user=user_context,
                token=response.session.access_token,
                error=None,
            )
        else:
            return AuthResponse(
                success=False, user=None, token=None, error="Invalid email or password"
            )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return AuthResponse(
            success=False, user=None, token=None, error="Authentication failed"
        )


@router.post("/logout")
async def logout(
    user: UserContext = Depends(get_current_user),
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> Dict[str, str]:
    """
    Logout current user.

    This endpoint signs out the user from Supabase Auth.
    """
    try:
        auth_handler.supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_request: TokenRefreshRequest,
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> AuthResponse:
    """
    Refresh JWT token using refresh token.
    """
    try:
        response = auth_handler.supabase.auth.refresh_session(
            refresh_request.refresh_token
        )

        if response.session:
            # Validate the new token
            user_context = await auth_handler.validate_token(
                response.session.access_token
            )

            return AuthResponse(
                success=True,
                user=user_context,
                token=response.session.access_token,
                error=None,
            )
        else:
            return AuthResponse(
                success=False, user=None, token=None, error="Token refresh failed"
            )

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return AuthResponse(
            success=False, user=None, token=None, error="Token refresh failed"
        )


@router.post("/reset-password")
async def reset_password(
    reset_request: PasswordResetRequest,
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> Dict[str, str]:
    """
    Send password reset email to user.
    """
    try:
        auth_handler.supabase.auth.reset_password_email(reset_request.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.post("/update-password")
async def update_password(
    password_update: PasswordUpdateRequest,
    user: UserContext = Depends(get_current_user),
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> Dict[str, str]:
    """
    Update user password.
    """
    try:
        # First verify current password by attempting to sign in
        verify_response = auth_handler.supabase.auth.sign_in_with_password(
            {"email": user.email, "password": password_update.current_password}
        )

        if not verify_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Update password
        auth_handler.supabase.auth.update_user(
            {"password": password_update.new_password}
        )

        return {"message": "Password updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password update failed",
        )


@router.get("/me", response_model=UserContext)
async def get_current_user_info(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """
    Get current authenticated user information.
    """
    return user


@router.put("/profile")
async def update_profile(
    profile_update: UserProfileUpdate,
    user: UserContext = Depends(get_current_user),
    auth_handler: SupabaseJWTAuth = Depends(get_auth_handler),
) -> Dict[str, str]:
    """
    Update user profile information.
    """
    try:
        # Prepare update data
        update_data = {}
        if profile_update.first_name is not None:
            update_data["first_name"] = profile_update.first_name
        if profile_update.last_name is not None:
            update_data["last_name"] = profile_update.last_name
        if profile_update.phone is not None:
            update_data["phone"] = profile_update.phone

        if update_data:
            # Update user metadata in Supabase
            auth_handler.supabase.auth.update_user({"data": update_data})

            # Also update in users table if it exists
            try:
                auth_handler.supabase.table("users").update(update_data).eq(
                    "id", user.user_id
                ).execute()
            except Exception as e:
                logger.warning(f"Could not update users table: {str(e)}")

        return {"message": "Profile updated successfully"}

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@router.get("/permissions")
async def get_user_permissions(
    user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user's permissions and role information.
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role.value,
        "permissions": user.permissions,
        "authenticated": user.authenticated,
    }


@router.post("/verify-token")
async def verify_token(
    request: Request, auth_handler: SupabaseJWTAuth = Depends(get_auth_handler)
) -> Dict[str, Any]:
    """
    Verify JWT token validity.

    This endpoint can be used by other services to verify token validity.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.split(" ")[1]

    try:
        user_context = await auth_handler.validate_token(token)
        return {
            "valid": True,
            "user_id": user_context.user_id,
            "email": user_context.email,
            "role": user_context.role.value,
            "permissions": user_context.permissions,
        }
    except AuthenticationError as e:
        return {"valid": False, "error": str(e)}
