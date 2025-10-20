# company_router.py
import re
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import cloudinary.uploader
import logging
from typing import List, Optional
from config.config import get_db_connection, get_db_cursor, release_db_connection
from auth.auth import get_current_user

# Initialize router without prefix since we want exact paths
router = APIRouter(
    tags=["company"],
    responses={404: {"description": "Not found"}}
)

# Setup logging
logger = logging.getLogger(__name__)

# Templates setup
templates = Jinja2Templates(directory="../static/templates")

def get_db():
    """Dependency to get DB connection"""
    conn = get_db_connection()
    try:
        cursor = get_db_cursor(conn)
        yield cursor
    finally:
        release_db_connection(conn)

def format_target_audience(age_groups: Optional[str], audience_types: Optional[str], 
                         business_types: Optional[str], geographics: Optional[str]) -> str:
    """Helper to format the target audience display"""
    parts = []
    if age_groups:
        parts.append(f"Age Groups: {age_groups}")
    if audience_types:
        parts.append(f"Types: {audience_types}")
    if business_types:
        parts.append(f"Businesses: {business_types}")
    if geographics:
        parts.append(f"Geographics: {geographics}")
    return " | ".join(parts) if parts else "Not specified"

# ===== Original Path Routes =====

@router.get("/Company_form", response_class=HTMLResponse)
def company_form(
    request: Request, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Display the company information form with original /Company_form path"""
    try:
        # Get pending company name from cookie
        company_name = request.cookies.get("pending_company_name", "")
        company_website = request.cookies.get("pending_company_website", "")  # Get website from cookie
       
        # Fetch most recent company name from database
        cursor.execute("""
            SELECT name, website
            FROM companies
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user["user_id"],))
        
        company_result = cursor.fetchone()
        db_company_name = company_result[0] if company_result else "New Company"
        db_company_website = company_result[1] if company_result and company_result[1] else ""
        
        # Use pending company name from cookie if available, otherwise use DB name
        display_company_name = company_name or db_company_name
        display_company_website = company_website or db_company_website
       
        return templates.TemplateResponse(
            "info_form.html", 
            {
                "request": request, 
                "user": user,
                "company_name": display_company_name,
                "company_website": display_company_website  # Pass to template
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading company form: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/company/{company_id}", response_class=HTMLResponse)
def company_details(
    request: Request, 
    company_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Display company details page"""
    try:
        # Fetch company details
        cursor.execute(
            """
            SELECT id, user_id, name, slogan, description, website,phone_number,
                   products, services, marketing_goals,
                   target_age_groups, target_audience_types, target_business_types,
                   target_geographics, preferred_platforms, special_events, 
                   marketing_challenges, brand_tone, monthly_budget, logo_url, created_at
            FROM companies 
            WHERE id = %s AND user_id = %s
            """,
            (company_id, user["user_id"])
        )
        company = cursor.fetchone()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Fetch approved strategy
        cursor.execute(
            """
            SELECT id, content, created_at FROM strategies 
            WHERE company_id = %s AND status = 'approved'
            LIMIT 1
            """,
            (company_id,)
        )
        approved_strategy = cursor.fetchone()
        
        # Count strategies - ensure we get 0 if no results
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count
            FROM strategies 
            WHERE company_id = %s
            """,
            (company_id,)
        )
        counts = cursor.fetchone()
        
        # Handle case where counts might be None
        total_count = counts[0] or 0
        approved_count = counts[1] or 0
        archived_count = total_count - approved_count
        
        # Format company data
        company_dict = {
            "id": company[0],
            "name": company[2],
            "slogan": company[3] or "Not specified",
            "description": company[4] or "Not provided",
            "website": company[5] or "Not provided",  # Add website
            "phone_number": company[6] or "Not provided",  # Add phone number
            "products": company[7] or "None listed",
            "services": company[8] or "None listed",
            "marketing_goals": company[9] or "Not specified",
            "target_audience": format_target_audience(
                company[10], company[11], company[12], company[13]
            ),
            "preferred_platforms": company[14] or "Not specified",
            "special_events": company[15] or "None planned",
            "marketing_challenges": company[16] or "None specified",
            "brand_tone": company[17] or "Not defined",
            "monthly_budget": company[18] or "Not specified",
            "logo_url": company[19],
            "created_at": company[20].strftime("%Y-%m-%d")
        }
        
        # Format approved strategy if exists
        approved_strategy_dict = None
        if approved_strategy:
            approved_strategy_dict = {
                "id": approved_strategy[0],
                "content": approved_strategy[1],
                "created_at": approved_strategy[2].strftime("%Y-%m-%d %H:%M")
            }
        
        return templates.TemplateResponse("company_details.html", {
            "request": request, 
            "user": user, 
            "company": company_dict,
            "approved_strategy": approved_strategy_dict,
            "strategy_counts": {
                "total": total_count,
                "approved": approved_count,
                "archived": archived_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching company details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/edit_company/{company_id}", response_class=HTMLResponse)
def edit_company_form(
    request: Request, 
    company_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Display edit form with original /edit_company/{id} path"""
    try:
        cursor.execute(
            """
            SELECT id, name, slogan, description, website, phone_number,
                   products, services, 
                   marketing_goals, target_age_groups, 
                   target_audience_types, target_business_types,
                   target_geographics, preferred_platforms, 
                   special_events, brand_tone, monthly_budget, 
                   marketing_challenges, logo_url
            FROM companies 
            WHERE id = %s AND user_id = %s
            """,
            (company_id, user["user_id"])
        )
        company = cursor.fetchone()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        company_dict = {
            "id": company[0],
            "name": company[1],
            "slogan": company[2],
            "description": company[3],
            "website": company[4],  # Add website
            "phone_number": company[5],
            "products": company[6],
            "services": company[7],
            "marketing_goals": company[8],
            "target_age_groups": company[9],
            "target_audience_types": company[10],
            "target_business_types": company[11],
            "target_geographics": company[12],
            "preferred_platforms": company[13],
            "special_events": company[14],
            "brand_tone": company[15],
            "monthly_budget": company[16],
            "marketing_challenges": company[17],
            "logo_url": company[18]
        }
        
        return templates.TemplateResponse(
            "edit_company.html", 
            {
                "request": request, 
                "user": user, 
                "company": company_dict
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching company for edit: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/submit_company")
def submit_company(
    request: Request,
    slogan: str = Form(""),
    description: str = Form(""),
    website: str = Form(""),  # Add website parameter
    phone_number: str = Form(""),  # Add phone number parameter
    products: str = Form(...),
    services: str = Form(...),
    channels: List[str] = Form([]),
    goals: List[str] = Form([]),
    target_age: List[str] = Form([]),
    target_type: List[str] = Form([]),
    target_business: List[str] = Form([]),
    target_geographic: List[str] = Form([]), 
    special_events: List[str] = Form([]),
    challenges: List[str] = Form([]),
    brand_tone: str = Form(...),
    budget: str = Form(...),
    logo: UploadFile = File(None),
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Submit company with original /submit_company path"""
    try: 
        company_name = request.cookies.get("pending_company_name")
        company_website = request.cookies.get("pending_company_website", "")  # Get website from cookie
        company_phone = request.cookies.get("pending_company_phone", "")  # Get phone from cookie
        
        if not company_name:
            raise HTTPException(status_code=400, detail="Company name missing")

        # Validate website format
        if website and not validate_website(website):
            raise HTTPException(status_code=400, detail="Invalid website URL format")
                                
        # Validate phone number format (optional)
        if phone_number and not validate_phone(phone_number):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
                                
        # Use the form value if provided, otherwise use the cookie value
        final_website = website or company_website
        final_phone = phone_number or company_phone
        if final_phone:
            # Remove all spaces, parentheses, dashes, dots - keep only digits and +
            final_phone = re.sub(r'[^\d+]', '', final_phone)

        
        logo_url = None
        if logo and logo.filename:
            try:
                upload_result = cloudinary.uploader.upload(
                    logo.file,
                    folder="company_logos"
                )
                logo_url = upload_result['secure_url']
            except Exception as e:
                logger.error(f"Error uploading logo: {str(e)}")
                raise HTTPException(status_code=500, detail="Error uploading logo")

        cursor.execute(
            """
            INSERT INTO companies (
                user_id, name, slogan, description, website,phone_number,
                products, services,
                target_age_groups, target_audience_types, target_business_types,
                target_geographics, preferred_platforms, marketing_goals,
                special_events, marketing_challenges,
                brand_tone, monthly_budget, logo_url
            ) VALUES (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user["user_id"], company_name, slogan, description, final_website,final_phone,
                products, services,
                ",".join(target_age), ",".join(target_type),
                ",".join(target_business), ",".join(target_geographic),
                ",".join(channels), ",".join(goals),
                ",".join(special_events), ",".join(challenges),
                brand_tone, budget, logo_url
            )
        )
        company_id = cursor.fetchone()[0]
        cursor.connection.commit()
        
        response = RedirectResponse(url=f"/company/{company_id}", status_code=303)
        response.delete_cookie("pending_company_name")
        response.delete_cookie("pending_company_website")  # Clear website cookie
        response.delete_cookie("pending_company_phone")  # Clear phone cookie
        return response
        
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/update_company/{company_id}")
@router.put("/update_company/{company_id}")
def update_company(
    company_id: int,
    request: Request,
    name: str = Form(...),  # Add name parameter
    slogan: str = Form(""),
    description: str = Form(""),
    website: str = Form(""),  # Add website parameter
    phone_number: str = Form(""),  # Add phone number parameter
    products: str = Form(...),
    services: str = Form(...),
    goals: List[str] = Form([]),
    target_age: List[str] = Form([]),
    target_type: List[str] = Form([]),
    target_business: List[str] = Form([]),
    target_geographic: List[str] = Form([]),
    channels: List[str] = Form([]),
    special_events: List[str] = Form([]),
    brand_tone: str = Form(...),
    budget: str = Form(...),
    challenges: List[str] = Form([]),
    logo: UploadFile = File(None),
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Update company with PUT method"""
    """Update company with original /update_company/{id} path"""
    try:
        # Validate website format
        if website and not validate_website(website):
            raise HTTPException(status_code=400, detail="Invalid website URL format")
        
        # Validate phone number format (optional)
        if phone_number and not validate_phone(phone_number):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        else:
            phone_number = re.sub(r'[^\d+]', '', phone_number)
        
        
        logo_url = None
        if logo and logo.filename:
            try: 
                upload_result = cloudinary.uploader.upload(
                    logo.file,
                    folder="company_logos"
                )
                logo_url = upload_result['secure_url']
            except Exception as e:
                logger.error(f"Error uploading logo: {str(e)}")
                raise HTTPException(status_code=500, detail="Error uploading logo")
        else:
            cursor.execute(
                "SELECT logo_url FROM companies WHERE id = %s",
                (company_id,)
            )
            logo_url = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE companies SET
                name = %s,
                slogan = %s,
                description = %s,
                website = %s,
                phone_number = %s,
                products = %s,
                services = %s,
                marketing_goals = %s,
                target_age_groups = %s,
                target_audience_types = %s,
                target_business_types = %s,
                target_geographics = %s,
                preferred_platforms = %s,
                special_events = %s,
                brand_tone = %s,
                monthly_budget = %s,
                marketing_challenges = %s,
                logo_url = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                name,  # Add name value
                slogan, description, website, phone_number, products, services,
                ",".join(goals), ",".join(target_age),
                ",".join(target_type), ",".join(target_business),
                ",".join(target_geographic), ",".join(channels),
                ",".join(special_events), brand_tone,
                budget, ",".join(challenges), logo_url,
                company_id, user["user_id"]
            )
        )
        cursor.connection.commit()
        
        return RedirectResponse(url=f"/company/{company_id}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/delete_company/{company_id}")
def delete_company(
    company_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_db)
):
    """Delete company with original /delete_company/{id} path"""
    try:
        cursor.execute(
            "SELECT id FROM companies WHERE id = %s AND user_id = %s",
            (company_id, user["user_id"])
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Company not found")
        
        cursor.execute(
            "DELETE FROM companies WHERE id = %s",
            (company_id,)
        )
        cursor.connection.commit()
        
        return RedirectResponse(url="/home", status_code=303)
        
    except Exception as e:
        logger.error(f"Error deleting company: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
        
# Add this function to the company.py file (before the routes that use it)
def validate_website(url):
    """Validate website URL format"""
    if not url:
        return True  # Empty is allowed
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Z0-9][A-Z0-9_-]*)(\.[A-Z0-9][A-Z0-9_-]*)+)'  # domain
        r'(:[0-9]{1,5})?'  # optional port
        r'(/.*)?$',  # optional path
        re.IGNORECASE
    )
    
    # LinkedIn pattern
    linkedin_pattern = re.compile(
        r'^(https?://)?(www\.)?linkedin\.com/.*',
        re.IGNORECASE
    )
    
    return bool(url_pattern.match(url)) or bool(linkedin_pattern.match(url))        

# Add phone number validation function
def validate_phone(phone_number):
    """Validate phone number format (allows spaces, parentheses, dashes, dots)"""
    if not phone_number:
        return True  # Empty is allowed
    
    # Flexible phone validation - allows various formatting characters
    phone_pattern = re.compile(
        r'^\+?[0-9]{1,4}?[-.\s()]*[0-9]{1,4}?[-.\s()]*[0-9]{1,4}[-.\s()]*[0-9]{1,4}[-.\s()]*[0-9]{1,9}$'
    )
    
    return bool(phone_pattern.match(phone_number))