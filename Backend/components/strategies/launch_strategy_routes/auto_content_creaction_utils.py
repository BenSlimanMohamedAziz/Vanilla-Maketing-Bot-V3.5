# Imports

import os
import asyncio
import logging
import tempfile
import shutil
import time
from typing import List, Optional
import replicate
from dotenv import load_dotenv
import requests
import io
import uuid
from datetime import datetime
from PIL import Image
from fastapi import File, Form, HTTPException, Depends, UploadFile
from fastapi.responses import JSONResponse
from fastapi import APIRouter

 # Import config and db
from config.config import get_db_connection, get_db_cursor, release_db_connection, settings

# Import user
from auth.auth import get_current_user

# Import together for img gen api
from together import Together


# Import helpers for strategy content creation
from components.strategies.launch_strategy_routes.image_content_creation_helpers import (
    universal_framer, 
    generate_overlay_text
)

# Import utils for strategy content cloud uploads
from components.strategies.launch_strategy_routes.cloudinary_utils import (
    upload_image_to_cloudinary, 
    upload_video_to_cloudinary
)

# Import video helpers
from .video_content_creation_helpers import (
    download_logo, 
    create_enhanced_video, 
    add_background_music,
    cleanup_temp_files
)


#---------------------------------------------------------------------------------------


# Set up logging
logger = logging.getLogger(__name__)

# Router prep
router = APIRouter(
    tags=["strategy_launch_auto_content_creation"],
    responses={404: {"description": "Not found"}}
)

# Together client for image generation
# API keys and endpoints LLAMA
LLAMA_API_KEY = settings.LLAMA_API_KEY
LLAMA_API_URL = settings.LLAMA_API_URL
together_client = Together(api_key=LLAMA_API_KEY)

# Database dependency
async def get_db():
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    try:
        yield cursor, conn
    finally:
        release_db_connection(conn)

#---------------------------------------------------------------------------------------                


