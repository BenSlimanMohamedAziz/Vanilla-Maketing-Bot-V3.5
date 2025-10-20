# Imports
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from auth.auth import get_current_user
from config.config import get_db_connection, get_db_cursor, release_db_connection
import asyncio
import psycopg2
from datetime import datetime
import re
from fastapi import Body
import os
from auth.meta_oauth import MetaOAuth
from auth.linkedin_oauth import LinkedInOAuth

# For mailing : 
from components.Mail.mails import send_influencer_emails


# Import the content Publishing
from .platfroms_publish_utils import (
    publish_instagram_post,
    publish_instagram_story,
    publish_instagram_reel,
    publish_facebook_text_post,
    publish_facebook_image_post,
    publish_facebook_video_post,
    publish_linkedin_image_post,
    publish_linkedin_text_post,
    publish_linkedin_video_post
)


#---------------------------------------------------------------------------------------


# Initialize router and templates
router = APIRouter(
    tags=["strategy_launch"],
    responses={404: {"description": "Not found"}}
)

# Getting templates Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "static" / "templates"

# templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Logging
logger = logging.getLogger(__name__)

# Database dependency
async def get_db():
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    try:
        yield cursor, conn
    finally:
        release_db_connection(conn)
        
#---------------------------------------------------------------------------------------


