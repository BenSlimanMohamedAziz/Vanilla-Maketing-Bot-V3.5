# Imports

import io
import os
import cv2
import uuid
import numpy as np
import requests
import tempfile
import shutil
import asyncio
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from PIL import Image, ImageDraw
import concurrent.futures

# Set up logging
logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive video operations
video_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# ---------------------------------------------------------------------------- #

# Download the company logo
async def download_logo(logo_url: str) -> Optional[str]:
    """Download the logo from the provided URL - Async version"""
    try:
        logger.info("Downloading logo...")
        
        # Run the download in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(logo_url, stream=True, timeout=30)
        )
        response.raise_for_status()
        
        # Create temporary file
        temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        await loop.run_in_executor(
            None,
            lambda: temp_logo.write(response.content)
        )
        temp_logo.close()
        
        logger.info("✅ Logo downloaded successfully!")
        return temp_logo.name
        
    except Exception as e:
        logger.error(f"❌ Error downloading logo: {e}")
        return None


# Helper to add bg music to video
async def add_background_music(video_path: str, audio_path: str, output_path: str) -> bool:
    """Add background music to video using moviepy - Async version"""
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
        
        logger.info("Adding background music...")
        
        # Run in thread pool (moviepy is CPU intensive)
        loop = asyncio.get_event_loop()
        
        def process_audio():
            # Load video and audio
            video = VideoFileClip(video_path)
            
            # Check if audio file exists
            if not os.path.exists(audio_path):
                logger.warning(f"⚠️ Audio file {audio_path} not found, continuing without background music")
                shutil.copy2(video_path, output_path)
                video.close()
                return False
            
            audio = AudioFileClip(audio_path)
            
            # Loop audio if video is longer, or trim if audio is longer
            if audio.duration < video.duration:
                # Loop the audio to match video length
                loops_needed = int(video.duration / audio.duration) + 1
                audio_list = [audio] * loops_needed
                from moviepy.editor import concatenate_audioclips
                audio = concatenate_audioclips(audio_list)
                audio = audio.subclip(0, video.duration)
            else:
                # Trim audio to match video length
                audio = audio.subclip(0, video.duration)
            
            # Set audio volume to 30% to not overpower original video audio
            audio = audio.volumex(0.3)
            
            # Combine original audio with background music (if original video has audio)
            if video.audio is not None:
                final_audio = CompositeAudioClip([video.audio, audio])
            else:
                final_audio = audio
            
            # Set audio to video
            final_video = video.set_audio(final_audio)
            
            # Write final video
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='fast',
                verbose=False,
                logger=None
            )
            
            # Clean up
            video.close()
            audio.close()
            final_video.close()
            
            return True
        
        success = await loop.run_in_executor(video_executor, process_audio)
        
        if success:
            logger.info("✅ Background music added successfully!")
        else:
            logger.warning("⚠️ Background music processing completed without audio")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error adding background music: {e}")
        logger.info("Continuing without background music...")
        # If audio fails, just copy the video without audio processing
        shutil.copy2(video_path, output_path)
        return False


# Create Logo frame
def create_logo_frame(width: int, height: int, logo_path: str) -> np.ndarray:
    """Create a frame with logo using PIL and OpenCV"""
    # Create white background
    img = Image.new('RGB', (width, height), color='white')
    
    try:
        # Load logo with transparency support
        logo = Image.open(logo_path)
        
        # Convert to RGBA if not already
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')
        
        # Resize logo to fit (max 40% of width)
        max_width = int(width * 0.4)
        max_height = int(height * 0.4)
        
        logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Center the logo
        x = (width - logo.width) // 2
        y = (height - logo.height) // 2
        
        # Paste logo onto white background with transparency support
        img.paste(logo, (x, y), logo)
        
    except Exception as e:
        logger.warning(f"Could not process logo: {e}")
    
    # Convert to OpenCV format
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# Add Fade effect
def apply_fade_effect(frame: np.ndarray, fade_type: str, progress: float) -> np.ndarray:
    """Apply fade in/out effect to a frame"""
    if fade_type == "out":
        alpha = 1.0 - progress
    else:  # fade in
        alpha = progress
    
    # Create fade effect
    faded = frame * alpha
    return faded.astype(np.uint8)


# Create final video
async def create_enhanced_video(original_video_path: str, logo_path: str, output_path: str) -> bool:
    """Add fadeout and logo to the original video using OpenCV - Async version"""
    
    def process_video_sync():
        """Synchronous video processing (runs in thread pool)"""
        cap = None
        out = None
        
        try:
            logger.info("Starting video post-processing...")
            
            # Open original video
            cap = cv2.VideoCapture(original_video_path)
            
            if not cap.isOpened():
                logger.error("❌ Error: Could not open video file")
                return False
            
            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"Video properties: {width}x{height} at {fps} FPS, {total_frames} frames")
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error("❌ Error: Could not create output video")
                return False
            
            # Process original video frames with fadeout at the end
            frames_processed = 0
            fadeout_start_frame = max(0, total_frames - fps)  # Start fadeout 1 second before end
            
            logger.info("Processing original video frames...")
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frames_processed += 1
                
                # Apply fadeout to last second only
                if frames_processed >= fadeout_start_frame:
                    fade_progress = (frames_processed - fadeout_start_frame) / min(fps, total_frames - fadeout_start_frame)
                    frame = apply_fade_effect(frame, "out", fade_progress)
                
                out.write(frame)
            
            logger.info("✅ Original video processed with fadeout")
            
            # Release the original video capture
            cap.release()
            
            # Add logo scene (2 seconds) if logo exists - ONLY AFTER original video
            if logo_path and os.path.exists(logo_path):
                logger.info("Adding logo scene...")
                logo_frames = fps * 2  # 2 seconds of logo
                logo_frame = create_logo_frame(width, height, logo_path)
                
                for i in range(logo_frames):
                    frame = logo_frame.copy()
                    
                    # Apply fade in for first 0.5 seconds and fade out for last 0.5 seconds
                    if i < fps // 2:  # First 0.5 seconds fade in
                        progress = i / (fps // 2)
                        frame = apply_fade_effect(frame, "in", progress)
                    elif i > logo_frames - fps // 2:  # Last 0.5 seconds fade out
                        progress = (logo_frames - i) / (fps // 2)
                        frame = apply_fade_effect(frame, "out", progress)
                    else:
                        # Middle section - no fade effect
                        frame = logo_frame.copy()
                    
                    out.write(frame)
                
                logger.info("✅ Logo scene added")
            else:
                logger.info("⚠️ Logo not available, skipping logo scene")
            
            logger.info(f"🎉 Enhanced video saved as '{output_path}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during video post-processing: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Clean up
            if cap:
                cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
    
    # Run the synchronous video processing in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(video_executor, process_video_sync)


#---------------------------------------------------------------------------------------


# Clean downloaded videos
async def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files asynchronously"""
    loop = asyncio.get_event_loop()
    
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                await loop.run_in_executor(None, os.remove, file_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {file_path}: {e}")