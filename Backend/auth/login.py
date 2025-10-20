from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from auth.auth import TOKEN_EXPIRE_DAYS, create_access_token, verify_password
from config.config import get_db_connection, get_db_cursor, release_db_connection


router = APIRouter(
    tags=["login_route"],
    responses={404: {"description": "Not found"}}
)
templates = Jinja2Templates(directory="../static/templates")

@router.get("/login")
@router.get("/login_page")
def login_page(request: Request): 
    response = templates.TemplateResponse("login.html", {"request": request})
    response.delete_cookie("login_error")
    return response

@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    try:
        cursor.execute("SELECT id, email, password_hash, role, full_name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or not verify_password(password, user[2]):
            response = RedirectResponse(url="/login_page", status_code=303)
            response.set_cookie("login_error", "Wrong email or password", max_age=5)
            return response

        user_id, email, password_hash, role, full_name = user
        access_token = create_access_token({
            "sub": email,
            "role": role,
            "full_name": full_name,
            "user_id": user_id
        })

        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(
            "token", 
            access_token, 
            httponly=True, 
            #secure=True,  # Enable in production with HTTPS
            secure=False,
            max_age=TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Expires in 30 days
            samesite='lax'
        )
        return response
    finally:
        release_db_connection(conn)