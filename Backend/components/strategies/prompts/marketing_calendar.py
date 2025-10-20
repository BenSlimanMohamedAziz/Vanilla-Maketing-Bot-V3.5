import asyncio
from groq import AsyncGroq
from config.config import settings
from datetime import datetime, timedelta
from config.config import get_db_connection, get_db_cursor, release_db_connection
import logging

logger = logging.getLogger(__name__)

# Initialize Async Groq client
GROQ_API_KEY = settings.GROQ_API_KEY_2
client = AsyncGroq(api_key=GROQ_API_KEY)

async def get_season(month):
    if 3 <= month <= 5: return "Spring"
    elif 6 <= month <= 8: return "Summer"
    elif 9 <= month <= 11: return "Autumn"
    else: return "Winter"

async def get_relevant_events(company_id, limit=4):
    """Get relevant upcoming events for a company"""
    loop = asyncio.get_event_loop()
    
    def db_operation():
        conn = get_db_connection()
        cursor = get_db_cursor(conn)
        
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
        
        release_db_connection(conn)
        return events
    
    return await loop.run_in_executor(None, db_operation)

def format_events_text(events):
    """Format events data into text for the prompt"""
    if not events:
        return "No upcoming events found"
    
    formatted = []
    for event in events:
        formatted.append(f"- {event['title']} (Date: {event['date']}) [URL: {event['url']}]")
    
    return "\n".join(formatted)

async def generate_marketing_calendar(summary_part: str, budget_part: str, events_marketing_part: str, company_data, current_date, logo_description, company_id):
    """Generate a comprehensive marketing calendar with events, influencer collabs, and ad campaigns"""
    current_season = await get_season(current_date.month)
    
    # Get relevant events asynchronously
    relevant_events = await get_relevant_events(company_id)
    events_text = format_events_text(relevant_events)
    
    # Format target audience
    target_audience = f"""
    - Age Groups: {company_data.get('target_age_groups', 'Not specified')}
    - Audience Types: {company_data.get('target_audience_types', 'Not specified')}
    - Business Types: {company_data.get('target_business_types', 'Not specified')}
    - Geographic Targets: {company_data.get('target_geographics', 'Not specified')}
    """
    
    prompt = f"""
    IMPORTANT: You are my personal marketing strategist working directly for my company {company_data['name']}. 
    Logo Description: {logo_description}
    
    Generate a COMPREHENSIVE marketing calendar that aligns with our brand and current {current_season} season.

⚠️ CRITICAL CALENDAR CONTEXT:
    - This is PART 3 of a 7-part monthly strategy generated on {current_date.strftime('%B %d, %Y')} so the start date of the whole strategy and this CALENDAR/Planning/Blueprint is {current_date.strftime('%B %d, %Y')}
    - You are creating the MARKETING CALENDAR section
    - ALL activities must be scheduled between {current_date.strftime('%B %d, %Y')} and {(current_date + timedelta(days=30)).strftime('%B %d, %Y')}
    - This is a 30-day calendar, NOT a quarterly or full season calendar
    - End date is {(current_date + timedelta(days=30)).strftime('%B %d, %Y')}, NOT {current_date.strftime('%B')} 31st
    - Break down into 4 weekly blocks + final 2-3 days
    - This builds upon Executive Summary (Part 1) and Budget Plan (Part 2) and PART 2B - EVENT MARKETING here are the PREVIOUS SECTIONS so you read them, learn and understand and FOR CONTEXT:
    
    PART 1 - EXECUTIVE SUMMARY:
    {summary_part}
    
    ─────────────────────────────────────────────────────────────
    
    PART 2 - BUDGET PLAN:
    {budget_part}
    
    ─────────────────────────────────────────────────────────────
    
    PART 2B - EVENT MARKETING STRATEGY:
    {events_marketing_part}
    
    ═══════════════════════════════════════════════════════════════
    
    👉 YOUR TASK: Create a detailed 30-day marketing calendar that:
       - IMPLEMENTS the objectives from Part 1 (Executive Summary)
       - STAYS WITHIN the budget allocated in Part 2
       - INCORPORATES the event strategies from Part 2B
       - Distributes activities evenly across the 4 weeks
       - Uses EXACT dates within the 30-day window
       
    STRATEGIC FOUNDATION:
    1. SEASONAL LEVERAGE: Capitalize on {current_season} trends
    2. EVENT INTEGRATION: These confirmed events must be incorporated:
       {events_text} or {events_marketing_part}
    3. AUDIENCE FOCUS: Target these segments:
       {target_audience}

    This is the COMPANY PROFILE:
    Name: {company_data['name']}
    Slogan: {company_data.get('slogan', '')}
    Description: {company_data.get('description', '')}
    Products: {company_data.get('products', '')}
    Services: {company_data.get('services', '')}
    Target Audience: {target_audience}
    Platforms: {company_data['preferred_platforms']}
    Special Events: {company_data.get('special_events', '')}
    Brand Tone: {company_data['brand_tone']}
    Budget: {company_data.get('monthly_budget', '')}
    Marketing Goals: {company_data.get('marketing_goals', '')}
    Current Date: {current_date.strftime('%Y-%m-%d')}
    Season: {current_season}

    REQUIREMENTS:
    1. Create a DETAILED monthly marketing calendar starting from {current_date.strftime('%B %Y')}
    2. Include ALL these activity types:
       - Event participation
       - Influencer/partner collaborations
       - Advertising campaigns
       - Content distribution
       - Seasonal promotions
       - Product launches/updates
    3. For EACH activity, specify:
       - Exact dates or date ranges
       - Activity type
       - Detailed description
       - Required preparation
       - Key performance indicators
    4. Incorporate these upcoming events: {events_text}
    5. Ensure ALL activities match our brand tone and target audience
    6. For any coins, money or budget or prices make sure it's always in TND

    OUTPUT FORMAT (STRICT HTML):

    <section class="marketing-calendar">
        <h1>{company_data['name']} {current_season} Marketing Blueprint ({current_date.strftime('%b-%Y')} to {(current_date + timedelta(days=90)).strftime('%b-%Y')})</h1>
        <div class="seasonal-context">
            <h3>Capitalizing on {current_season}:</h3>
            <p>seasonal_opportunities</p>
        </div>
        <table class="calendar-grid">
            <thead>
                <tr>
                    <th>Dates</th>
                    <th>Campaign Theme</th>
                    <th>Key Actions</th>
                    <th>Collaborations</th>
                    <th>Platforms</th>
                    <th>KPI Targets</th>
                </tr>
            </thead>
            <tbody>
                <!-- 8 weeks of detailed activities -->
                [WEEKLY ENTRIES HERE]
            </tbody>
        </table>
    </section>

    FINAL INSTRUCTIONS:
    - Return ONLY the HTML output
    - Include specific dates based on current date
    - Make all descriptions actionable and specific
    - Ensure consistent brand voice throughout
    - Seamlessly integrate events: {events_text}
    - Maintain exact HTML structure
    - No additional explanations
    """

    try:
        completion = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=4096,
            top_p=1,
            stream=False,
            stop=None
        )
        
        content = completion.choices[0].message.content
        return content
        
    except Exception as e:
        logger.error(f"Failed to generate marketing calendar: {str(e)}")
        raise Exception(f"Marketing calendar generation failed: {str(e)}")