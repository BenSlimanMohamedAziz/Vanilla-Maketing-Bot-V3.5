# Imports
from bs4 import BeautifulSoup
from fastapi import APIRouter, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from imageio import imiter
from slowapi import Limiter
from slowapi.util import get_remote_address
import psycopg2
import requests
from auth.auth import get_current_user
from config.config import get_db_cursor, get_db_connection, release_db_connection
import asyncio
import logging
from datetime import datetime
import json

#---------------------------------------------------------------------------------------

# Logo description
from components.helpers.image_analyzer import get_logo_description 

#---------------------------------------------------------------------------------------

# Import strategy generation functions
from components.strategies.prompts.marketing_calendar import generate_marketing_calendar
from components.strategies.prompts.digital_marketing import generate_platform_strategies,save_content_items_to_db
from components.strategies.prompts.executive_summary import generate_executive_summary
from components.strategies.prompts.maketing_trends_advices_tips import generate_advices_and_tips
from components.strategies.prompts.influencers_emails_marketing import generate_influencer_recommendations,extract_and_save_influencers
from components.strategies.prompts.marketing_budget_plan import generate_budget_plan
from components.strategies.prompts.events_marketing import generate_event_strategy

#---------------------------------------------------------------------------------------

# Import scraping helper
from components.strategies.strategy_routes.web_scraping_helper import scrape_events_firecrawl

#---------------------------------------------------------------------------------------


# Initialize router
router = APIRouter(
    tags=["strategy"],
    responses={404: {"description": "Not found"}}
)

# Initialize templates
templates = Jinja2Templates(directory="../static/templates")

# Set up logging
logger = logging.getLogger(__name__)

# Dependency to get database cursor
async def get_cursor():
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    try:
        yield cursor
    finally:
        release_db_connection(conn)
        
# === DB Setup ===
conn = get_db_connection()
cursor = get_db_cursor(conn)

#---------------------------------------------------------------------------------------
   
   
#--------------------------------- Helper Functions --------------------------------------------#