# Function to generate posts based on paltfrom and content type :
@router.post("/generate_for_post_type/{content_id}")
async def generate_for_post_type(content_id: int, user: dict = Depends(get_current_user), db=Depends(get_db)):
    print(f"\n[INFO] Starting content generation for content_id: {content_id}")
    
    cursor, conn = db
    
    try:
        # Get content item details including platform
        print("[INFO] Fetching content details from database...")
        cursor.execute("""
            SELECT ci.platform, ci.content_type, ci.image_prompt, ci.video_placeholder, 
                   ci.caption, ci.hashtags, c.id as company_id, c.name as company_name, c.logo_url
            FROM content_items ci
            JOIN companies c ON ci.company_id = c.id
            WHERE ci.id = %s AND ci.user_id = %s
        """, (content_id, user["user_id"]))
        
        content_data = cursor.fetchone()
        if not content_data:
            print(f"[ERROR] Content not found for content_id: {content_id}")
            raise HTTPException(status_code=404, detail="Content not found")
        
        platform, content_type, image_prompt, video_placeholder, caption, hashtags, company_id, company_name, logo_url = content_data
        print(f"[INFO] Platform: {platform}, Content type: {content_type}, Company: {company_name}")
        
        media_url = None
        
        # Define platform-specific aspect ratio prompts
        aspect_ratio_prompts = {
            "Instagram": {
                "feed": "Square aspect ratio (1:1)",
                "Feed Image Posts": "Square aspect ratio (1:1)",
                "Instagram Stories": "Vertical aspect ratio (9:16)",
                "Story": "Vertical aspect ratio (9:16)",
                "Stories": "Vertical aspect ratio (9:16)",
                "Instagram Story": "Vertical aspect ratio (9:16)",
                "Instagram Reels": "Vertical aspect ratio (9:16)",
                "Reel": "Vertical aspect ratio (9:16)"
            },
            "Facebook": {
                "Image Posts": "4:5 aspect ratio",
                "Video Posts": "4:5 aspect ratio",
                "Facebook Image Posts": "4:5 aspect ratio",
            },
            "LinkedIn": {
                "LinkedIn Image Posts": "Portrait aspect ratio (4:5)",
                "Video Posts": "Portrait aspect ratio (4:5)",
                "LinkedIn Video Posts": "Portrait aspect ratio (4:5)",
            }
        }
        
        # Get the appropriate aspect ratio prompt
        aspect_prompt = aspect_ratio_prompts.get(platform, {}).get(content_type, "")
        
        if platform.lower() in ['instagram', 'facebook', 'linkedin'] and content_type in ['feed', 'Stories', 'Story', 'Image', 'Feed Image Posts', 'Instagram Stories', 'Image Posts', 'LinkedIn Image Posts','Facebook Image Posts']:
            print(f"[INFO] Generating {platform} {content_type} image...")
            
            # Generate dynamic overlay text
            dynamic_overlay_text = await generate_overlay_text(company_id, cursor)
            
            # Add platform-specific aspect ratio to the prompt
            enhanced_prompt = f"{image_prompt} - IMPORTANT: {aspect_prompt}"
            
            # Use FLUX model - run in thread pool since it's blocking
            flux_model = "black-forest-labs/FLUX.1-schnell-Free"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: together_client.images.generate(
                    prompt=enhanced_prompt,
                    model=flux_model,
                    steps=4,
                    n=1,
                )
            )
            
            if not response.data:
                print("[ERROR] No image data received from API")
                return JSONResponse({"error": "No image data in response"}, status_code=500)
                
            first_image = response.data[0]
            
            if not hasattr(first_image, 'url') or not first_image.url:
                print("[ERROR] No image URL in response")
                return JSONResponse({"error": "No image URL in response"}, status_code=500)
            
            # Download the generated image and logo concurrently
            img_response, logo_response = await asyncio.gather(
                loop.run_in_executor(None, lambda: requests.get(first_image.url)),
                loop.run_in_executor(None, lambda: requests.get(logo_url)),
                return_exceptions=True
            )
            
            # Check for exceptions in downloads
            if isinstance(img_response, Exception):
                raise img_response
            if isinstance(logo_response, Exception):
                raise logo_response
                
            img_response.raise_for_status()
            logo_response.raise_for_status()
            
            # Load images in thread pool
            generated_img, logo_img = await asyncio.gather(
                loop.run_in_executor(None, lambda: Image.open(io.BytesIO(img_response.content)).convert("RGBA")),
                loop.run_in_executor(None, lambda: Image.open(io.BytesIO(logo_response.content)).convert("RGBA"))
            )
            
            # Apply the universal frame
            framed_image = await universal_framer.create_post_from_images(
                generated_img, 
                logo_img, 
                platform,
                content_type,
                company_id,
                overlay_text=dynamic_overlay_text
            )
            
            # Save the framed image to a temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{platform.lower()}_{content_type.lower().replace(' ', '_')}_{company_id}_{timestamp}_{unique_id}.png"
            filepath = f"../static/imgs/generated_campagin_img/{filename}"
            
            await loop.run_in_executor(None, lambda: framed_image.save(filepath, "PNG"))
            
            # Upload to Cloudinary
            cloudinary_url = await upload_image_to_cloudinary(
                filepath,
                public_id=f"{platform.lower()}_{content_type.lower().replace(' ', '_')}_{company_id}_{timestamp}_{unique_id}"
            )
            
            # Save the Cloudinary URL to database
            cursor.execute("""
                UPDATE content_items 
                SET media_link = %s
                WHERE id = %s
            """, (cloudinary_url, content_id))
            await loop.run_in_executor(None, conn.commit)
            
            # Clean up local file
            await loop.run_in_executor(None, os.remove, filepath)
            
            return JSONResponse({
                "image_url": cloudinary_url,
                "content_type": content_type.lower().replace(' ', '_'),
                "platform": platform.lower(),
                "dimensions": f"{universal_framer.get_platform_dimensions(platform, content_type)[0]}x{universal_framer.get_platform_dimensions(platform, content_type)[1]}"
            })
                
        elif content_type in ['Text Posts', 'Text Posts (Status Updates / Announcements)', 'Articles', 'Article', 'Text','Status']:
            print(f"[INFO] Generating {platform} Text Post...")
            # For text posts, we just return the caption and hashtags
            full_text = f"{caption}\n\n{hashtags}" if hashtags else caption
            
            return JSONResponse({
                "text_content": full_text,
                "content_type": "text",
                "platform": platform.lower()
            })
            
        elif content_type in ['Instagram Reels', 'Facebook Videos', 'Linkedin Videos','LinkedIn Videos','Reels (Video)', 'Reel', 'Reels', 'Video Post', 'Video Posts', 'Videos']:
            print(f"[INFO] Processing {platform} Video...")
            
            # Generate video using the video placeholder as prompt
            video_path = await generate_video_with_logo(video_placeholder, logo_url)
            
            if not video_path:
                return JSONResponse({"error": "Failed to generate video"}, status_code=500)
            
            # Process video upload asynchronously
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{platform.lower()}_{content_type.lower().replace(' ', '_')}_{company_id}_{timestamp}_{unique_id}.mp4"
            local_video_path = f"../static/vids/{filename}"
            
            # Copy video in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, shutil.copy2, video_path, local_video_path)
            print(f"✅ Video saved locally: {local_video_path}")
            
            # Upload to Cloudinary
            public_id = f"{platform.lower()}_{content_type.lower().replace(' ', '_')}_{company_id}_{timestamp}_{unique_id}"
            cloudinary_url = await upload_video_to_cloudinary(local_video_path, public_id)
            
            # Clean up files
            cleanup_tasks = [
                loop.run_in_executor(None, os.remove, local_video_path),
                loop.run_in_executor(None, os.remove, video_path)
            ]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Save to database
            cursor.execute("""
                UPDATE content_items 
                SET media_link = %s
                WHERE id = %s
            """, (cloudinary_url, content_id))
            await loop.run_in_executor(None, conn.commit)
            
            return JSONResponse({
                "video_url": cloudinary_url,
                "content_type": "video",
                "platform": platform.lower(),
                "message": "Video generated successfully"
            })
            
        else:
            print(f"[ERROR] Unsupported platform: {platform}")
            return JSONResponse({"error": f"Unsupported platform: {platform}"}, status_code=400)
            
    except Exception as e:
        print(f"[ERROR] Content generation failed: {str(e)}")
        logger.error(f"Content generation error: {str(e)}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)



#---------------------------------------------------------------------------------------



# Load environment variables
load_dotenv()

# List of available API tokens for video gen
API_TOKENS = [
    os.getenv('REPLICATE_API_TOKEN_1'),
    os.getenv('REPLICATE_API_TOKEN_2'), 
    os.getenv('REPLICATE_API_TOKEN_3'),
    os.getenv('REPLICATE_API_TOKEN_4'),
    os.getenv('REPLICATE_API_TOKEN_5'),
    os.getenv('REPLICATE_API_TOKEN_6')
]

# Filter out any None values (if some tokens aren't set)
API_TOKENS = [token for token in API_TOKENS if token]


# Generate Video
async def generate_video_with_logo(prompt: str, logo_url: str) -> Optional[str]:
    """Generate a video with the given prompt and add logo branding - Async version"""
    
    # Try each API token until one works
    for idx, api_token in enumerate(API_TOKENS, 1):
        try:
            logger.info(f"Trying API token #{idx}: {api_token[:10]}...")
            
            # Create a NEW replicate client with the current token
            client = replicate.Client(api_token=api_token)
            
            logger.info(f"Generating video with prompt: {prompt}")
            
            # Generate video using the specific client (run in thread pool as it's blocking)
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(
                None,
                lambda: client.run(
                    "minimax/video-01",
                    input={"prompt": prompt}
                )
            )
            
            # Get the video URL
            video_url = str(output)
            logger.info(f"✅ Video generated successfully with token #{idx}: {video_url}")
            
            # Download the original video
            logger.info("Downloading original video...")
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(video_url, stream=True, timeout=60)
            )
            response.raise_for_status()
            
            # Create temporary files
            original_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            await loop.run_in_executor(
                None,
                lambda: open(original_video_path, "wb").write(response.content)
            )
            
            logger.info("✅ Original video downloaded!")
            
            # Download logo
            logo_path = await download_logo(logo_url)
            
            # Create enhanced video with post-processing
            enhanced_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            success = await create_enhanced_video(
                original_video_path, 
                logo_path, 
                enhanced_video_path
            )
            
            if not success:
                logger.error("❌ Failed to create enhanced video")
                # Clean up and try next token
                await cleanup_temp_files([original_video_path, enhanced_video_path, logo_path])
                continue
            
            # Add background music if available
            final_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            bg_music_path = "./sounds/bg_music.mp3"  # Audio file in the same directory as main.py
            
            # Check if background music file exists
            if os.path.exists(bg_music_path):
                logger.info("Adding background music...")
                await add_background_music(enhanced_video_path, bg_music_path, final_video_path)
            else:
                logger.info("⚠️ Background music file not found, proceeding without music")
                shutil.copy2(enhanced_video_path, final_video_path)
            
            # Clean up temporary files
            await cleanup_temp_files([original_video_path, enhanced_video_path, logo_path])
            
            if success:
                logger.info(f"🎉 Final video ready: {final_video_path}")
                return final_video_path
            else:
                await cleanup_temp_files([final_video_path])
                continue  # Try next token
                
        except replicate.exceptions.ReplicateError as e:
            # Specific handling for Replicate API errors (like rate limits)
            logger.error(f"❌ Replicate API error with token #{idx}: {e}")
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                logger.info(f"Token #{idx} is rate limited, trying next token...")
            else:
                logger.info("Trying next API token...")
            await asyncio.sleep(1)
            continue
            
        except Exception as e:
            logger.error(f"❌ Error with API token #{idx}: {e}")
            logger.info("Trying next API token...")
            await asyncio.sleep(1)
            continue
    
    # If all tokens failed
    logger.error("❌ All API tokens failed!")
    return None


