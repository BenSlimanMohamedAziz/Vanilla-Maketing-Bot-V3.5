# Imports

import os
import tempfile
import shutil
import time
import traceback
import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from auth.auth import get_current_user
from config.config import get_db_connection, get_db_cursor, release_db_connection
from .cloudinary_utils import upload_image_to_cloudinary


#---------------------------------------------------------------------------------------



# Initialize router
router = APIRouter(
    tags=["strategy_content_mgnmt"],
    responses={404: {"description": "Not found"}}
)

# Logger
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

# Get Company 
async def get_company_id_from_strategy(strategy_id: int, cursor) -> int:
    """Helper function to get company ID from strategy ID"""
    cursor.execute("SELECT company_id FROM strategies WHERE id = %s", (strategy_id,))
    result = cursor.fetchone()
    return result[0] if result else None

#---------------------------------------------------------------------------------------

# Return Media Content
@router.get("/get_content_items/{strategy_id}")
async def get_content_items(strategy_id: int, user: dict = Depends(get_current_user)):
    """Get all content items for a strategy - Async version"""
    try:
        logger.info(f"Getting content items for strategy {strategy_id}, user {user['user_id']}")
        
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify strategy belongs to user
        cursor.execute("""
            SELECT s.id 
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s
        """, (strategy_id, user["user_id"]))
        
        result = cursor.fetchone()
        logger.info(f"Strategy verification result: {result}")
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get all content items for this strategy
        cursor.execute("""
            SELECT id, platform, content_type, caption, hashtags, 
                   media_link, video_placeholder, best_time, status
            FROM content_items
            WHERE strategy_id = %s
            ORDER BY 
                CASE 
                    WHEN status = 'pending' THEN 1
                    WHEN status = 'approved' THEN 2
                    WHEN status = 'posted' THEN 3
                    ELSE 4
                END,
                best_time
        """, (strategy_id,))
        
        content_items = []
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} content items")
        
        for row in rows:
            content_items.append({
                "id": row[0],
                "platform": row[1],
                "content_type": row[2],
                "caption": row[3],
                "hashtags": row[4],
                "media_link": row[5],
                "video_placeholder": row[6],
                "best_time": row[7],
                "status": row[8]
            })
        
        return {"content_items": content_items}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content items: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'db_gen' in locals():
            await db_gen.aclose()

#---------------------------------------------------------------------------------------