# Event Scraping helper for strategy   
# Web Scraping
async def scrape_events_data(company_id: int):
    """Scrape events Data from website and store in database"""
    url = "https://www.discovertunisia.com/en/evenements"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logger.info(f"Starting event scraping for company {company_id}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        event_rows = soup.select('div.view-content div.views-row')
        
        if not event_rows:
            logger.warning("No events found on the page")
            return 0
            
        events_added = 0
        today = datetime.now().date()
        
        for row in event_rows:
            try:
                # Extract event details
                title = row.select_one('div.field-title a')
                date_day = row.select_one('span.date-day')
                date_month = row.select_one('span.date-month')
                image = row.select_one('img[data-src]')
                link = row.select_one('div.field-title a')
                read_more = row.select_one('div.field-link-readmore a')
                
                if not (title and link):
                    continue
                    
                # Parse the date
                event_date = None
                day = date_day.get_text(strip=True) if date_day else None
                month = date_month.get_text(strip=True) if date_month else None
                
                month_map = {
                    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                }
                
                if day and month and month.upper() in month_map:
                    current_year = today.year
                    month_num = month_map[month.upper()]
                    try:
                        event_date = datetime(current_year, month_num, int(day)).date()
                        # If event date is in past, skip it
                        if event_date < today:
                            continue
                    except ValueError:
                        continue
                
                # Insert event if it doesn't exist
                cursor.execute("""
                    INSERT INTO scraped_events (
                        company_id, title, event_date, date_day, date_month, 
                        image_url, event_url, read_more_url
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, event_url) DO NOTHING
                """, (
                    company_id,
                    title.get_text(strip=True),
                    event_date,
                    day,
                    month,
                    image['data-src'] if image else None,
                    'https://www.discovertunisia.com' + link['href'],
                    'https://www.discovertunisia.com' + read_more['href'] if read_more else None
                ))
                
                if cursor.rowcount > 0:
                    events_added += 1
                    
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue
                
        conn.commit()
        logger.info(f"Added {events_added} new events for company {company_id}")
        return events_added
        
    except Exception as e:
        logger.error(f"Error scraping events: {e}")
        return 0  
     
    
# Get best 4 events for strategy
async def get_relevant_events(company_id: int, limit: int = 4) -> list:
    """Get relevant upcoming events for a company"""
    today = datetime.now().date()
    cursor.execute("""
        SELECT title, event_date, event_url
        FROM scraped_events
        WHERE company_id = %s AND (event_date >= %s OR event_date IS NULL)
        ORDER BY event_date ASC
        LIMIT %s
    """, (company_id, today, limit))
    
    events = []
    for title, event_date, event_url in cursor.fetchall():
        date_str = event_date.strftime("%Y-%m-%d") if event_date else "Date not specified"
        events.append({
            "title": title,
            "date": date_str,
            "url": event_url
        })
    
    return events


# Format events
async def format_events_text(events):
    if not events:
        return "No upcoming events identified"
    text = "\nUPCOMING EVENTS:\n"
    for event in events:
        text += f"- {event['title']} ({event['date']}): Participation recommendations...\n"
    return text


# Extract image prompts -> Image gen model
def extract_image_prompts(content):
    """Extract image prompts from strategy content"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    prompts = {}
    
    prompt_section = soup.find('section', class_='image-prompts')
    if prompt_section:
        for card in prompt_section.find_all('div', class_='prompt-card'):
            prompt_type = card.find('h3').get_text(strip=True)
            prompt_text = card.find('code').get_text(strip=True)
            prompts[prompt_type] = prompt_text
    
    return prompts    

#--------------------------------- End Helper Functions --------------------------------------------#  
    
    
#---------------------------------------------------------------------------------------------# 

#--------------------------------- Main Functions --------------------------------------------# 


# Var for gen progress
generation_progress = {}

# SSE endpoint
@router.get("/strategy_progress/{company_id}")
async def strategy_progress(
    company_id: int,
    user: dict = Depends(get_current_user)
):
    async def event_generator():
        try:
            while True:
                if company_id in generation_progress:
                    progress_data = generation_progress[company_id]
                    
                    if progress_data.get('status') == 'completed':
                        yield f"event: complete\ndata: {json.dumps(progress_data)}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps(progress_data)}\n\n"
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Status check endpoint (fallback)
@router.get("/check_strategy_status/{company_id}")
async def check_strategy_status(
    company_id: int,
    user: dict = Depends(get_current_user),
    cursor = Depends(get_cursor)
):
    if company_id in generation_progress:
        return generation_progress[company_id]
    
    # Check database for completed strategy
    cursor.execute("""
        SELECT id FROM strategies 
        WHERE company_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (company_id,))
    
    result = cursor.fetchone()
    if result:
        return {"status": "completed", "strategy_id": result[0]}
    
    return {"status": "unknown"}


