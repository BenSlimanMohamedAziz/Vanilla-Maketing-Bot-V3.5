# logout.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from auth.auth import get_current_user

router = APIRouter(
    tags=["logout_route"],
    responses={404: {"description": "Not found"}}
)


@router.get("/logout")
def logout(request: Request):
    """
    Handle user logout by:
    1. Deleting the authentication token cookie
    2. Clearing any session-related cookies
    3. Redirecting to login page
    """
    try:
        # Get current user (just to verify they were logged in)
        # This will automatically handle token verification
        _ = get_current_user(request)
        
        response = RedirectResponse(url="/login_page", status_code=303)
        
        # Clear the auth token
        response.delete_cookie(
            "token",
            httponly=True,
            secure=True,  # Should match your login cookie settings
            samesite='lax'
        )
        
        # Clear any other session-related cookies if needed
        response.delete_cookie("pending_company_name")
        response.delete_cookie("login_error")
        
        return response
        
    except Exception:
        # Even if token was invalid, still proceed with logout
        response = RedirectResponse(url="/login_page", status_code=303)
        response.delete_cookie("token")
        return response