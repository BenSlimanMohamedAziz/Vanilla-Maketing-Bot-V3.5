# imports

import json
import random
import re
import shutil
import tempfile
import time
import traceback
from fastapi import FastAPI, File, HTTPException, Depends, Form, Query, Request, UploadFile
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import psycopg2
import requests
from urllib3 import Retry

# Auth
from auth.login import router as login_router
from auth.signup import router as signup_router
from auth.logout import router as logout_router
from auth.auth import get_current_user

from components.users.user_settings import router as settings_router

# DB & settings Import
from config.config import get_db_connection, get_db_cursor, release_db_connection,settings

# Company router 
from components.company.company_router import router as company_router

# Strategies router
from components.strategies.strategy_routes.strategy_router import router as strategy_router, limiter

# Launch Strategies router
from components.strategies.launch_strategy_routes.strategy_execution_fncs import router as strategy_execution_router
# Import the content creation router
from components.strategies.launch_strategy_routes.auto_content_creaction_utils import router as auto_content_creation_router

# Import the content management router
from components.strategies.launch_strategy_routes.content_management_routes import router as content_management_router




# Insights 
from components.insightsBIData.insights_platforms_data import (
    get_facebook_analytics, 
    get_instagram_analytics,
    get_linkedin_analytics
)


# For web scraping 
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import asyncio
import logging


# For Img Gen 
# === Image Generation ===
from fastapi.responses import JSONResponse
from together import Together
import uuid


# For Posting / Uploading Cloud : 
from components.strategies.launch_strategy_routes.cloudinary_utils import (
    upload_image_to_cloudinary, 
    upload_video_to_cloudinary
) 

# === App Setup ===
app = FastAPI()


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount the static directory
app.mount("/static", StaticFiles(directory="../static"), name="static")
#Front Templates
templates = Jinja2Templates(directory="../static/templates")


# API keys and endpoints LLAMA
LLAMA_API_KEY = settings.LLAMA_API_KEY
LLAMA_API_URL = settings.LLAMA_API_URL

#For Img Gen : 
# Initialize Together client
together_client = Together(api_key=LLAMA_API_KEY)

# Ensure the image directory exists
os.makedirs("../static/imgs/generated_campagin_img", exist_ok=True)


# API keys and endpoints Groq Model and tools
GROQ_API_KEY = settings.GROQ_API_KEY_1
TAVILY_API_KEY = settings.TAVILY_API_KEY_2
TAVILY_API_URL = settings.TAVILY_API_URL
FIRECRAWL_API_KEY= settings.FIRECRAWL_API_KEY_2
FIRECRAWL_API_URL= settings.FIRECRAWL_API_KEY_2


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DB Setup ===
conn = get_db_connection()
cursor = get_db_cursor(conn)

# === Auth ===
# Include auth routers
app.include_router(login_router)
app.include_router(signup_router)
app.include_router(logout_router)

# Include the company router
app.include_router(company_router) 

# Include Strategies router
app.include_router(strategy_router)
app.state.limiter = limiter 
# Include Launch Strategies router
app.include_router(strategy_execution_router) 
# Include auto content creation router
app.include_router(auto_content_creation_router)

# Include content management router
app.include_router(content_management_router)

# Include the settings router
app.include_router(settings_router)


# Default page
@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Home - Dashboard routes
@app.get("/home", response_class=HTMLResponse)
def home(request: Request, user: dict = Depends(get_current_user)):
    # Fetch companies with accurate strategy counts
    cursor.execute("""
        SELECT 
            c.id, 
            c.name, 
            c.created_at,
            c.monthly_budget,
            COUNT(s.id) as strategy_count,
            SUM(CASE WHEN s.status = 'approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN s.status = 'archived' THEN 1 ELSE 0 END) as archived_count,
            SUM(CASE WHEN s.status NOT IN ('approved', 'archived') THEN 1 ELSE 0 END) as other_count
        FROM companies c
        LEFT JOIN strategies s ON c.id = s.company_id
        WHERE c.user_id = %s
        GROUP BY c.id, c.name, c.created_at, c.monthly_budget
        ORDER BY c.created_at DESC
    """, (user["user_id"],))
    
    companies = []
    total_strategies = 0
    total_approved = 0
    total_archived = 0
    
    for row in cursor.fetchall():
        monthly_budget = float(row[3]) if row[3] is not None else 0
        strategy_count = row[4] or 0
        approved_count = row[5] or 0
        archived_count = row[6] or 0
        
        total_strategies += strategy_count
        total_approved += approved_count
        total_archived = total_strategies-total_approved
        
        companies.append({
            "id": row[0],
            "name": row[1],
            "created_at": row[2].strftime("%Y-%m-%d"),
            "monthly_budget": monthly_budget,
            "strategy_count": strategy_count,
            "approved_count": approved_count,
            "archived_count": archived_count
        })
    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "companies": companies,
        "total_strategies": total_strategies,
        "total_approved": total_approved,
        "total_archived": total_archived,
        "total_budget": sum(company['monthly_budget'] for company in companies)
    })



#Insights routes :
@app.get("/get_facebook_analytics")
async def get_facebook_analytics_endpoint(
    days: int = Query(default=30, ge=1, le=90),
    user: dict = Depends(get_current_user)
):
    return await get_facebook_analytics(user["user_id"], cursor, days)

@app.get("/get_instagram_analytics")
async def get_instagram_analytics_endpoint(
    days: int = Query(default=14, ge=1, le=90),
    user: dict = Depends(get_current_user)
):
    return await get_instagram_analytics(user["user_id"], cursor, days)

@app.get("/get_linkedin_analytics")
async def get_linkedin_analytics_endpoint(
    days: int = Query(default=30, ge=1, le=90),
    user: dict = Depends(get_current_user)
):
    return await get_linkedin_analytics(user["user_id"], days)