# New Strategy gen endpoint
@router.post("/generate_strategy/{company_id}")
async def generate_strategy(
    company_id: int, 
    user: dict = Depends(get_current_user)
):
    
    # Initialize progress tracking
    generation_progress[company_id] = {
        "status": "generating",
        "progress": 0,
        "currentStep": "Initializing..."
    }
    
    ''' Old- backup
    # Web Scraping for events
    scrape_task = asyncio.create_task(scrape_events_data(company_id))
    relevant_events = await get_relevant_events(company_id)
    
    # Format events text
    events_text = await format_events_text(relevant_events)
    
    try:
        await asyncio.wait_for(scrape_task, timeout=10) 
        relevant_events = await get_relevant_events(company_id)
    except asyncio.TimeoutError:
        logger.warning("Event scraping timed out, using existing events")
    '''
    
    # Web Scraping for events
    scrape_task = asyncio.create_task(scrape_events_data(company_id))
    scrape_task_firecrawl = asyncio.create_task(scrape_events_firecrawl(company_id))
   
    try:
        await asyncio.wait_for(
        asyncio.gather(scrape_task, scrape_task_firecrawl, return_exceptions=True),
        timeout=10
    )
    except asyncio.TimeoutError:
        logger.warning("Event scraping timed out, using existing events")
        
    relevant_events = await get_relevant_events(company_id)
    # Format events text
    events_text = await format_events_text(relevant_events)
    
    try:
        # Get company data
        cursor.execute("""
            SELECT id, name, slogan, description, website, phone_number, products, services,
                   marketing_goals, target_age_groups, target_audience_types,
                   target_business_types, target_geographics, preferred_platforms, 
                   special_events, brand_tone, monthly_budget, logo_url
            FROM companies WHERE id = %s AND user_id = %s
        """, (company_id, user["user_id"]))
        
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        cursor.execute("""
            SELECT title, event_date, event_url
            FROM scraped_events
            WHERE company_id = %s
            ORDER BY event_date ASC
        """, (company_id,))  # 👈 Notice the comma after company_id (tuple)

        # ✅ Fetch all rows
        events_rows = cursor.fetchall()

        # ✅ Convert to JSON-like list of dicts
        events_list = [
            {
                "title": row[0],
                "event_date": row[1].strftime("%m/%d/%Y") if row[1] else None,  # formatted date
                "event_url": row[2]
            }
            for row in events_rows
        ]
                    
        company_data = {
            'id': company[0],
            'name': company[1],
            'slogan': company[2],
            'description': company[3],
            'website': company[4],
            'phone_number': company[5],
            'products': company[6],
            'services': company[7],
            'marketing_goals': company[8],
            'target_age_groups': company[9],
            'target_audience_types': company[10],
            'target_business_types': company[11],
            'target_geographics': company[12],
            'preferred_platforms': company[13],
            'special_events': company[14],
            'brand_tone': company[15],
            'monthly_budget': company[16],
            'logo_url': company[17]
        }
        
        # Format target audience
        target_audience = f"""
        - Age Groups: {company_data.get('target_age_groups', 'Not specified')}
        - Audience Types: {company_data.get('target_audience_types', 'Not specified')}
        - Business Types: {company_data.get('target_business_types', 'Not specified')}
        - Geographic Targets: {company_data.get('target_geographics', 'Not specified')}
        """
        
        # Get additional data
        current_date = datetime.now()
        logo_description = get_logo_description(company_data['logo_url']) if company_data['logo_url'] else ""
        relevant_events = await get_relevant_events(company_id)
        
        # Update progress for each section
        async def update_progress(step, progress_pct):
            generation_progress[company_id] = {
                "status": "generating",
                "progress": progress_pct,
                "currentStep": step
            }
        
        # Generate each section
        logger.info("Generating executive summary")
        await update_progress("Generating Executive Summary", 10)
        executive_summary = await generate_executive_summary(company_data, current_date, logo_description)
        logger.info("Done executive summary")
        
        logger.info("Generating budget plan")
        await update_progress("Generating Budget Plan", 25)
        budget_plan = await generate_budget_plan(executive_summary, company_data, current_date, relevant_events)
        logger.info("Done budget plan")
        
        logger.info("Generating event marketing")
        await update_progress("Generating Event Marketing", 40)
        events_marketing = await generate_event_strategy(executive_summary, budget_plan, company_data, events_text, current_date, events_list)
        logger.info("Done event marketing")
        
        logger.info("Generating content calendar")
        await update_progress("Generating Content Calendar", 55)
        content_calendar = await generate_marketing_calendar(executive_summary, budget_plan, events_marketing, company_data, current_date, logo_description, company_id)
        logger.info("Done content calendar")
        
        logger.info("Generating influencer recommendations")
        await update_progress("Generating Influencer Recommendations", 70)
        influencer_section = await generate_influencer_recommendations(
            executive_summary,
            budget_plan,
            current_date,
            company_data,
            target_audience,
            company_data['products'],
            company_data['services']
        )
        logger.info("Done influencer recommendations")
        
        logger.info("Generating platform strategies")
        await update_progress("Generating Platform Strategies", 85)
        platform_strategies = await generate_platform_strategies(company_data, current_date, logo_description)
        logger.info("Done platform strategies")
        
        logger.info("Generating advice and tips")
        await update_progress("Generating Marketing Tips & Advice", 95)
        advices_tips = await generate_advices_and_tips(company_data, current_date, logo_description)
        logger.info("Done advice and tips")
        
        # Combine all sections
        full_strategy = f"""
        <div class="marketing-strategy">
            {executive_summary}
            {budget_plan}
            {content_calendar}
            {events_marketing}
            {influencer_section}
            {platform_strategies}
            {advices_tips}
        </div>
        """
        
        # Save to database
        cursor.execute("""
            INSERT INTO strategies (company_id, content, created_at, status)
            VALUES (%s, %s, NOW(), 'new')
            RETURNING id
        """, (company_id, full_strategy))
        
        strategy_id = cursor.fetchone()[0]
        conn.commit()
        
        # Mark as complete
        generation_progress[company_id] = {
            "status": "completed",
            "strategy_id": strategy_id,
            "progress": 100
        }
        
        # Return JSON instead of redirect
        return JSONResponse({
            "success": True,
            "strategy_id": strategy_id,
            "redirect_url": f"/strategy/{strategy_id}"
        })
        
    except Exception as e:
        logger.error(f"Strategy generation failed: {str(e)}")
        generation_progress[company_id] = {
            "status": "error",
            "error": str(e),
            "progress": 0
        }
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up after 5 minutes
        asyncio.create_task(cleanup_progress(company_id))