# Launch function
@router.get("/launch_strategy/{strategy_id}", response_class=HTMLResponse)
async def launch_strategy_page(
    request: Request, 
    strategy_id: int, 
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    cursor, conn = db
    
    try:
        # Get strategy and associated company info
        cursor.execute("""
            SELECT s.id, s.company_id, c.name as company_name, c.logo_url
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s AND s.status = 'approved'
        """, (strategy_id, user["user_id"]))
        
        strategy = cursor.fetchone()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found or not approved")

        # Get Instagram content items grouped by type
        cursor.execute("""
            SELECT id, content_type, caption, hashtags, image_prompt, 
                   video_idea, video_placeholder, story_idea
            FROM content_items 
            WHERE strategy_id = %s AND platform = 'Instagram'
            ORDER BY CASE 
                WHEN content_type = 'Feed Image Posts' THEN 1
                WHEN content_type = 'Instagram Stories' THEN 2
                WHEN content_type = 'Instagram Reels' THEN 3
                ELSE 4
            END
        """, (strategy_id,))
        
        content_items = {
            'feed_posts': [],
            'stories': [],
            'reels': []
        }
        
        for row in cursor.fetchall():
            item = {
                "id": row[0],
                "type": row[1],
                "caption": row[2],
                "hashtags": row[3],
                "image_prompt": row[4],
                "video_idea": row[5],
                "video_placeholder": row[6],
                "story_idea": row[7]
            }
            
            if row[1] == 'Feed Image Posts':
                content_items['feed_posts'].append(item)
            elif row[1] == 'Instagram Stories':
                content_items['stories'].append(item)
            elif row[1] == 'Instagram Reels':
                content_items['reels'].append(item)

        # Get Facebook content items grouped by type
        cursor.execute("""
            SELECT id, content_type, caption, hashtags, image_prompt, 
                   video_idea, video_placeholder, story_idea
            FROM content_items 
            WHERE strategy_id = %s AND platform = 'Facebook'
            ORDER BY CASE 
                WHEN content_type = 'Text Posts (Status Updates / Announcements)' THEN 1
                WHEN content_type = 'Image Posts' THEN 2
                WHEN content_type = 'Video Posts' THEN 3
                ELSE 4
            END
        """, (strategy_id,))
        
        facebook_content = {
            'text_posts': [],
            'image_posts': [],
            'video_posts': []
        }
        
        for row in cursor.fetchall():
            item = {
                "id": row[0],
                "type": row[1],
                "caption": row[2],
                "hashtags": row[3],
                "image_prompt": row[4],
                "video_idea": row[5],
                "video_placeholder": row[6],
                "story_idea": row[7]
            }
            
            if row[1] == 'Text Posts (Status Updates / Announcements)':
                facebook_content['text_posts'].append(item)
            elif row[1] == 'Image Posts':
                facebook_content['image_posts'].append(item)
            elif row[1] == 'Video Posts':
                facebook_content['video_posts'].append(item)
        
        return templates.TemplateResponse("launch_strategy.html", {
            "request": request,
            "user": user,
            "strategy": {
                "id": strategy[0],
                "company_id": strategy[1],
                "company_name": strategy[2],
                "logo_url": strategy[3]
            },
            "content_items": content_items,  # Keep this for backward compatibility
            "instagram_content": content_items,  # Same as content_items
            "facebook_content": facebook_content
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error loading launch strategy page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

#---------------------------------------------------------------------------------------


# Get generated strategy content to display 
@router.get("/get_strategy_content/{strategy_id}")
async def get_strategy_content(strategy_id: int, user: dict = Depends(get_current_user)):
    """Get structured content from approved strategy - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify strategy belongs to user and is approved
        cursor.execute("""
            SELECT s.content 
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s AND s.status = 'approved'
        """, (strategy_id, user["user_id"]))
        
        strategy = cursor.fetchone()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found or not approved")
        
        # Run HTML parsing in thread pool (BeautifulSoup is CPU intensive)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            parse_strategy_content,
            strategy[0]  # Pass the strategy content
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_strategy_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()


# Parse Strategy content
def parse_strategy_content(strategy_content: str):
    """Parse strategy content and extract structured data - Runs in thread pool"""
    soup = BeautifulSoup(strategy_content, 'html.parser')
    
    # Extract events data - PROPER PARSING
    events_section = soup.find('section', class_='event-strategy')
    events = []
    
    if events_section:
        print("Found events section, parsing events...")
        
        # Find all h3 elements that contain event titles
        event_headings = events_section.find_all('h3')
        
        for heading in event_headings:
            event_name = heading.get_text(strip=True)
            
            # Skip if this doesn't look like a real event heading
            if not event_name or len(event_name) < 10:
                continue
                
            # Find the next ul element which contains the event details
            next_ul = heading.find_next('ul')
            if not next_ul:
                continue
                
            event_data = {
                'name': event_name,
                'date': '',
                'place': '',
                'description': ''
            }
            
            # Extract all list items from this event's ul
            list_items = next_ul.find_all('li')
            
            for li in list_items:
                li_text = li.get_text(strip=True)
                
                # Extract date and location
                if 'Date & Location:' in li_text:
                    date_location = li_text.replace('Date & Location:', '').strip()
                    if '–' in date_location:
                        parts = date_location.split('–', 1)
                        event_data['date'] = parts[0].strip()
                        event_data['place'] = parts[1].strip()
                    else:
                        event_data['date'] = date_location
                
                # Extract strategic value as description
                elif 'Strategic Value:' in li_text:
                    # Get the strategic value content from nested list items
                    strategic_items = li.find_all('li')
                    if strategic_items:
                        strategic_texts = [item.get_text(strip=True) for item in strategic_items]
                        event_data['description'] = ' | '.join(strategic_texts)
                    else:
                        # If no nested list, get the text after "Strategic Value:"
                        strategic_text = li_text.replace('Strategic Value:', '').strip()
                        event_data['description'] = strategic_text
            
            # Only add the event if we have at least a name and date
            if event_data['name'] and event_data['date']:
                events.append(event_data)
                print(f"Extracted event: {event_data}")
    
    print(f"Final parsed events: {events}")
    
    # Extract influencers data - SEPARATE SECTION
    influencers_section = soup.find('section', class_='influencer-recommendations')
    influencers = []
    if influencers_section:
        print("Found influencers section, parsing influencers...")
        influencer_cards = influencers_section.find_all('div', class_='influencer-card')
        for card in influencer_cards:
            name = card.find('h3').text.replace('INFLUENCER_NAME:', '').strip() if card.find('h3') else 'Unknown'
            email = card.find('p', string=lambda t: 'EMAIL:' in t).text.replace('EMAIL:', '').strip() if card.find('p', string=lambda t: 'EMAIL:' in t) else 'Email not provided'
            followers = card.find('p', string=lambda t: 'FOLLOWERS:' in t).text.replace('FOLLOWERS:', '').strip() if card.find('p', string=lambda t: 'FOLLOWERS:' in t) else 'Followers not specified'
            handle = card.find('p', string=lambda t: 'HANDLE:' in t).text.replace('HANDLE:', '').strip() if card.find('p', string=lambda t: 'HANDLE:' in t) else 'Handle not specified'
            niche = card.find('p', string=lambda t: 'NICHE:' in t).text.replace('NICHE:', '').strip() if card.find('p', string=lambda t: 'NICHE:' in t) else 'Niche not specified'
            
            collab_text = card.find('p', string=lambda t: 'Price Range:' in t).text if card.find('p', string=lambda t: 'Price Range:' in t) else ''
            budget = 'Budget not specified'
            if 'Price Range:' in collab_text:
                budget = collab_text.split('Price Range:')[-1].strip()
            
            influencers.append({
                'name': name,
                'email': email,
                'followers': followers,
                'handle': handle,
                'niche': niche,
                'budget': budget,
                'email_sent': True
            })
    
    # Extract other sections (keep your existing code)
    blueprint_section = soup.find('section', class_='marketing-calendar')
    blueprint_data = []
    if blueprint_section:
        rows = blueprint_section.find('tbody').find_all('tr') if blueprint_section.find('tbody') else []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6:
                blueprint_data.append({
                    'dates': cells[0].text.strip(),
                    'theme': cells[1].text.strip(),
                    'actions': cells[2].text.strip(),
                    'platforms': cells[4].text.strip(),
                    'targets': cells[5].text.strip()
                })
    
    recommendations_section = soup.find('section', class_='marketing-advice')
    recommendations = {
        'growth': [], 'content': [], 'advantage': [], 'outreach': [], 'budget': []
    }
    
    if recommendations_section:
        growth_section = recommendations_section.find('div', class_='growth')
        if growth_section:
            recommendations['growth'] = [li.text.strip() for li in growth_section.find_all('li')]
        
        content_section = recommendations_section.find('div', class_='content')
        if content_section:
            recommendations['content'] = [li.text.strip() for li in content_section.find_all('li')]
        
        advantage_section = recommendations_section.find('div', class_='advantage')
        if advantage_section:
            recommendations['advantage'] = [li.text.strip() for li in advantage_section.find_all('li')]
        
        outreach_section = recommendations_section.find('div', class_='outreach')
        if outreach_section:
            recommendations['outreach'] = [li.text.strip() for li in outreach_section.find_all('li')]
        
        budget_section = recommendations_section.find('div', class_='budget')
        if budget_section:
            recommendations['budget'] = [li.text.strip() for li in budget_section.find_all('li')]
    
    return {
        'events': events,
        'influencers': influencers,
        'blueprint': blueprint_data,
        'recommendations': recommendations
    }


            
# Parse Strategy content
""" Back up code
def parse_strategy_content(strategy_content: str):
    '''Parse strategy content and extract structured data - Runs in thread pool'''
    soup = BeautifulSoup(strategy_content, 'html.parser')
    
    # Extract events data
    events_section = soup.find('section', class_='event-strategy')
    events = []
    if events_section:
        event_headings = events_section.find_all('h3')
        for heading in event_headings:
            # Get the date and place paragraph
            date_place_p = heading.find_next('p')
            date_place_text = date_place_p.text.strip() if date_place_p else ''
            
            # Extract date and place from the text
            date = ''
            place = ''
            if date_place_text and '• Date and Place:' in date_place_text:
                # Remove the bullet point and label: "• Date and Place: June 29, 2025, Dougga, Tunisia"
                content = date_place_text.replace('• Date and Place:', '').strip()
                
                # Split by comma: ["June 29", "2025", "Dougga", "Tunisia"]
                parts = [part.strip() for part in content.split(',')]
                
                if len(parts) >= 3:
                    # Reconstruct: date = "June 29, 2025", place = "Dougga, Tunisia"  
                    date = f"{parts[0]}, {parts[1]}"  # "June 29, 2025"
                    place = ', '.join(parts[2:])       # "Dougga, Tunisia"
            
            # Get description
            strategic_value_p = date_place_p.find_next('p') if date_place_p else None
            description = strategic_value_p.text.strip() if strategic_value_p else ''
            
            event = {
                'name': heading.text.strip(),
                'date': date,
                'place': place,  # "Dougga, Tunisia"
                'description': description
            }
            events.append(event)

    # Extract marketing blueprint data
    blueprint_section = soup.find('section', class_='marketing-calendar')
    blueprint_data = []
    if blueprint_section:
        rows = blueprint_section.find('tbody').find_all('tr') if blueprint_section.find('tbody') else []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6:  # Ensure we have all columns
                blueprint_data.append({
                    'dates': cells[0].text.strip(),
                    'theme': cells[1].text.strip(),
                    'actions': cells[2].text.strip(),
                    'platforms': cells[4].text.strip(),
                    'targets': cells[5].text.strip()
                })
    
    # Extract influencers data
    influencers_section = soup.find('section', class_='influencer-recommendations')
    influencers = []
    if influencers_section:
        influencer_cards = influencers_section.find_all('div', class_='influencer-card')
        for card in influencer_cards:
            name = card.find('h3').text.replace('INFLUENCER_NAME:', '').strip() if card.find('h3') else 'Unknown'
            email = card.find('p', string=lambda t: 'EMAIL:' in t).text.replace('EMAIL:', '').strip() if card.find('p', string=lambda t: 'EMAIL:' in t) else 'Email not provided'
            followers = card.find('p', string=lambda t: 'FOLLOWERS:' in t).text.replace('FOLLOWERS:', '').strip() if card.find('p', string=lambda t: 'FOLLOWERS:' in t) else 'Followers not specified'
            handle = card.find('p', string=lambda t: 'HANDLE:' in t).text.replace('HANDLE:', '').strip() if card.find('p', string=lambda t: 'HANDLE:' in t) else 'Handle not specified'
            niche = card.find('p', string=lambda t: 'NICHE:' in t).text.replace('NICHE:', '').strip() if card.find('p', string=lambda t: 'NICHE:' in t) else 'Niche not specified'
            
            # Extract budget from COLLABORATION_TYPE
            collab_text = card.find('p', string=lambda t: 'Price Range:' in t).text if card.find('p', string=lambda t: 'Price Range:' in t) else ''
            budget = 'Budget not specified'
            if 'Price Range:' in collab_text:
                budget = collab_text.split('Price Range:')[-1].strip()
            
            influencers.append({
                'name': name,
                'email': email,
                'followers': followers,
                'handle': handle,
                'niche': niche,
                'budget': budget,
                'email_sent': True
            })
    
    # Extract recommendations data - UPDATED TO MATCH YOUR HTML STRUCTURE
    recommendations_section = soup.find('section', class_='marketing-advice')
    recommendations = {
        'growth': [],
        'content': [],
        'advantage': [],
        'outreach': [],
        'budget': []
    }
    
    if recommendations_section:
        # Growth & Trends
        growth_section = recommendations_section.find('div', class_='growth')
        if growth_section:
            recommendations['growth'] = [li.text.strip() for li in growth_section.find_all('li')]
        
        # Content & Ads
        content_section = recommendations_section.find('div', class_='content')
        if content_section:
            recommendations['content'] = [li.text.strip() for li in content_section.find_all('li')]
        
        # Competitive Edge
        advantage_section = recommendations_section.find('div', class_='advantage')
        if advantage_section:
            recommendations['advantage'] = [li.text.strip() for li in advantage_section.find_all('li')]
        
        # Influencers & Events
        outreach_section = recommendations_section.find('div', class_='outreach')
        if outreach_section:
            recommendations['outreach'] = [li.text.strip() for li in outreach_section.find_all('li')]
        
        # Budget & Metrics
        budget_section = recommendations_section.find('div', class_='budget')
        if budget_section:
            recommendations['budget'] = [li.text.strip() for li in budget_section.find_all('li')]
    
    return {
        'events': events,
        'influencers': influencers,
        'blueprint': blueprint_data,
        'recommendations': recommendations
    }
"""

#---------------------------------------------------------------------------------------
    
    
# AUTO email send on launch    
@router.post("/send_launch_emails/{company_id}")
async def send_launch_emails(
    company_id: int, 
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Auto send emails on strategy launch
    This endpoint is async and non-blocking
    """
    cursor, conn = db
    
    try:
        # Verify user owns the company
        cursor.execute("""
            SELECT id FROM companies 
            WHERE id = %s AND user_id = %s
        """, (company_id, user["user_id"]))
        
        company = cursor.fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get the approved strategy
        cursor.execute("""
            SELECT id FROM strategies 
            WHERE company_id = %s AND status = 'approved'
            ORDER BY approved_at DESC LIMIT 1
        """, (company_id,))
        
        strategy = cursor.fetchone()
        if not strategy:
            return JSONResponse(
                {"success": False, "message": "No approved strategy found for this company"},
                status_code=404
            )
            
        strategy_id = strategy[0]
        
        # Call your existing email function (uncomment when ready)
        # Note: Make sure send_influencer_emails is also async or runs in executor
        #await send_influencer_emails(strategy_id)
        
        logger.info(f"Launch emails triggered for strategy {strategy_id}, company {company_id}")
        
        return JSONResponse({
            "success": True, 
            "message": "Emails sent successfully",
            "strategy_id": strategy_id,
            "company_id": company_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending launch emails: {str(e)}")
        return JSONResponse(
            {"success": False, "message": f"Failed to send emails: {str(e)}"},
            status_code=500
        )    
 
 
 
#--------------------------------------------------------------------------------------- 
 
 
 
# Save influencer email route
@router.post("/save_influencer_email/{strategy_id}")
async def save_influencer_email(
    strategy_id: int,
    request_data: dict = Body(...),
    user: dict = Depends(get_current_user)
):
    """Save edited influencer email content"""
    try:
        cursor, conn = get_db()
        
        # Verify strategy belongs to user
        cursor.execute("""
            SELECT s.id 
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s
        """, (strategy_id, user["user_id"]))
        
        strategy = cursor.fetchone()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Extract data from request
        influencer_index = request_data.get('influencer_index')
        email_content = request_data.get('email_content')
        influencer_name = request_data.get('influencer_name')
        influencer_email = request_data.get('influencer_email')
        
        if influencer_index is None or not email_content:
            raise HTTPException(status_code=400, detail="Missing required data")
        
        # Update or insert the influencer email in database
        cursor.execute("""
            INSERT INTO influencers (strategy_id, name, email, email_text, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (strategy_id, email) 
            DO UPDATE SET 
                email_text = EXCLUDED.email_text,
                updated_at = NOW()
        """, (strategy_id, influencer_name, influencer_email, email_content))
        
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Email content saved successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving influencer email: {str(e)}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
    finally:
        if 'conn' in locals():
            release_db_connection(conn) 
      
        
#---------------------------------------------------------------------------------------


# Show todays posts to generate and approve or post theme
@router.get("/get_todays_posts/{company_id}")
async def get_todays_posts(company_id: int, user: dict = Depends(get_current_user)):
    """Get all posts scheduled for today that need approval or posting from the approved strategy - Async version"""
    try:
        logger.info(f"Starting get_todays_posts for company_id: {company_id}, user_id: {user.get('user_id')}")
        
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify company belongs to user
        logger.info("Executing company verification query...")
        try:
            cursor.execute("SELECT id FROM companies WHERE id = %s AND user_id = %s", 
                          (company_id, user["user_id"]))
            company_result = cursor.fetchone()
            logger.info(f"Company result: {company_result}")
        except psycopg2.Error as db_error:
            logger.error(f"Database error during company verification: {db_error}")
            # Reset cursor state and try again
            conn.rollback()
            cursor.execute("SELECT id FROM companies WHERE id = %s AND user_id = %s", 
                          (company_id, user["user_id"]))
            company_result = cursor.fetchone()
        
        if not company_result:
            logger.info("Company not found for user")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # First get the approved strategy for this company
        logger.info("Executing strategy query...")
        try:
            cursor.execute("""
                SELECT id FROM strategies 
                WHERE company_id = %s AND status = 'approved'
                ORDER BY approved_at DESC 
                LIMIT 1
            """, (company_id,))
            
            approved_strategy = cursor.fetchone()
            logger.info(f"Strategy result: {approved_strategy}")
        except psycopg2.Error as db_error:
            logger.error(f"Database error during strategy query: {db_error}")
            conn.rollback()
            cursor.execute("""
                SELECT id FROM strategies 
                WHERE company_id = %s AND status = 'approved'
                ORDER BY approved_at DESC 
                LIMIT 1
            """, (company_id,))
            approved_strategy = cursor.fetchone()
        
        if not approved_strategy:
            logger.info(f"No approved strategy found for company {company_id}")
            return {"posts": []}  # No approved strategy, no posts to show
        
        strategy_id = approved_strategy[0]
        logger.info(f"Using approved strategy ID {strategy_id} for company {company_id}")
        
        # Get current day name and time
        now = datetime.now()
        current_day = now.strftime("%A")
        current_time = now.time()
        logger.info(f"Current day: {current_day}, Current time: {current_time}")
        
        # Get posts scheduled for today FROM THE APPROVED STRATEGY ONLY
        logger.info("Executing posts query...")
        try:
            cursor.execute("""
                SELECT 
                    ci.id, ci.platform, ci.content_type, ci.caption, ci.hashtags, 
                    ci.image_prompt, ci.video_placeholder, ci.best_time,
                    ci.status, c.name as company_name, c.logo_url
                FROM content_items ci
                JOIN companies c ON ci.company_id = c.id
                WHERE ci.company_id = %s 
                AND ci.strategy_id = %s
                AND ci.best_time LIKE %s
                AND ci.status IN ('pending', 'needs_approval')
                ORDER BY 
                    CASE 
                        WHEN ci.status = 'needs_approval' THEN 0
                        WHEN ci.status = 'pending' THEN 1
                        ELSE 2
                    END,
                    ci.best_time
            """, (company_id, strategy_id, f"%{current_day}%"))
            
            rows = cursor.fetchall()
        except psycopg2.Error as db_error:
            logger.error(f"Database error during posts query: {db_error}")
            conn.rollback()
            # Try the query again after rollback
            cursor.execute("""
                SELECT 
                    ci.id, ci.platform, ci.content_type, ci.caption, ci.hashtags, 
                    ci.image_prompt, ci.video_placeholder, ci.best_time,
                    ci.status, c.name as company_name, c.logo_url
                FROM content_items ci
                JOIN companies c ON ci.company_id = c.id
                WHERE ci.company_id = %s 
                AND ci.strategy_id = %s
                AND ci.best_time LIKE %s
                AND ci.status IN ('pending', 'needs_approval')
                ORDER BY 
                    CASE 
                        WHEN ci.status = 'needs_approval' THEN 0
                        WHEN ci.status = 'pending' THEN 1
                        ELSE 2
                    END,
                    ci.best_time
            """, (company_id, strategy_id, f"%{current_day}%"))
            rows = cursor.fetchall() or [] 
        
        # Proper handling of empty results
        if not rows:
            logger.info("No pending/needs_approval posts found for today")
            return {"posts": []}
        
        logger.info(f"Found {len(rows)} rows")    
        posts = []
        
        for i, row in enumerate(rows):
            logger.info(f"Processing row {i+1}/{len(rows)}: {row[0]}")
            # Extract hour from best_time (e.g., "Monday 9AM" -> 9)
            time_str = row[7] if row[7] else ""
            scheduled_hour = None
            if time_str:
                try:
                    time_part = time_str.split()[1]  # Get "9AM" part
                    if 'AM' in time_part or 'PM' in time_part:
                        hour = int(time_part.replace('AM', '').replace('PM', ''))
                        if 'PM' in time_part and hour != 12:
                            hour += 12
                        elif 'AM' in time_part and hour == 12:
                            hour = 0
                        scheduled_hour = hour
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse time from '{time_str}': {e}")
                    pass
          
            should_show = False
            is_past_due = False
            
            if scheduled_hour is not None:
                current_hour = current_time.hour
                
                # Past due if current hour is greater than scheduled hour
                if current_hour > scheduled_hour:
                    should_show = True
                    is_past_due = True
                # Within 1 hour if current hour is exactly 1 hour before scheduled
                elif current_hour == scheduled_hour - 1 or current_hour == scheduled_hour:
                    should_show = True
            
            if should_show:
                posts.append({
                    "id": row[0],
                    "platform": row[1],
                    "content_type": row[2],
                    "caption": row[3],
                    "hashtags": row[4],
                    "image_prompt": row[5],
                    "video_placeholder": row[6],
                    "scheduled_time": row[7],
                    "status": row[8],
                    "company_name": row[9],
                    "logo_url": row[10],
                    "scheduled_hour": scheduled_hour,
                    "is_past_due": is_past_due,
                    "strategy_id": strategy_id  # Add strategy_id for reference
                })
        
        logger.info(f"Returning {len(posts)} posts")
        return {"posts": posts}
        
    except psycopg2.Error as e:
        logger.error(f"Database error in get_todays_posts: {e}")
        # Always rollback on database errors to reset cursor state
        if 'conn' in locals():
            conn.rollback()
        return {"posts": [], "error": "Database error occurred"}
    except Exception as e:
        logger.error(f"Unexpected error in get_todays_posts: {e}")
        # Rollback on any error to be safe
        if 'conn' in locals():
            conn.rollback()
        return {"posts": [], "error": "An unexpected error occurred"}
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()        
            
#---------------------------------------------------------------------------------------

# Approve content for auto post
@router.post("/approve_post/{content_id}")
async def approve_post(
    content_id: int,
    request: dict,  # Changed from caption: str = Body(...)
    user: dict = Depends(get_current_user)
):
    """Approve a post and save caption changes using existing logic - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify content belongs to user
        cursor.execute("""
            SELECT ci.id 
            FROM content_items ci
            JOIN companies c ON ci.company_id = c.id
            WHERE ci.id = %s AND c.user_id = %s
        """, (content_id, user["user_id"]))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Extract caption from request
        caption = request.get("caption", "")
        
        # Use your existing caption editing logic
        hashtags = re.findall(r'#\w+', caption)
        clean_caption = re.sub(r'#\w+', '', caption).strip()
        final_hashtags = ' '.join(hashtags) if hashtags else None
        
        # Update status to approved and save caption
        cursor.execute("""
            UPDATE content_items 
            SET status = 'approved', caption = %s, hashtags = %s
            WHERE id = %s
        """, (clean_caption, final_hashtags, content_id))
        
        # Run commit in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.commit)
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        # Rollback on error
        if 'conn' in locals():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, conn.rollback)
        logger.error(f"Error approving post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()            
            
#---------------------------------------------------------------------------------------

# Reject content 
@router.post("/reject_post/{content_id}")
async def reject_post(
    content_id: int,
    user: dict = Depends(get_current_user)
):
    """Reject a post and mark it as rejected - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify content belongs to user
        cursor.execute("""
            SELECT ci.id 
            FROM content_items ci
            JOIN companies c ON ci.company_id = c.id
            WHERE ci.id = %s AND c.user_id = %s
        """, (content_id, user["user_id"]))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Update status to rejected and set rejected_at timestamp
        cursor.execute("""
            UPDATE content_items 
            SET status = 'rejected', rejected_at = NOW()
            WHERE id = %s
        """, (content_id,))
        
        # Run commit in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.commit)
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        # Rollback on error
        if 'conn' in locals():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, conn.rollback)
        logger.error(f"Error rejecting post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()          
    
    
#---------------------------------------------------------------------------------------


# Check approved post to auto post them
@router.get("/check_approved_posts/{company_id}")
async def check_approved_posts(
    company_id: int, 
    user: dict = Depends(get_current_user)
):
    """Background endpoint to check for approved posts ready to post FROM APPROVED STRATEGY ONLY - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify company belongs to user
        cursor.execute("SELECT id FROM companies WHERE id = %s AND user_id = %s", 
                      (company_id, user["user_id"]))
        company_result = cursor.fetchone()
        if not company_result:
            logger.info(f"Company {company_id} not found for user {user['user_id']}")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get the approved strategy for this company
        cursor.execute("""
            SELECT id FROM strategies 
            WHERE company_id = %s AND status = 'approved'
            ORDER BY approved_at DESC 
            LIMIT 1
        """, (company_id,))
        
        approved_strategy = cursor.fetchone()
        if not approved_strategy:
            logger.info(f"No approved strategy found for company {company_id}")
            return {"posts_posted": 0}  # No approved strategy
        
        strategy_id = approved_strategy[0]
        logger.info(f"Using approved strategy ID {strategy_id} for auto-posting (company {company_id})")
        
        now = datetime.now()
        current_day = now.strftime("%A")
        current_hour = now.hour
        
        # Get approved posts for current day and hour FROM THE APPROVED STRATEGY ONLY
        cursor.execute("""
            SELECT id, platform, content_type, best_time, status, caption, hashtags
            FROM content_items 
            WHERE company_id = %s 
            AND strategy_id = %s
            AND status = 'approved'
            AND best_time LIKE %s
        """, (company_id, strategy_id, f"%{current_day}%"))
        
        # Check if there are results before processing
        posts_results = cursor.fetchall()
        if not posts_results:
            # No approved posts ready - this is normal, not an error
            return {"posts_posted": 0}
        
        posts_to_post = []
        for row in posts_results:
            content_id, platform, content_type, time_str, status, caption, hashtags = row
            
            # Extract scheduled hour
            try:
                time_part = time_str.split()[1]  # Get "9AM" part
                if 'AM' in time_part or 'PM' in time_part:
                    hour = int(time_part.replace('AM', '').replace('PM', ''))
                    if 'PM' in time_part and hour != 12:
                        hour += 12
                    elif 'AM' in time_part and hour == 12:
                        hour = 0
                    
                    # Post if current hour matches scheduled hour OR if past due
                    if current_hour >= hour:
                        posts_to_post.append({
                            "id": content_id,
                            "platform": platform,
                            "content_type": content_type,
                            "caption": caption,
                            "hashtags": hashtags,
                            "is_past_due": current_hour > hour,
                            "strategy_id": strategy_id,
                            "scheduled_time": time_str
                        })
            except Exception as e:
                logger.warning(f"Error parsing time for content {content_id}: {str(e)}")
                continue
        
        # Sort by past due first, then by scheduled time
        posts_to_post.sort(key=lambda x: (not x["is_past_due"], x["id"]))
        
        # Process posts with 5-second delay between past due posts
        posted_count = 0
        posted_posts = []
        
        if posts_to_post:
            logger.info(f"Found {len(posts_to_post)} posts ready for auto-posting from strategy {strategy_id}")
        
        for i, post in enumerate(posts_to_post):
            try:
                
                success = await post_content_automatically(
                    company_id=company_id,
                    post=post,
                    current_user=user
                )
                
                if success:
                    posted_count += 1
                    posted_posts.append({
                        "id": post["id"],
                        "platform": post["platform"],
                        "content_type": post["content_type"],
                        "scheduled_time": post.get("scheduled_time"),
                        "was_past_due": post["is_past_due"]
                    })
                    logger.info(f"Successfully auto-posted content {post['id']}")
                    
                    # Add 5-second delay between past due posts
                    if post["is_past_due"] and i < len(posts_to_post) - 1:
                        await asyncio.sleep(2)
                        
            except Exception as e:
                logger.error(f"Error posting content {post['id']}: {str(e)}")
                continue
        
        if posted_count > 0:
            logger.info(f"Auto-posted {posted_count} posts for company {company_id}")
            
        return {
            "posts_posted": posted_count,
            "posted_posts": posted_posts
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in check_approved_posts: {str(e)}")
        return {"posts_posted": 0, "error": str(e)}
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()    
            

#---------------------------------------------------------------------------------------


# Auto Content posting function
async def post_content_automatically(company_id: int, post: dict, current_user: dict):
    """Automatically post approved content using existing posting functions - Async version"""
    try:
        content_id = post["id"]
        platform = post["platform"].lower()
        content_type = post["content_type"]
        
        # Prepare the caption with hashtags
        full_caption = post["caption"] or ""
        if post["hashtags"]:
            full_caption += " " + post["hashtags"]
        
        # Get database connection
        from config.config import get_db_connection, get_db_cursor, release_db_connection
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        
        try:
            # Get the media URL (Cloudinary URL)
            cursor.execute("""
                SELECT media_link, video_placeholder 
                FROM content_items WHERE id = %s
            """, (content_id,))
            result = cursor.fetchone()
            media_url = result[0] if result else None
            video_url = result[0] if result else None
            
            # Get the stored account credentials from database
            cursor.execute("""
                SELECT platform, account_id, account_name, access_token, page_id, instagram_id
                FROM user_linked_accounts 
                WHERE user_id = %s AND platform IN ('facebook', 'instagram','linkedin')
                ORDER BY created_at DESC
            """, (current_user["user_id"],))
            
            accounts = cursor.fetchall()
            facebook_account = next((acc for acc in accounts if acc[0] == 'facebook'), None)
            instagram_account = next((acc for acc in accounts if acc[0] == 'instagram'), None)
            linkedin_account = next((acc for acc in accounts if acc[0] == 'linkedin'), None)

            if platform == 'facebook' and not facebook_account:
                raise Exception("No Facebook account linked for this user")
            if platform == 'instagram' and not instagram_account:
                raise Exception("No Instagram account linked for this user")
            if platform == 'linkedin' and not linkedin_account:
                raise Exception("No Linkedin account linked for this user")

            success = False
            
            # Encryption For linked meta account
            ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY").encode()
            meta_oauth = MetaOAuth(ENCRYPTION_KEY)
            linkedin_oauth = LinkedInOAuth(ENCRYPTION_KEY)
            
            if platform == 'facebook':
                # Use the Facebook API directly instead of calling the endpoint
                facebook_page_id = facebook_account[4]
                
                encrypted_access_token = facebook_account[3]  # access_token field
                decrypted_fb_access_token = meta_oauth._decrypt_token(encrypted_access_token)
                access_token = decrypted_fb_access_token
                
                if not access_token:
                    raise Exception("Facebook access token not found")
                
                # Map content types to your Facebook posting system
                if 'Image' in content_type:
                    if not media_url:
                        raise Exception("No image URL found for Facebook post")
                    
                    logger.info(f"Posting Facebook image from URL: {media_url}")
                    success = await publish_facebook_image_post(
                        page_id=facebook_page_id,
                        access_token=access_token,
                        image_url=media_url,
                        message=full_caption
                    )
                    
                elif 'Video' in content_type:
                    if not video_url:
                        raise Exception("No video URL found for Facebook post")
                    
                    logger.info(f"Posting Facebook video from URL: {video_url}")
                    success = await publish_facebook_video_post(
                        page_id=facebook_page_id,
                        access_token=access_token,
                        video_url=video_url,
                        title=full_caption[:100],
                        description=full_caption
                    )
                    
                else:  # Text post
                    logger.info(f"Posting Facebook text status: {full_caption}")
                    success = await publish_facebook_text_post(
                        page_id=facebook_page_id,
                        access_token=access_token,
                        message=full_caption
                    )
                
            elif platform == 'instagram':
                # Instagram credentials
                instagram_account_id = instagram_account[5] 
                
                encrypted_access_token = instagram_account[3]  # access_token field
                decrypted_ig_access_token = meta_oauth._decrypt_token(encrypted_access_token)
                access_token = decrypted_ig_access_token
                
                if not access_token:
                    raise Exception("Instagram access token not found")
                
                if 'Feed Image' in content_type:
                    if not media_url:
                        raise Exception("No image URL found for Instagram post")
                    
                    logger.info(f"Posting Instagram feed image from URL: {media_url}")
                    success = await publish_instagram_post(
                        account_id=instagram_account_id,
                        access_token=access_token,
                        image_url=media_url,
                        caption=full_caption
                    )
                    
                elif 'Story' in content_type or 'Stories' in content_type or "Instagram Stories" in content_type:
                    if not media_url:
                        logger.error(f"No media_url found for Instagram story. Content ID: {content_id}")
                        logger.error(f"Database result: media_link={media_url}, video_placeholder={video_url}")
                        raise Exception("No image URL found for Instagram story")
                    
                    logger.info(f"Posting Instagram story from URL: {media_url}")
                    logger.debug(f"Content type check: '{content_type}' contains 'Story' or 'Stories'")
                    
                    success = await publish_instagram_story(
                        account_id=instagram_account_id,
                        access_token=access_token,
                        image_url=media_url
                    )
                    
                elif 'Reel' in content_type:
                    if not video_url:
                        raise Exception("No video URL found for Instagram reel")
                    
                    logger.info(f"Posting Instagram reel from URL: {video_url}")
                    success = await publish_instagram_reel(
                        account_id=instagram_account_id,
                        access_token=access_token,
                        video_url=video_url,
                        caption=full_caption
                    )
                    
            elif platform == 'linkedin':
                # LinkedIn posting logic
                encrypted_access_token = linkedin_account[3] 
                decrypted_li_access_token = linkedin_oauth._decrypt_token(encrypted_access_token)
                access_token = decrypted_li_access_token
                
                if not access_token:
                    raise Exception("LinkedIn access token not found")
                
                # Get LinkedIn user ID
                user_id = f"urn:li:person:{linkedin_account[1]}"
                
                if 'Image' in content_type:
                    if not media_url:
                        raise Exception("No image URL found for LinkedIn post")
                    
                    logger.info(f"Posting image to LinkedIn from URL: {media_url}")
                    success = await publish_linkedin_image_post(
                        access_token=access_token,
                        user_id=user_id,
                        image_url=media_url,
                        text=full_caption
                    )
                    
                elif 'Video' in content_type:
                    if not video_url:
                        raise Exception("No video URL found for LinkedIn post")
                    
                    logger.info(f"Posting video to LinkedIn from URL: {video_url}")
                    success = await publish_linkedin_video_post(
                        access_token=access_token,
                        user_id=user_id,
                        video_url=video_url,
                        text=full_caption
                    )
                    
                else:  # Text post
                    logger.info(f"Posting text to LinkedIn: {full_caption}")
                    success = await publish_linkedin_text_post(
                        access_token=access_token,
                        user_id=user_id,
                        text=full_caption
                    )
            
            if success:
                # Update status to posted
                cursor.execute("""
                    UPDATE content_items 
                    SET status = 'posted'
                    WHERE id = %s
                """, (content_id,))
                conn.commit()
                logger.info(f"Successfully posted content {content_id} to {platform}")
                return True
            else:
                # If posting fails, set back to needs_approval
                cursor.execute("""
                    UPDATE content_items 
                    SET status = 'needs_approval'
                    WHERE id = %s
                """, (content_id,))
                conn.commit()
                logger.error(f"Failed to post content {content_id} to {platform}")
                raise Exception(f"Failed to post content to {platform}")
                
        except Exception as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        error_msg = f"Error in post_content_automatically for content {content_id}: {str(e)}"
        logger.error(error_msg)
        raise e
    finally:
        # Ensure database connection is properly released
        if 'conn' in locals():
            release_db_connection(conn)          