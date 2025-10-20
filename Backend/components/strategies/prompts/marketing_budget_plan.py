import re
import asyncio
import aiohttp
from groq import AsyncGroq
from config.config import settings
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Initialize Async Groq client
GROQ_API_KEY = settings.GROQ_API_KEY_7
TAVILY_API_KEY = settings.TAVILY_API_KEY_3
client = AsyncGroq(api_key=GROQ_API_KEY)

def get_season(month):
    if 3 <= month <= 5: return "Spring"
    elif 6 <= month <= 8: return "Summer"
    elif 9 <= month <= 11: return "Autumn"
    else: return "Winter"

async def search_marketing_budget_insights(company_name: str, description: str, company_slogan: str) -> Optional[str]:
    """
    Search for marketing budget insights
    """
    try:
        tavily_url = "https://api.tavily.com/search"
        
        search_queries = [
            f"marketing budget allocation",
            f"content creation costs Tunisia",
            f"social media advertising costs Tunisia",
            f"influencer marketing pricing Tunisia",
            f"event sponsorship costs Tunisia"
        ]
        
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for query in search_queries:
                payload = {
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": 2
                }
                
                task = session.post(tavily_url, json=payload, timeout=aiohttp.ClientTimeout(total=30))
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, Exception):
                    logger.error(f"Search request failed: {response}")
                    continue
                    
                try:
                    async with response as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        if data.get('results'):
                            for result in data['results']:
                                all_results.append(result.get('content', ''))
                except Exception as e:
                    logger.error(f"Failed to process response: {e}")
        
        if all_results:
            return " | ".join(all_results)[:1000]
        
        return None
        
    except Exception as e:
        logger.error(f"Budget search failed: {str(e)}")
        return None

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

async def generate_budget_plan(summary_part: str, company_data: Dict[str, Any], current_date: datetime, relevant_events: str) -> str:
    """
    Generate marketing budget allocation plan
    """
    current_season = get_season(current_date.month)
    
    # Format target audience
    target_audience = f"""
    - Age Groups: {company_data.get('target_age_groups', 'Not specified')}
    - Audience Types: {company_data.get('target_audience_types', 'Not specified')}
    - Business Types: {company_data.get('target_business_types', 'Not specified')}
    - Geographic Targets: {company_data.get('target_geographics', 'Not specified')}
    """
    
    # Get company details
    company_name = company_data['name']
    description = company_data.get('description', 'general')
    monthly_budget_str = company_data.get('monthly_budget', '')
    company_slogan= company_data.get('slogan', '')
    
    # Perform web search for budget insights
    budget_insights = await search_marketing_budget_insights(
        company_name, description, company_slogan
    )
    
    #Test
    print (budget_insights)

    prompt = f"""
    IMPORTANT: You are the Chief Marketing Strategist for {company_name}.
    
    Create a professional marketing budget allocation plan for {current_date.strftime('%B %Y')}.

    COMPANY PROFILE:
    Name: {company_name}
    Slogan: {company_data.get('slogan', '')}
    Description: {company_data.get('description', '')}
    Website: {company_data.get('website', '')}
    Products: {company_data.get('products', '')}
    Services: {company_data.get('services', '')}
    Target Audience: {target_audience}
    Preferred Platforms: {company_data['preferred_platforms']}
    Brand Tone: {company_data['brand_tone']}
    Marketing Goals: {company_data.get('marketing_goals', '')}
    Monthly Budget: {monthly_budget_str}
    Special Events: {company_data.get('special_events', '')}
    Current Season: {current_season}
    Relevant Events: {relevant_events}
    

    {f'BUDGET Ideas from the search tool to help : {budget_insights}' if budget_insights else ''}

⚠️ CRITICAL BUDGET CONTEXT:
    - This is PART 2 of a 7-part monthly strategy generated on {current_date.strftime('%B %d, %Y')} so the start date of this is {current_date.strftime('%B %d, %Y')}
    - You are creating the BUDGET ALLOCATION section
    - This budget covers ONLY the next 30 days: {current_date.strftime('%B %d')} - {(current_date + timedelta(days=30)).strftime('%B %d')}
    - All spending must be planned for this specific 30-day period
    - Budget allocations should support activities spanning these exact 4 weeks
    - This builds upon the Executive Summary (Part 1) already created - FOR CONTEXT you can here read and learn about part 1 Executive Summary (Part 1) : {summary_part}

    
    REQUIREMENTS:
    - Allocate the entire {monthly_budget_str} budget across exactly 4 categories
    - Categories must be: Content Creation & Production, Social Media Advertising, Influencer Partnerships, Event Sponsorships
    - Ensure percentages total 100%
    - All amounts must be in TND
    - Consider {current_season} season and company's marketing goals
    - Use realistic Tunisia market pricing

    OUTPUT FORMAT (STRICT HTML):

    <section class="marketing-budget">
        <h2>Budget Allocation (Total {monthly_budget_str} TND):</h2>
        <h3>Recommended Spending:</h3>
        <table>
            <tr>
                <th>Category</th>
                <th>Percentage</th>
                <th>Amount</th>
            </tr>
            <tr>
                <td>Content Creation & Production (Mention type of content and what productions)</td>
                <td>[percentage]%</td>
                <td>[amount TND]</td>
            </tr>
            <tr>
                <td>Social Media Advertising (Mention the Preferred Platforms)</td>
                <td>[percentage]%</td>
                <td>[amount TND]</td>
            </tr>
            <tr>
                <td>Influencer Partnerships</td>
                <td>[percentage]%</td>
                <td>[amount TND]</td>
            </tr>
            <tr>
                <td>Event Sponsorships (Mention Events use the Relevant Events: {relevant_events})</td>
                <td>[percentage]%</td>
                <td>[amount TND]</td>
            </tr>
        </table>
    </section>
    
    [budget breakdown (4 Main Categories, and also use the Relevant Events: {relevant_events}, the infleuncers are the one that will get the highest percentage like 50%,
    also make sure you use most of the budget ]
    
    FINAL INSTRUCTIONS:
    - Return ONLY the HTML above
    - Fill in percentages and amounts based on company profile and market research
    - Ensure professional, realistic allocations
    - Maintain exact HTML structure
    - Only generate the table nothing more
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
            temperature=0.4,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
            stop=None
        )
        
        content = completion.choices[0].message.content
        
        # Clean the response to remove markdown formatting
        cleaned_content = await clean_html_response(content)
        
        return cleaned_content
        
    except Exception as e:
        logger.error(f"Failed to generate budget plan: {str(e)}")
        raise Exception(f"Budget plan generation failed: {str(e)}")