# Cleanup
async def cleanup_progress(company_id):
    await asyncio.sleep(300)
    if company_id in generation_progress:
        del generation_progress[company_id] 


'''
# Old Strategy generation
@router.post("/generate_strategy/{company_id}")
async def generate_strategy(
    company_id: int, 
    user: dict = Depends(get_current_user)
):
    
    # Web Scraping for events
    scrape_task = asyncio.create_task(scrape_events_data(company_id))
    relevant_events = get_relevant_events(company_id)
    
    # Format events text
    events_text = format_events_text(relevant_events)
    
    try:
        await asyncio.wait_for(scrape_task, timeout=10) 
        relevant_events = get_relevant_events(company_id)
    except asyncio.TimeoutError:
        logger.warning("Event scraping timed out, using existing events")
    
    try:
        # Get company data
        cursor.execute("""
            SELECT id, name, slogan, description, website, phone_number, products, services,
                   marketing_goals, target_age_groups, target_audience_types,
                   target_business_types, target_geographics, preferred_platforms, 
                   special_events, brand_tone, monthly_budget, logo_url
            FROM companies WHERE id = %s AND user_id = %s
        """, (company_id, user["user_id"]))
        
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        company_data = {
            'id': company[0],
            'name': company[1],
            'slogan': company[2],
            'description': company[3],
            'website': company[4],
            'phone_number': company[5],
            'products': company[6],
            'services': company[7],
            'marketing_goals': company[8],
            'target_age_groups': company[9],
            'target_audience_types': company[10],
            'target_business_types': company[11],
            'target_geographics': company[12],
            'preferred_platforms': company[13],
            'special_events': company[14],
            'brand_tone': company[15],
            'monthly_budget': company[16],
            'logo_url': company[17]
        }
        
        # Format target audience
        target_audience = f"""
        - Age Groups: {company_data.get('target_age_groups', 'Not specified')}
        - Audience Types: {company_data.get('target_audience_types', 'Not specified')}
        - Business Types: {company_data.get('target_business_types', 'Not specified')}
        - Geographic Targets: {company_data.get('target_geographics', 'Not specified')}
        """
        
        # Get additional data
        current_date = datetime.now()
        logo_description = get_logo_description(company_data['logo_url']) if company_data['logo_url'] else ""
        relevant_events = get_relevant_events(company_id)
        
        # Generate each section
        logger.info("Generating executive summary")
        executive_summary = await generate_executive_summary(company_data, current_date, logo_description)
        logger.info("Done executive summary")
        
        logger.info("Generating budget plan")
        budget_plan = await generate_budget_plan(company_data, current_date, relevant_events)
        logger.info("Done budget plan")
        
        logger.info("Generating event marketing")
        events_marketing = await generate_event_strategy(company_data, events_text, current_date)
        logger.info("Done event marketing")
        
        logger.info("Generating content calendar")
        content_calendar = await generate_marketing_calendar(company_data, current_date, logo_description, company_id)
        logger.info("Done content calendar")
        
        logger.info("Generating influencer recommendations")
        influencer_section = await generate_influencer_recommendations(
            company_data,
            target_audience,
            company_data['products'],
            company_data['services']
        )
        logger.info("Done influencer recommendations")
        
        logger.info("Generating platform strategies")
        platform_strategies = await generate_platform_strategies(company_data, current_date, logo_description)
        logger.info("Done platform strategies")
        
        logger.info("Generating advice and tips")
        advices_tips = await generate_advices_and_tips(company_data, current_date, logo_description)
        logger.info("Done advice and tips")
        
        # Combine all sections
        full_strategy = f"""
        <div class="marketing-strategy">
            {executive_summary}
            {budget_plan}
            {content_calendar}
            {events_marketing}
            {influencer_section}
            {platform_strategies}
            {advices_tips}
        </div>
        """
        
        # Save to database
        cursor.execute("""
            INSERT INTO strategies (company_id, content, created_at, status)
            VALUES (%s, %s, NOW(), 'new')
            RETURNING id
        """, (company_id, full_strategy))
        
        strategy_id = cursor.fetchone()[0]
        conn.commit()
        
        return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)
    
        #return {
        #    "redirect_url": f"/strategy/{strategy_id}"
        #}
        
    except Exception as e:
        logger.error(f"Strategy generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))    
'''    
#---------------------------------------------------------------------------------------

    
# Route for the loading page - generating new strategy
@router.get("/strategy/new/{company_id}", response_class=HTMLResponse)
async def new_strategy_page(
    request: Request, 
    company_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_cursor)
):
    # Check if company belongs to user
    cursor.execute("SELECT name FROM companies WHERE id = %s AND user_id = %s", (company_id, user["user_id"]))
    company = cursor.fetchone()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Pass company details for loading page
    return templates.TemplateResponse("strategy.html", {
        "request": request,
        "user": user,
        "company_id": company_id,
        "company_name": company[0],
        "should_generate": True
    })        
    
