import logging
import re
import asyncio
from fastapi import logger
from groq import AsyncGroq
import aiohttp
from config.config import settings
from datetime import datetime, timedelta

# Initialize Async Groq client
GROQ_API_KEY = settings.GROQ_API_KEY_3
client = AsyncGroq(api_key=GROQ_API_KEY)

logger = logging.getLogger(__name__)
   

# current date/time formatted
async def get_current_datetime() -> str:
    now = datetime.now()
    formatted_date = now.strftime("%m/%d/%Y %H:%M")
    return formatted_date

async def clean_html_response(content: str) -> str:
    """
    Clean the AI response by removing markdown code blocks and extra formatting
    """
    # Remove ```html and ``` markers
    content = re.sub(r'```html\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'```', '', content)
    
    # Remove any leading/trailing whitespace
    content = content.strip()
    
    # Ensure content starts with <section
    if not content.startswith('<section'):
        # Find the first <section tag
        section_match = re.search(r'<section.*?>', content, re.DOTALL)
        if section_match:
            start_index = content.find(section_match.group())
            content = content[start_index:]
    
    return content   
    
async def generate_event_strategy(summary_part: str, budget_part: str, company_data, events_text, current_date, events_list):
    """
    Generate an event participation strategy focusing on the most relevant events
    """
    # Current Date
    current_time = await get_current_datetime()
 
    prompt = f"""
    IMPORTANT: You are my personal marketing strategist working directly for my company {company_data['name']}, Here's the logo {company_data.get('logo_url', '')}
    (this will be used for making a COMPLETE marketing events for our company). 
    Also as Event Strategy Director for {company_data['name']}, create a HIGHLY TARGETED 
    event participation plan focusing on ONLY 4 events that will deliver maximum value.

⚠️ CRITICAL EVENT CONTEXT:
    - This is PART 4 of a 7-part monthly strategy generated on {current_date.strftime('%B %d, %Y')} so the start date of the whole strategy and this section is {current_date.strftime('%B %d, %Y')}
    - You are creating the EVENT PARTICIPATION STRATEGY section
    - All event activities must be executable within this specific 30-day period
    - This builds upon Executive Summary (Part 1) and Budget Plan (Part 2)
    
    📋 PREVIOUS SECTIONS FOR CONTEXT, also, to read them, learn and understand:
    ═══════════════════════════════════════════════════════════════
    
    PART 1 - EXECUTIVE SUMMARY:
    {summary_part}
    
    ─────────────────────────────────────────────────────────────
    
    PART 2 - BUDGET PLAN:
    {budget_part}

    ════════════════════════════════════════════════════════════════

    === COMPANY CONTEXT ===
    🏢 Company: {company_data['name']}
    🏢 Slogan: {company_data['slogan']}
    🏢 DESCRIPTION: {company_data['description']}
    🎯 Audience: {company_data.get('target_audience_types', 'Not specified')}
    🏆 Goals: {company_data.get('marketing_goals', '')}
    💰 Budget: ${company_data.get('monthly_budget', 'N/A')}
    🗓 Current Date: {current_date}
    === AVAILABLE EVENTS ===
    {events_text}

    === STRATEGY REQUIREMENTS ===
    1. SELECTION: Choose ONLY 4 events with strongest alignment to:
       - Our target audience
       - Marketing goals
       - Budget considerations
        - STAYS WITHIN budgets allocated in Part 2 and Company Budget: ${company_data.get('monthly_budget', 'N/A')}
    2. For EACH selected event provide:
       a. DATE & LOCATION: Exact details (From the {events_text} )
       b. STRATEGIC VALUE: 2 specific benefits for us
       c. PARTICIPATION PLAN: Concrete action steps
       d. UNIQUE ANGLES: Different approaches for each event
    3. FORMATTING: Use bullet points for clarity
    4. For coins, money, prices and budget make sure it's always in TND

    === OUTPUT FORMAT ===
        <section class="event-strategy">
                      <h2>Event Participation Strategy</h2>
                        <div>
                          {events_text}
                            [For each relevant event:
                            - Extract Event Title
                            - Extract the Date and Place
                            - Why this event matters for my company and benefits
                            - How to participate effectively + activities
                            ]
                        </div>
                    </section>


    === FINAL INSTRUCTIONS ===
    1. BE SELECTIVE: Only include 4 events
    2. ONLY includes events occurring between {current_date.strftime('%B %d')} and {(current_date + timedelta(days=30)).strftime('%B %d')} and SUPPORTS the objectives outlined in Part 1 (Executive Summary) and Delivers measurable results within the 30-day timeframe
    3. BE SPECIFIC: Exact dates, locations, and actions
    4. BE STRATEGIC: Clear business rationale for each
    5. FORMAT: ONLY return the HTML block above
    6. NO DISCLAIMERS: Just the event strategy
    7. If {events_text} empty or no events and No upcoming events identified then take a look at this list of event :{events_list} and choose like 5 and update their dates to current and future dates starting from todays date: {current_time}
    and don't make the future dates too far from current date, and for these events when you choose them and add them make sure its the same format and style same and identical the to the html code and the formating from  === STRATEGY REQUIREMENTS === and 
    === OUTPUT FORMAT === i gave them to you earlier and the date when adding the event must be in this form: "Date & Location: 23 May 2025 – Location" the month name must be its long whole name
    8. Be real and logical and follow the company profile and theme to give accurate added values and plans and angles.
    9. the final result must strictly look like this example : 
    <section class="event-strategy">
        <h2>Event Participation Strategy</h2>
            <div class="event">
                <h3>1. Expo Osaka 2025 – Tunisian Pavilion (Awarded by BIE)</h3>
                    <ul>
                    <li>
                        <strong>Date &amp; Location:</strong>
                        13 April 2025 – Osaka, Japan (International Expo Grounds)
                    </li>

                    <li>
                        <strong>Strategic Value:</strong>
                        <ul>
                        <li>Direct exposure to 1 M+ international visitors, many of whom are avid sports fans and tech-savvy consumers.</li>
                        <li>Leverage the prestige of a BIE-awarded pavilion to boost brand credibility and attract media coverage in Asian markets.</li>
                        </ul>
                    </li>

                    <li>
                        <strong>Participation Plan:</strong>
                        <ul>
                        <li>Reserve a branded activation zone within the Tunisian pavilion – budget ≈ 2000 TND.</li>
                        <li>Design an interactive “Live-Score Wall” that streams real-time sports scores, allowing visitors to engage via QR-code-linked giveaways (e.g., limited-edition TT caps).</li>
                        <li>Host a 15-minute “Fan-Zone” mini-talk featuring a local sports influencer discussing upcoming tournaments and how TT enhances fan experience.</li>
                        <li>Capture visitor data through a quick-scan contest; follow up with personalized email offers post-event.</li>
                        </ul>
                    </li>

                    <li>
                        <strong>Unique Angle:</strong>
                        Position TT as the “Official Digital Companion” for sports fans attending the Expo,
                        emphasizing real-time engagement and cross-cultural community building.
                    </li>
                    </ul>
            </div>
    </section>
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
        
        # Clean the response to remove markdown formatting
        cleaned_content = await clean_html_response(content)
        print(events_text)
        return cleaned_content
    
    except Exception as e:
        logger.error(f"Failed to generate event strategy: {str(e)}")
        raise Exception(f"Event strategy generation failed: {str(e)}")