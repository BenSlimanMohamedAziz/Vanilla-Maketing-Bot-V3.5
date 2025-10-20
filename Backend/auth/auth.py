from pathlib import Path
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os


# Get the directory where this file (auth.py) is located
current_dir = Path(__file__).resolve().parent
# Navigate to the config directory and get the .env
env_path = current_dir.parent / "config" / ".env"

# Load environment variables
load_dotenv(dotenv_path=env_path)

router = APIRouter(
    tags=["auth_jwt_security"],
    responses={404: {"description": "Not found"}}
)


# Security settings from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Default to HS256 if not set
TOKEN_EXPIRE_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", 30))  # Default to 30 if not set

# Validate that SECRET_KEY was loaded
if not SECRET_KEY: 
    raise ValueError("SECRET_KEY not found in environment variables")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """Create a long-lived access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Includes: sub, user_id, role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Token missing in cookie")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "email": payload.get("sub"),
            "full_name": payload.get("full_name"),
            "user_id": payload.get("user_id")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def logout():
    response = RedirectResponse(url="/login_page")
    response.delete_cookie("token")
    return response    