#---------------------------------------------------------------------------------------

# Route for viewing strategy
@router.get("/strategy/{strategy_id}", response_class=HTMLResponse)
async def view_strategy(
    request: Request, 
    strategy_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_cursor)
):
    cursor.execute("""
        SELECT s.id, s.content, s.created_at, s.status, s.approved_at, s.archived_at,
            c.id as company_id, c.name as company_name
        FROM strategies s
        JOIN companies c ON s.company_id = c.id
        WHERE s.id = %s AND c.user_id = %s
    """, (strategy_id, user["user_id"]))

    
    strategy = cursor.fetchone()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy_dict = {
        "id": strategy[0],
        "content": strategy[1], 
        "created_at": strategy[2],
        "status": strategy[3],
        "approved_at": strategy[4],
        "archived_at": strategy[5],
        "company_id": strategy[6],
        "company_name": strategy[7]
    }
    
    
    return templates.TemplateResponse("strategy.html", {
        "request": request,
        "user": user,
        "strategy": strategy_dict
    })    
    
#---------------------------------------------------------------------------------------


# Save edited Influncers E-mails

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

# Save edited Influncers E-mails
@router.post("/save_email/{strategy_id}")
@limiter.limit("100/minute")
async def save_email(
    strategy_id: int, 
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Save individual email content for a strategy"""
    
    try:
        # Get the request data
        data = await request.json()
        email_index = data.get('email_index')
        email_content = data.get('email_content')
        
        if email_index is None or email_content is None:
            return JSONResponse(
                {"success": False, "error": "Missing email_index or email_content"},
                status_code=400
            )
        
        # Verify strategy belongs to user
        cursor.execute("""
            SELECT s.id, s.content, s.status, c.user_id 
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s
        """, (strategy_id,))
        
        strategy = cursor.fetchone()
        if not strategy:
            return JSONResponse(
                {"success": False, "error": "Strategy not found"},
                status_code=404
            )
        
        if strategy[3] != user["user_id"]:
            return JSONResponse(
                {"success": False, "error": "Unauthorized"},
                status_code=403
            )
        
        # Only allow saving for approved strategies
        if strategy[2] != 'approved':
            return JSONResponse(
                {"success": False, "error": "Can only save emails for approved strategies"},
                status_code=400
            )
        
        # Parse the strategy content
        soup = BeautifulSoup(strategy[1], 'html.parser')
        
        # Find all email textareas
        email_textareas = soup.find_all('textarea', class_='editable-email')
        
        if email_index >= len(email_textareas):
            return JSONResponse(
                {"success": False, "error": "Invalid email index"},
                status_code=400
            )
        
        # Update the specific textarea
        textarea = email_textareas[email_index]
        textarea.clear()
        from bs4 import NavigableString
        textarea.append(NavigableString(email_content))
        
        # Update the strategy content in database
        updated_content = str(soup)
        cursor.execute("""
            UPDATE strategies 
            SET content = %s
            WHERE id = %s
        """, (updated_content, strategy_id))
        
        # Also update the influencer email in the influencers table
        cursor.execute("""
            UPDATE influencers 
            SET email_text = %s
            WHERE strategy_id = %s 
            AND id = (
                SELECT id FROM influencers 
                WHERE strategy_id = %s 
                ORDER BY id 
                LIMIT 1 OFFSET %s
            )
        """, (email_content, strategy_id, strategy_id, email_index))
        
        conn.commit()
        
        return JSONResponse({
            "success": True, 
            "message": "Email saved successfully"
        })
        
    except psycopg2.Error as e:
        logger.error(f"Database error saving email: {str(e)}")
        return JSONResponse(
            {"success": False, "error": "Database error - please try again"},
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error saving email: {str(e)}")
        return JSONResponse(
            {"success": False, "error": "Unexpected error"},
            status_code=500
        )

#---------------------------------------------------------------------------------------


# Approve strategy
@router.post("/approve_strategy/{strategy_id}")
async def approve_strategy(
    request: Request, 
    strategy_id: int, 
    user: dict = Depends(get_current_user),
):
    
    # First get the strategy content before archiving others
    cursor.execute("""
        SELECT id, content, company_id FROM strategies 
        WHERE id = %s
    """, (strategy_id,))
    strategy = cursor.fetchone()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # --------------- New Email ------------------ 
    # Get the form data which includes edited emails
    form_data = await request.form()
    
    # Debug: Print all form data
    print("=== FORM DATA DEBUG ===")
    for key, value in form_data.items():
        print(f"{key}: {len(str(value))} characters - {str(value)[:100]}...")
    print("=== END DEBUG ===")
    
    # Parse the original strategy content
    soup = BeautifulSoup(strategy[1], 'html.parser')
    
    # Update ALL email textareas with the form data
    email_textareas = soup.find_all('textarea', class_='editable-email')
    print(f"Found {len(email_textareas)} textareas in HTML")
    
    for idx, textarea in enumerate(email_textareas):
        email_key = f"email_{idx}"
        if email_key in form_data:
            print(f"Updating textarea {idx} with {len(form_data[email_key])} characters")
            # Clear and update textarea content
            textarea.clear()
            from bs4 import NavigableString
            textarea.append(NavigableString(form_data[email_key]))
        else:
            print(f"No form data found for {email_key}")
    
    # Get the updated strategy content
    updated_strategy_content = str(soup)
    
    # --------------------------------------------
    
    # Extract image prompts from strategy content
    image_prompts = extract_image_prompts(updated_strategy_content)
    
    # Archive any existing approved strategy for this company
    cursor.execute("""
        UPDATE strategies 
        SET status = 'denied - archived', archived_at = NOW()
        WHERE company_id = %s 
        AND status = 'approved'
    """, (strategy[2],))
    
    # Then approve the selected strategy
    cursor.execute("""
        UPDATE strategies 
        SET content = %s, status = 'approved', approved_at = NOW()
        WHERE id = %s
        RETURNING company_id
    """, (updated_strategy_content, strategy_id))
    
    company_id = cursor.fetchone()[0]
    
    # Now save the content items to database
    await save_content_items_to_db(strategy_id, company_id, user["user_id"], updated_strategy_content)
    
    # Save extracted image prompts
    for prompt_type, prompt_text in image_prompts.items():
        cursor.execute("""
            INSERT INTO image_prompts (strategy_id, company_id, user_id, prompt_text, prompt_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (strategy_id, company_id, user["user_id"], prompt_text, prompt_type))
        
    # Extract and save influencers - using strategy_content instead of full_strategy
    print("About to extract influencers...")
    await extract_and_save_influencers(strategy_id, company_id, user["user_id"], updated_strategy_content)
    
    conn.commit()
    
    return RedirectResponse(url=f"/company/{company_id}", status_code=303) 

#---------------------------------------------------------------------------------------

# Archinve non-approved strategies
@router.post("/archive_and_regenerate/{strategy_id}")
async def archive_and_regenerate(
    strategy_id: int, 
    user: dict = Depends(get_current_user),
):
    # Archive the current strategy
    cursor.execute("""
        UPDATE strategies 
        SET status = 'denied - archived', archived_at = NOW()
        WHERE id = %s AND company_id IN (
            SELECT id FROM companies WHERE user_id = %s
        )
        RETURNING company_id
    """, (strategy_id, user["user_id"]))
    
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    company_id = result[0]
    conn.commit()
    
    # Old Backup return
    #return RedirectResponse(url=f"/strategy/new/{company_id}", status_code=303)  
    
    return RedirectResponse(
        url=f"/company/{company_id}?archived=true#Strategies",
        status_code=303
    )  

#---------------------------------------------------------------------------------------


# Route - Check strategy status
@router.get("/check_strategy_status_by_id/{strategy_id}")
async def check_strategy_status_by_id(
    strategy_id: int,
    user: dict = Depends(get_current_user),
    cursor = Depends(get_cursor)
):
    """Check strategy status by strategy ID"""
    try:
        cursor.execute("""
            SELECT status 
            FROM strategies 
            WHERE id = %s AND company_id IN (
                SELECT id FROM companies WHERE user_id = %s
            )
        """, (strategy_id, user["user_id"]))
        
        result = cursor.fetchone()
        if not result:
            return JSONResponse({"status": "not_found"}, status_code=404)
        
        return {"status": result[0]}
        
    except Exception as e:
        logger.error(f"Error checking strategy status: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": str(e)}, 
            status_code=500
        )