#---------------------------------------------------------------------------------------


# User Uploads his own custom made content instead
@router.post("/upload_custom_media")
async def upload_custom_media(
    file: UploadFile = File(...),
    content_id: int = Form(...),
    is_video: bool = Form(False),
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    cursor, conn = db
    try:
        # Verify the content belongs to the user
        cursor.execute("""
            SELECT id FROM content_items 
            WHERE id = %s AND user_id = %s
        """, (content_id, user["user_id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Content not found")

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        # Upload to Cloudinary
        resource_type = "video" if is_video else "image"
        public_id = f"custom_{resource_type}_{content_id}_{int(time.time())}"
        
        cloudinary_url = await upload_image_to_cloudinary(
            temp_path,
            public_id=public_id,
            resource_type=resource_type
        )

        # Update the content item in database
        if is_video:
            # For videos, update both media_link and video_placeholder
            cursor.execute("""
                UPDATE content_items 
                SET media_link = %s, video_placeholder = %s
                WHERE id = %s
            """, (cloudinary_url, cloudinary_url, content_id))
        else:
            # For images, just update media_link
            cursor.execute("""
                UPDATE content_items 
                SET media_link = %s
                WHERE id = %s
            """, (cloudinary_url, content_id))
        
        conn.commit()

        # Clean up temp file
        os.unlink(temp_path)

        return {"media_url": cloudinary_url}

    except Exception as e:
        logger.error(f"Custom media upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()