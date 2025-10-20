# Imports

import io
import os
import uuid
import numpy as np
import requests
import shutil
import asyncio
import logging
from typing import Optional, List, Tuple
from collections import Counter
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sklearn.cluster import KMeans
import concurrent.futures

# Config db
from config.config import get_db_cursor, get_db_connection, release_db_connection

# Add Groq imports
import logging
from groq import AsyncGroq
from config.config import settings

# Logo description
from components.helpers.image_analyzer import get_logo_description 

# Set up logging
logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive operations
image_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Groq client for AI text generation
GROQ_API_KEY = settings.GROQ_API_KEY_3
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# === DB Setup ===
conn = get_db_connection()
cursor = get_db_cursor(conn)

#---------------------------------------------------------------------------------------


# Class
class UniversalSocialFramer:
    """
    Builds frames for social media posts with dynamic colors from logo:
    - Dynamic canvas sizes based on platform
    - Side rails using dominant logo color (optional based on platform)
    - White content area
    - Logo placement
    - Text overlay with drop shadow on main image with rounded corners
    - All images with rounded corners
    """
    
#---------------------------------------------------------------------------------------
    
    # Init
    
    def __init__(self):
        # Initialize color variables (will be set from logo analysis)
        self.BRAND_ColorDom = None   # Dominant color from logo
        self.BRAND_ColorSec = None   # Secondary color from logo
        self.additional_colors = []  # For logos with more than 2 colors
        self.TEXT_DARK = (60, 60, 60, 255)     # dark gray for text
        self.TEXT_LIGHT = (120, 120, 120, 255) # light gray for subtle text
        self.CORNER_RADIUS = 15      # 15px rounded corners

