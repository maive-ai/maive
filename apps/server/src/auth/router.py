"""
Auth router with authentication and authorization endpoints.

This module contains all the API endpoints for user authentication,
authorization, and user management.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from src.auth import schemas
from src.auth.config import get_auth_settings
from src.auth.constants import CookieNames, TimeInSeconds
from src.auth.dependencies import (
    get_auth_provider_dependency,
    get_current_user,
)
from src.config import get_client_base_url

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signout")
async def sign_out(
    response: Response,
    request: Request,
    auth_provider: Any = Depends(get_auth_provider_dependency),
    current_user: Any = Depends(get_current_user),
) -> Response:
    """
    Sign out the current user.

    Invalidates the current user's session and clears cookies.
    """
    # Get access token from cookies
    session_token = request.cookies.get(CookieNames.SESSION_TOKEN.value)

    if session_token:
        try:
            await auth_provider.sign_out(session_token)
        except Exception:
            # Continue with logout even if sign_out fails
            pass

    # Clear session cookies
    response.delete_cookie(CookieNames.SESSION_TOKEN.value)
    response.delete_cookie(CookieNames.REFRESH_TOKEN.value)

    # Return 204 No Content (no redirect)
    return Response(status_code=204)


@router.get("/me", response_model=schemas.User)
async def get_current_user_info(
    current_user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    """
    Get current user information.

    Returns the profile information of the currently authenticated user.
    """
    return current_user


@router.get("/callback")
async def oauth_callback(
    code: str | None = None,
    error: str | None = None,
    auth_provider: Any = Depends(get_auth_provider_dependency),
) -> RedirectResponse:
    """
    OAuth2 callback endpoint for Cognito authentication.

    Exchanges authorization code for tokens and redirects to frontend.
    """
    if error:
        client_base_url = get_client_base_url()
        return RedirectResponse(
            url=f"{client_base_url}/auth/error?message={error}", status_code=302
        )

    if not code:
        client_base_url = get_client_base_url()
        return RedirectResponse(
            url=f"{client_base_url}/auth/error?message=No authorization code provided",
            status_code=302,
        )

    try:
        # Exchange authorization code for tokens
        result = await auth_provider.exchange_code_for_tokens(code)

        if result.success and result.session:
            client_base_url = get_client_base_url()

            redirect_url = f"{client_base_url}/"

            redirect_response = RedirectResponse(url=redirect_url, status_code=302)

            # Get auth settings for cookie configuration
            auth_settings = get_auth_settings()

            # Set HTTP-only session cookies
            redirect_response.set_cookie(
                key=CookieNames.SESSION_TOKEN.value,
                value=result.session.access_token,
                httponly=auth_settings.cookie_httponly,
                secure=auth_settings.cookie_secure,
                samesite=auth_settings.cookie_samesite.value,
                max_age=TimeInSeconds.ONE_HOUR,
                domain=auth_settings.cookie_domain,
            )
            redirect_response.set_cookie(
                key=CookieNames.REFRESH_TOKEN.value,
                value=result.session.refresh_token,
                httponly=auth_settings.cookie_httponly,
                secure=auth_settings.cookie_secure,
                samesite=auth_settings.cookie_samesite.value,
                max_age=TimeInSeconds.THIRTY_DAYS,
                domain=auth_settings.cookie_domain,
            )

            return redirect_response
        else:
            client_base_url = get_client_base_url()
            return RedirectResponse(
                url=f"{client_base_url}/auth/error?message={result.error}",
                status_code=302,
            )
    except Exception:
        client_base_url = get_client_base_url()
        return RedirectResponse(
            url=f"{client_base_url}/auth/error?message=Authentication failed",
            status_code=302,
        )


@router.post("/refresh", response_model=schemas.AuthResponse)
async def refresh_token(
    response: Response,
    request: Request,
    auth_provider: Any = Depends(get_auth_provider_dependency),
) -> schemas.AuthResponse:
    """
    Refresh access token using refresh token.

    Uses the refresh token from cookies to get a new access token.
    """
    refresh_token = request.cookies.get(CookieNames.REFRESH_TOKEN.value)

    if not refresh_token:
        return schemas.AuthResponse(
            success=False,
            session=None,
            error="No refresh token found",
        )

    try:
        result = await auth_provider.refresh_session(refresh_token)

        if result.success and result.session:
            # Get auth settings for cookie configuration
            auth_settings = get_auth_settings()

            # Update session cookies
            response.set_cookie(
                key=CookieNames.SESSION_TOKEN.value,
                value=result.session.access_token,
                httponly=auth_settings.cookie_httponly,
                secure=auth_settings.cookie_secure,
                samesite=auth_settings.cookie_samesite.value,
                max_age=TimeInSeconds.ONE_HOUR,
                domain=auth_settings.cookie_domain,
            )
            response.set_cookie(
                key=CookieNames.REFRESH_TOKEN.value,
                value=result.session.refresh_token,
                httponly=auth_settings.cookie_httponly,
                secure=auth_settings.cookie_secure,
                samesite=auth_settings.cookie_samesite.value,
                max_age=TimeInSeconds.THIRTY_DAYS,
                domain=auth_settings.cookie_domain,
            )

        return schemas.AuthResponse(
            success=result.success,
            session=result.session.model_dump() if result.session else None,
            error=result.error,
        )
    except Exception as e:
        return schemas.AuthResponse(
            success=False,
            session=None,
            error=f"Failed to refresh token: {str(e)}",
        )
