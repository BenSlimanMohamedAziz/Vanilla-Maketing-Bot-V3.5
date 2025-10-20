import asyncio
from fastapi import APIRouter
import aiohttp
import requests
from config.config import settings
from datetime import datetime, timedelta
import logging
from config.config import get_db_connection, get_db_cursor, release_db_connection

# Initialize router
router = APIRouter(
    tags=["scraping_helper"],
    responses={404: {"description": "Not found"}}
)


logger = logging.getLogger(__name__)

# Firecrawl API configuration
FIRECRAWL_API_KEY = settings.FIRECRAWL_API_KEY_3
FIRECRAWL_API_URL = settings.FIRECRAWL_API_URL


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

# Firecrawl Events Scraping
async def scrape_events_firecrawl(company_id: int):
    """Scrape events data using Firecrawl API and store in database"""
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {FIRECRAWL_API_KEY}'
    }
    
    payload = {
        "url": "https://allevents.in/nabeul/all",
        "formats": ["markdown"]
    }
    
    try:
        logger.info(f"Starting Firecrawl event scraping for company {company_id}")
        
        response = requests.post(FIRECRAWL_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or not data.get('success'):
            logger.error(f"Firecrawl API error: {data.get('error', 'Unknown error')}")
            return 0
            
        markdown_content = data.get('data', {}).get('markdown', '')
        
        if not markdown_content:
            logger.warning("No content received from Firecrawl")
            return 0
            
        events_added = await process_firecrawl_events(company_id, markdown_content)
        return events_added
        
    except Exception as e:
        logger.error(f"Error scraping events with Firecrawl: {e}")
        return 0

async def process_firecrawl_events(company_id: int, markdown_content: str) -> int:
    """Process Firecrawl markdown content and extract events"""
    
    events_added = 0
    today = datetime.now().date()
    
    # Split content by lines and look for event patterns
    lines = markdown_content.split('\n')
    
    current_event = {}
    events = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Look for event title patterns (usually bold text with links)
        if line.startswith('[**') and '**]' in line:
            # If we have a previous event being built, save it
            if current_event and current_event.get('title'):
                events.append(current_event)
                current_event = {}
            
            # Extract title and URL
            try:
                title_end = line.find('**]')
                title = line[3:title_end].strip()  # Remove [** and **]
                
                # Extract URL
                url_start = line.find('](https://allevents.in/')
                if url_start != -1:
                    url_end = line.find('"', url_start + 2)
                    if url_end == -1:
                        url_end = line.find(')', url_start + 2)
                    if url_end != -1:
                        event_url = line[url_start + 2:url_end]
                    else:
                        event_url = line[url_start + 2:]
                else:
                    event_url = None
                
                current_event = {
                    'title': title,
                    'event_url': event_url
                }
            except Exception as e:
                logger.error(f"Error parsing event title: {e}")
                continue
        
        # Look for date patterns
        elif line.startswith('- ') and not current_event.get('date_str'):
            # This might be a date line (like "Sat, 15 Nov")
            date_str = line[2:].strip()  # Remove "- "
            current_event['date_str'] = date_str
            
            # Try to parse the date
            event_date = parse_firecrawl_date(date_str)
            if event_date and event_date >= today:
                current_event['event_date'] = event_date
                current_event['date_day'] = event_date.day if event_date else None
                current_event['date_month'] = event_date.strftime('%b').upper() if event_date else None
            else:
                # If date is in past, skip this event
                if event_date and event_date < today:
                    current_event = {}
        
        # Look for location patterns
        elif line and not line.startswith('-') and not line.startswith('[') and not current_event.get('location'):
            # This might be a location line
            current_event['location'] = line
    
    # Don't forget the last event
    if current_event and current_event.get('title'):
        events.append(current_event)
    
    # Insert events into database
    for event in events:
        if not event.get('event_date') or event['event_date'] < today:
            continue
            
        try:
            cursor.execute("""
                INSERT INTO scraped_events (
                    company_id, title, event_date, date_day, date_month, 
                    image_url, event_url, read_more_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                company_id,
                event['title'],
                event.get('event_date'),
                event.get('date_day'),
                event.get('date_month'),
                None,  # Firecrawl doesn't provide image URLs in markdown
                event.get('event_url'),
                event.get('event_url')  # Use same URL for read_more_url
            ))
            
            if cursor.rowcount > 0:
                events_added += 1
                
        except Exception as e:
            logger.error(f"Error inserting Firecrawl event: {e}")
            continue
    
    conn.commit()
    logger.info(f"Added {events_added} new events from Firecrawl for company {company_id}")
    return events_added

def parse_firecrawl_date(date_str: str):
    """Parse date strings from Firecrawl markdown output"""
    try:
        # Remove any extra spaces and normalize
        date_str = ' '.join(date_str.split())
        
        # Common date formats in the markdown
        date_formats = [
            '%a, %d %b',  # "Sat, 15 Nov"
            '%d-%b',       # "15-Nov"
            '%d %b',       # "15 Nov"
        ]
        
        current_year = datetime.now().year
        
        for fmt in date_formats:
            try:
                # Try parsing without year first
                parsed_date = datetime.strptime(date_str, fmt)
                # Add current year
                event_date = parsed_date.replace(year=current_year).date()
                
                # If the event date appears to be in the past, try next year
                if event_date < datetime.now().date():
                    event_date = parsed_date.replace(year=current_year + 1).date()
                
                return event_date
            except ValueError:
                continue
        
        # Try to handle date ranges like "23-25 Oct"
        if '-' in date_str and len(date_str.split('-')) == 2:
            try:
                date_part, month_part = date_str.split('-')
                day_part = date_part.strip().split()[-1] if ' ' in date_part else date_part.strip()
                month_part = month_part.strip()
                
                # Take the first day of the range
                day = int(day_part)
                month_str = month_part[:3].upper()
                
                month_map = {
                    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                }
                
                if month_str in month_map:
                    event_date = datetime(current_year, month_map[month_str], day).date()
                    if event_date < datetime.now().date():
                        event_date = datetime(current_year + 1, month_map[month_str], day).date()
                    return event_date
            except (ValueError, IndexError):
                pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return None    