#---------------------------------------------------------------------------------------


    # -------- Platform-specific dimensions --------
    def get_platform_dimensions(self, platform, content_type):
        """Return appropriate dimensions for each platform and content type"""
        if platform in ["Instagram", "instagram"]:
            if content_type in ["feed", "image post", "post", "Image Posts", "Feed Image Posts", "Instagram Feed", "Instagram Feed Image Posts"]:
                return (1080, 1080)  # Square 1:1
            elif content_type in ["Instagram Stories", "stories", "story", "instagram stories", "Stories", "Story"]:
                return (1080, 1920)  # Vertical 9:16
        elif platform in ["Facebook", "facebook"]:
            if content_type in ["image", "post", "Image Posts", "image post", "Facebook Image Posts"]:
                return (1200, 1500)  # 4:5 aspect ratio
        elif platform in ["LinkedIn", "linkedIn", "linkedin"]:
            if content_type in ["image", "post", "Image Posts", "image post", "LinkedIn Image Posts", "linkedIn Image Posts"]:
                return (1200, 1350)  # Portrait
        
        # Default to square if no specific dimensions found
        return (1200, 1200)


    # -------- Color Detection Utilities --------
    def _get_dominant_colors(self, img: Image.Image, num_colors: int = 3) -> List[Tuple[int, int, int, int]]:
        """Extract dominant colors from logo using K-means clustering."""
        img = img.convert("RGBA")
        resize_factor = 100 / min(img.size)
        small_img = img.resize(
            (int(img.width * resize_factor), int(img.height * resize_factor)),
            Image.Resampling.LANCZOS
        )
        
        arr = np.array(small_img)
        arr = arr.reshape((-1, 4))
        arr = arr[arr[:, 3] > 200]  # Filter out transparent pixels
        
        if len(arr) < num_colors:
            return [(0, 179, 173, 255), (44, 27, 71, 255)]  # Fallback colors
        
        rgb = arr[:, :3]
        kmeans = KMeans(n_clusters=num_colors, random_state=42)
        kmeans.fit(rgb)
        
        counts = Counter(kmeans.labels_)
        sorted_colors = sorted(
            [(color, count) for color, count in zip(kmeans.cluster_centers_, counts.values())],
            key=lambda x: -x[1]
        )
        
        return [(int(r), int(g), int(b), 255) for (r, g, b), _ in sorted_colors]

    # -------- Setting color --------
    def _set_colors_from_logo(self, logo_image: Image.Image):
        """Analyze logo and set color variables."""
        colors = self._get_dominant_colors(logo_image)
        
        if len(colors) >= 1:
            self.BRAND_ColorDom = colors[0]
        else:
            self.BRAND_ColorDom = (0, 179, 173, 255)  # Fallback teal
            
        if len(colors) >= 2:
            self.BRAND_ColorSec = colors[1]
        else:
            self.BRAND_ColorSec = (44, 27, 71, 255)  # Fallback purple
            
        if len(colors) > 2:
            self.additional_colors = colors[2:]


    # -------- Image Processing Utilities --------
    def _add_rounded_corners(self, img: Image.Image, radius: int = 15) -> Image.Image:
        """Add rounded corners to an image with transparency."""
        # Create a mask for rounded corners
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        
        # Draw white rounded rectangle on black background
        draw.rounded_rectangle([(0, 0), img.size], radius, fill=255)
        
        # Apply the mask to the image
        result = img.copy()
        result.putalpha(mask)
        
        return result


    # -------- Advanced Text Overlay --------
    def _add_text_with_drop_shadow(self, frame: Image.Image, x: int, y: int, width: int, height: int, text: str, 
                                   text_color: tuple = (255, 255, 255, 255), 
                                   shadow_color: tuple = (0, 0, 0, 176),
                                   shadow_offset: tuple = (5, 5),
                                   shadow_blur: int = 3,
                                   overlay_opacity: float = 0.10):
        """
        Add text with multiple enhancement techniques for maximum visibility
        """
        # Create overlay that matches the frame size
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw light overlay with rounded corners
        overlay_color = (241, 238, 233, int(255 * overlay_opacity))
        overlay_draw.rounded_rectangle(
            [x, y, x + width, y + height], 
            radius=self.CORNER_RADIUS,
            fill=overlay_color
        )
        
        # Composite overlay onto frame
        frame_with_overlay = Image.alpha_composite(frame.convert("RGBA"), overlay)
        frame.paste(frame_with_overlay, (0, 0))
        
        # Calculate font size based on image dimensions
        base_font_size = max(32, min(width, height) // 18)
        font = self.get_font(base_font_size, bold=True)
        
        # Create a temporary image for text effects
        temp_img = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Get text dimensions for centering
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate text position (centered)
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2
        
        # Add multiple shadow layers for depth
        shadow_layers = [
            ((7, 7), (0, 0, 0, 180), 5),    # Far shadow
            ((5, 5), (0, 0, 0, 200), 3),    # Mid shadow
            ((3, 3), (0, 0, 0, 220), 2),    # Near shadow
        ]
        
        for offset, color, blur in shadow_layers:
            shadow_temp = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_temp)
            
            shadow_x = text_x + offset[0]
            shadow_y = text_y + offset[1]
            shadow_draw.text((shadow_x, shadow_y), text, font=font, fill=color)
            
            if blur > 0:
                shadow_temp = shadow_temp.filter(ImageFilter.GaussianBlur(radius=blur))
            
            temp_img = Image.alpha_composite(temp_img, shadow_temp)
        
        # Redraw for final text
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Add stroke outline
        stroke_width = max(3, base_font_size // 12)
        stroke_color = (0, 0, 0, 255)
        temp_draw.text((text_x, text_y), text, font=font, fill=stroke_color, 
                      stroke_width=stroke_width, stroke_fill=stroke_color)
        
        # Final white text on top
        enhanced_text_color = (255, 255, 255, 255)
        temp_draw.text((text_x, text_y), text, font=font, fill=enhanced_text_color)
        
        # Apply sharpening
        temp_img = temp_img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=2))
        
        # Composite onto frame
        frame_with_text = Image.alpha_composite(frame.convert("RGBA"), temp_img)
        frame.paste(frame_with_text, (0, 0))


    # -------- Utilities --------
    async def download_image_async(self, url: str) -> Image.Image:
        """Async image download"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.get(url, stream=True, timeout=30)
        )
        response.raise_for_status()
        
        img_data = await loop.run_in_executor(
            None,
            lambda: Image.open(io.BytesIO(response.content))
        )
        return img_data.convert("RGBA")

    # Fit
    def _fit_inside_box(self, img: Image.Image, box_w: int, box_h: int) -> Image.Image:
        """Resize img to fit within (box_w, box_h) preserving aspect ratio."""
        iw, ih = img.size
        img_ratio = iw / ih
        box_ratio = box_w / box_h

        if img_ratio > box_ratio:
            new_w = box_w
            new_h = int(new_w / img_ratio)
        else:
            new_h = box_h
            new_w = int(new_h * img_ratio)

        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Getting Font
    def get_font(self, size: int = 20, bold: bool = False):
        """Get default font with fallbacks"""
        try:
            return ImageFont.truetype("arial.ttf" if not bold else "arialbd.ttf", size)
        except:
            try:
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except:
                return ImageFont.load_default()


    # -------- Frame builder --------
    # -------- Frame builder --------
    async def build_frame_with_elements(
        self,
        main_image: Image.Image,
        logo_image: Image.Image,
        platform: str,
        content_type: str,
        company_id: int,  # Add company_id parameter
        overlay_text: str = " ",
        rail_w: int = 44,
        top_margin: int = 20,
        bottom_margin: int = 60,
        inner_pad_x: int = 40,
    ) -> Image.Image:
        """Create complete framed post with dynamic colors from logo."""
        # First analyze the logo to set our brand colors
        self._set_colors_from_logo(logo_image)
        
        # Get platform-specific dimensions
        W, H = self.get_platform_dimensions(platform, content_type)
        frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(frame)

        # Add side rails for LinkedIn and Facebook, but not for Instagram Stories
        
        draw.rectangle((0, 0, rail_w, H), fill=self.BRAND_ColorDom)
        draw.rectangle((W - rail_w, 0, W, H), fill=self.BRAND_ColorDom)

        # Calculate content area
        logo_height_space = 160  # Fixed height for logo area (like original test code)
        content_x = rail_w + inner_pad_x
        content_y = top_margin + logo_height_space
        content_w = W - 2 * (rail_w + inner_pad_x)
        content_h = H - content_y - bottom_margin - 40

        # Prepare and fit main image with rounded corners
        main_rgba = main_image.convert("RGBA")
        fitted_main = self._fit_inside_box(main_rgba, content_w, content_h)
        fitted_main = self._add_rounded_corners(fitted_main, self.CORNER_RADIUS)

        # Paste main image centered
        main_paste_x = content_x + (content_w - fitted_main.width) // 2
        main_paste_y = content_y + (content_h - fitted_main.height) // 2
        frame.paste(fitted_main, (main_paste_x, main_paste_y), fitted_main)

        # Add light overlay with enhanced text visibility (skip for Instagram Stories)
        if overlay_text:
            self._add_text_with_drop_shadow(
                frame, 
                main_paste_x, 
                main_paste_y, 
                fitted_main.width, 
                fitted_main.height, 
                overlay_text,
                text_color=(255, 255, 255, 255),  # Pure white text
                shadow_color=(0, 0, 0, 176),      # Strong black shadow
                shadow_offset=(5, 5),             # Larger shadow offset
                shadow_blur=3,                    # More shadow blur
                overlay_opacity=0.10              # Light overlay opacity
            )

        # Add logo to top-left (skip for Instagram Stories to avoid clutter)
        
            # Make logo bigger like in the original test code
        max_logo_w = int(W * 0.55)  # 55% of width (like original test code)
        max_logo_h = logo_height_space
        logo_rgba = logo_image.convert("RGBA")
        logo_fitted = self._fit_inside_box(logo_rgba, max_logo_w, max_logo_h)
        logo_x = rail_w + inner_pad_x
        frame.paste(logo_fitted, (logo_x, top_margin), logo_fitted)

        # Add website in bottom right (skip for Instagram Stories)
        
        bottom_y = H - bottom_margin + 10
        website_font = self.get_font(30)  # Larger font like original
        # website_text = "nearshorepublic.com"
        # Get website from database
        cursor.execute("SELECT website FROM companies WHERE id = %s", (company_id,))
        company_data = cursor.fetchone()
        website_text = company_data[0] if company_data and company_data[0] else "CompanySite.com"
    
            # Calculate position for right alignment
        bbox = draw.textbbox((0, 0), website_text, font=website_font)
        website_x = W - rail_w - inner_pad_x - (bbox[2] - bbox[0])
        draw.text((website_x, bottom_y), website_text, font=website_font, fill=self.BRAND_ColorDom)

        return frame

    # -------- High-level helper --------
    async def create_post_from_images(
        self,
        main_image: Image.Image,
        logo_image: Image.Image,
        platform: str,
        content_type: str,
        company_id: int,
        overlay_text: str = " ",
    ) -> Image.Image:
        """High-level async method to create framed post"""
        return await self.build_frame_with_elements(
            main_image, logo_image, platform, content_type, company_id, overlay_text
        )


# Text Overlay for the image
async def generate_overlay_text(company_id: int, cursor) -> str:
    """
    Generate a dynamic 4-word overlay text based on company profile - Async and non-blocking
    """
    try:
        logger.info(f"Generating overlay text for company_id: {company_id}")
        
        # Fetch company data from database
        cursor.execute("""
            SELECT name, slogan, description, website, products, services,
                   marketing_goals, target_age_groups, target_audience_types,
                   target_business_types, target_geographics, preferred_platforms, 
                   special_events, brand_tone, monthly_budget, logo_url
            FROM companies 
            WHERE id = %s
        """, (company_id,))
        
        company_data = cursor.fetchone()
        if not company_data:
            logger.warning(f"Company not found for ID: {company_id}, using fallback text")
            return "Quality Service Excellence"
        
        # Unpack company data
        (name, slogan, description, website, products, services, 
         marketing_goals, target_age_groups, target_audience_types,
         target_business_types, target_geographics, preferred_platforms, 
         special_events, brand_tone, monthly_budget, logo_url) = company_data
        
        # Get logo description
        logo_description = get_logo_description(logo_url) if logo_url else "No logo"
        
        # Build target audience string
        target_audience = f"""
        - Age Groups: {target_age_groups or 'Not specified'}
        - Audience Types: {target_audience_types or 'Not specified'}
        - Business Types: {target_business_types or 'Not specified'}
        - Geographic Targets: {target_geographics or 'Not specified'}
        """
        
        # Create company profile for AI
        company_profile = f"""
        - COMPANY PROFILE - INFO: 
        {{
            "NAME": "{name}", 
            "SLOGAN": "{slogan or ''}",
            "DESCRIPTION": "{description or ''}",
            "WEBSITE": "{website or ''}",
            "PRODUCTS": "{products or ''}",
            "SERVICES": "{services or ''}",
            "TARGET AUDIENCE": {target_audience},
            "PLATFORMS": "{preferred_platforms or ''}",
            "SPECIAL EVENTS": "{special_events or ''}", 
            "BRAND TONE": "{brand_tone or ''}",
            "BUDGET": "{monthly_budget or ''}",
            "MARKETING GOALS": "{marketing_goals or ''}",
            "LOGO": "{logo_url or 'No logo'}",
            "LOGO Description": "{logo_description}"
        }}
        """
        
        # Create AI prompt
        prompt = f"""
        Based on the following company profile, generate a compelling 4-word overlay text for a social media post image.

        {company_profile}

        Requirements:
        - EXACTLY 4 words maximum
        - Catchy and engaging
        - Creative phrases like "join us", "enhance your experience", "discover more with [company]", Be creative use more creative phrases, use phrases about AI but not always and don't spam it, also stuff like "Partner With Us", "Follow Us" and more.
        - Reflects the company's brand and services
        - Suitable for social media overlay
        - Professional but memorable
        - Action-oriented when possible

        Generate only the 4-word text, nothing else.
        """
        
        # Call Groq API asynchronously (FIXED - no run_in_executor needed for AsyncGroq)
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=16,
            top_p=1,
            stream=False,
            stop=None
        )
        
        # Extract and clean the response
        overlay_text = completion.choices[0].message.content.strip()
        
        # Validate the response (ensure it's roughly 4 words)
        words = overlay_text.split()
        if len(words) > 6:  # Allow some flexibility but cap it
            overlay_text = " ".join(words[:4])
        elif len(words) < 2:  # If too short, use fallback
            overlay_text = f"Discover {name}" if name else "Quality Service Excellence"
        
        logger.info(f"Generated overlay text: '{overlay_text}'")
        return overlay_text
        
    except Exception as e:
        logger.error(f"Failed to generate overlay text: {str(e)}")
        # Fallback to default text
        return "Discover Quality Excellence"


# Initialize the framer
universal_framer = UniversalSocialFramer()