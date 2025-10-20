# Imports
from fastapi import logger
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# For Posting / Uploading Cloud : 
import cloudinary
import cloudinary.uploader


# Settings config import
from config.config import settings

#---------------------------------------------------------------------------------------



# Cloud Upload Config
cloudinary.config( 
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key = settings.CLOUDINARY_API_KEY,
    api_secret = settings.CLOUDINARY_API_SECRET,
    secure=True,
    # Add this to enable video uploads
    video_upload_options={
        'resource_type': 'video',
        'chunk_size': 6000000,
        'eager': [
            {'width': 300, 'height': 300, 'crop': 'pad', 'audio_codec': 'none'},
            {'width': 160, 'height': 100, 'crop': 'crop', 'gravity': 'south', 'audio_codec': 'none'}
        ]
    }
)

# Set up logger
logger = logging.getLogger(__name__)

# Cloud Upload Config
cloudinary.config( 
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
    # Add this to enable video uploads
    video_upload_options={
        'resource_type': 'video',
        'chunk_size': 6000000,
        'eager': [
            {'width': 300, 'height': 300, 'crop': 'pad', 'audio_codec': 'none'},
            {'width': 160, 'height': 100, 'crop': 'crop', 'gravity': 'south', 'audio_codec': 'none'}
        ]
    }
)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

#---------------------------------------------------------------------------------------

# Uploading Img content to cloud
async def upload_image_to_cloudinary(image_data, public_id=None, resource_type="image"):
    """
    Async wrapper for Cloudinary image upload
    """
    try:
        # Run the blocking Cloudinary upload in a thread pool
        loop = asyncio.get_event_loop()
        upload_result = await loop.run_in_executor(
            executor,
            lambda: cloudinary.uploader.upload(
                image_data,
                public_id=public_id,
                overwrite=True,
                resource_type=resource_type
            )
        )
        return upload_result["secure_url"]
    except Exception as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        raise e

#---------------------------------------------------------------------------------------    
    
    
# Uploading Video content to cloud
async def upload_video_to_cloudinary(file_path, public_id=None):
    """
    Async wrapper for Cloudinary video upload
    """
    try:
        print(f"Uploading video to Cloudinary: {file_path}")      
        
        # Run the blocking Cloudinary upload in a thread pool
        loop = asyncio.get_event_loop()
        upload_result = await loop.run_in_executor(
            executor,
            lambda: cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                resource_type="video",
                overwrite=True,
                timeout=120,
                format="mp4"
            )
        )
        
        print(f"✅ Video uploaded successfully: {upload_result['secure_url']}")
        return upload_result['secure_url']
        
    except Exception as e:
        print(f"ERROR: Cloudinary video upload error: {str(e)}")
        raise e

#---------------------------------------------------------------------------------------