# Create new content
@router.post("/create_content_item")
async def create_content_item(
    strategy_id: int = Form(...),
    platform: str = Form(...),
    content_type: str = Form(...),
    caption: str = Form(None),
    hashtags: str = Form(None),
    best_time: str = Form(None),
    status: str = Form('approved'),
    media: UploadFile = File(None),
    user: dict = Depends(get_current_user)
):
    """Create a new content item - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify strategy belongs to user
        cursor.execute("""
            SELECT s.id 
            FROM strategies s
            JOIN companies c ON s.company_id = c.id
            WHERE s.id = %s AND c.user_id = %s
        """, (strategy_id, user["user_id"]))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Handle file upload if exists
        media_link = None
        if media and media.filename:
            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # Read file content in chunks
                content = await media.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Upload to Cloudinary
            resource_type = "video" if "video" in content_type.lower() else "image"
            public_id = f"content_{strategy_id}_{int(time.time())}"
            
            media_link = await upload_image_to_cloudinary(
                temp_path,
                public_id=public_id,
                resource_type=resource_type
            )
            
            # Clean up temp file
            os.unlink(temp_path)
        
        # Get company ID
        company_id = await get_company_id_from_strategy(strategy_id, cursor)
        if not company_id:
            raise HTTPException(status_code=404, detail="Company not found for strategy")
        
        # Insert into database with the provided status
        cursor.execute("""
            INSERT INTO content_items (
                strategy_id, company_id, user_id, platform, content_type,
                caption, hashtags, media_link, best_time, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            strategy_id,
            company_id,
            user["user_id"],
            platform,
            content_type,
            caption,
            hashtags,
            media_link,
            best_time,
            status
        ))
        
        content_id = cursor.fetchone()[0]
        
        # Run commit in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.commit)
        
        return {"success": True, "content_id": content_id}
        
    except HTTPException:
        raise
    except Exception as e:
        # Rollback on error
        if 'conn' in locals():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, conn.rollback)
        logger.error(f"Error creating content item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()
        # Close media file if exists
        if media:
            await media.close()

#---------------------------------------------------------------------------------------

# Edit content
@router.put("/update_content_item/{content_id}")
async def update_content_item(
    content_id: int,
    platform: str = Form(...),
    content_type: str = Form(...),
    caption: str = Form(None),
    hashtags: str = Form(None),
    best_time: str = Form(None),
    status: str = Form(None),
    media: UploadFile = File(None),
    user: dict = Depends(get_current_user)
):
    """Update an existing content item - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify content belongs to user and get current status
        cursor.execute("""
            SELECT ci.id, ci.media_link, ci.status
            FROM content_items ci
            JOIN strategies s ON ci.strategy_id = s.id
            JOIN companies c ON s.company_id = c.id
            WHERE ci.id = %s AND c.user_id = %s
        """, (content_id, user["user_id"]))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Content item not found")
        
        current_media_link = result[1]
        current_status = result[2]
        media_link = current_media_link
        
        # Use the provided status or keep the current one
        final_status = status if status else current_status
        
        # Handle file upload if exists
        if media and media.filename:
            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                # Read file content in chunks
                content = await media.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Upload to Cloudinary
            resource_type = "video" if "video" in content_type.lower() else "image"
            public_id = f"content_{content_id}_{int(time.time())}"
            
            media_link = await upload_image_to_cloudinary(
                temp_path,
                public_id=public_id,
                resource_type=resource_type
            )
            
            # Clean up temp file
            os.unlink(temp_path)
        
        # Update in database
        cursor.execute("""
            UPDATE content_items
            SET platform = %s,
                content_type = %s,
                caption = %s,
                hashtags = %s,
                media_link = %s,
                best_time = %s,
                status = %s
            WHERE id = %s
        """, (
            platform,
            content_type,
            caption,
            hashtags,
            media_link,
            best_time,
            final_status,
            content_id
        ))
        
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
        logger.error(f"Error updating content item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure database connection is properly released
        if 'db_gen' in locals():
            await db_gen.aclose()
        # Close media file if exists
        if media:
            await media.close()

#---------------------------------------------------------------------------------------

# Return Content item
@router.get("/get_content_item/{content_id}")
async def get_content_item(content_id: int, user: dict = Depends(get_current_user)):
    """Get a specific content item - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify content belongs to user
        cursor.execute("""
            SELECT ci.id 
            FROM content_items ci
            JOIN strategies s ON ci.strategy_id = s.id
            JOIN companies c ON s.company_id = c.id
            WHERE ci.id = %s AND c.user_id = %s
        """, (content_id, user["user_id"]))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Content item not found")
        
        # Get the content item
        cursor.execute("""
            SELECT id, platform, content_type, caption, hashtags, 
                   media_link, video_placeholder, best_time, status
            FROM content_items
            WHERE id = %s
        """, (content_id,))
        
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Content item not found")
        
        return {
            "id": item[0],
            "platform": item[1],
            "content_type": item[2],
            "caption": item[3],
            "hashtags": item[4],
            "media_link": item[5],
            "video_placeholder": item[6],
            "best_time": item[7],
            "status": item[8]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'db_gen' in locals():
            await db_gen.aclose()

#---------------------------------------------------------------------------------------

# Delete Content
@router.delete("/delete_content_item/{content_id}")
async def delete_content_item(content_id: int, user: dict = Depends(get_current_user)):
    """Delete a content item - Async version"""
    try:
        # Get database connection
        db_gen = get_db()
        cursor, conn = await db_gen.__anext__()
        
        # Verify content belongs to user
        cursor.execute("""
            SELECT ci.id, ci.media_link
            FROM content_items ci
            JOIN strategies s ON ci.strategy_id = s.id
            JOIN companies c ON s.company_id = c.id
            WHERE ci.id = %s AND c.user_id = %s
        """, (content_id, user["user_id"]))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Content item not found")
        
        # Delete from database
        cursor.execute("DELETE FROM content_items WHERE id = %s", (content_id,))
        
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
        logger.error(f"Error deleting content item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'db_gen' in locals():
            await db_gen.aclose()