#---------------------------------------------------------------------------------------

# Route to get the last approved strategy date
@router.get("/get_last_approved_strategy_date/{company_id}")
async def get_last_approved_strategy_date(
    company_id: int,
    user: dict = Depends(get_current_user)
):
    try:
        cursor.execute("""
            SELECT approved_at 
            FROM strategies 
            WHERE company_id = %s 
            AND status = 'approved'
            ORDER BY approved_at DESC 
            LIMIT 1
        """, (company_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            return {"approved_date": result[0].strftime("%Y-%m-%d %H:%M:%S")}
        else:
            return {"approved_date": None}
            
    except Exception as e:
        logger.error(f"Error getting approved strategy date: {str(e)}")
        return {"approved_date": None}

# Helper to get the company then get the approved strategy 
@router.get("/get_user_companies")
async def get_user_companies(
    user: dict = Depends(get_current_user)
):
    try:
        cursor.execute("""
            SELECT id, name FROM companies 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user["user_id"],))
        
        companies = cursor.fetchall()
        return {
            "companies": [
                {"id": company[0], "name": company[1]} 
                for company in companies
            ]
        }
            
    except Exception as e:
        logger.error(f"Error getting user companies: {str(e)}")
        return {"companies": []}

#---------------------------------------------------------------------------------------


# Route for editing strategy form
@router.get("/edit_strategy/{strategy_id}", response_class=HTMLResponse)
async def edit_strategy_form(
    request: Request, 
    strategy_id: int, 
    user: dict = Depends(get_current_user),
):
    cursor.execute("""
        SELECT s.id, s.content, s.created_at, c.id as company_id, c.name as company_name
        FROM strategies s
        JOIN companies c ON s.company_id = c.id
        WHERE s.id = %s AND c.user_id = %s
    """, (strategy_id, user["user_id"]))
    
    strategy = cursor.fetchone()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy_dict = {
        "id": strategy[0],
        "content": strategy[1],
        "created_at": strategy[2].strftime("%Y-%m-%d %H:%M"),
        "company_id": strategy[3],
        "company_name": strategy[4]
    }
    
    return templates.TemplateResponse("edit_strategy.html", {
        "request": request,
        "user": user,
        "strategy": strategy_dict
    })

# Route for updating strategy content
@router.post("/update_strategy/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    content: str = Form(...),
    user: dict = Depends(get_current_user),
):
    
    # Check if strategy belongs to user
    cursor.execute("""
        SELECT s.id
        FROM strategies s
        JOIN companies c ON s.company_id = c.id
        WHERE s.id = %s AND c.user_id = %s
    """, (strategy_id, user["user_id"]))
    
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    cursor.execute("UPDATE strategies SET content = %s WHERE id = %s", (content, strategy_id))
    conn.commit()
    
    return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)


#---------------------------------------------------------------------------------------

# Route for deleting a strategy
@router.post("/delete_strategy/{strategy_id}")
async def delete_strategy(
    strategy_id: int, 
    user: dict = Depends(get_current_user),
    cursor = Depends(get_cursor)
):
    try:
        # Check if strategy belongs to user and get company_id
        cursor.execute("""
            SELECT s.id, c.id as company_id
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s
        """, (strategy_id, user["user_id"]))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        company_id = result[1]
        
        # Just delete the strategy - related records cascade automatically
        cursor.execute("DELETE FROM strategies WHERE id = %s", (strategy_id,))
        
        cursor.connection.commit()
        
        return RedirectResponse(url=f"/company/{company_id}", status_code=303)
        
    except Exception as e:
        if cursor.connection:
            cursor.connection.rollback()
        logger.error(f"Error deleting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete strategy")