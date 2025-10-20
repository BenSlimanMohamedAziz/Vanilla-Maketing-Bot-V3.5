# Imports
import asyncio
import time
import json
import requests
import logging
from typing import Optional
import concurrent.futures

# Set up logging
logger = logging.getLogger(__name__)

# Thread pool for API calls
publish_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

#---------------------------------------------------------------------------------------
# ------------------------- Instagram Publish Functions --------------------------- #
#---------------------------------------------------------------------------------------

# Publish Instagram img posts
async def publish_instagram_post(account_id: str, access_token: str, image_url: str, caption: str) -> bool:
    """Publish a regular post to Instagram - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        # 1. Create Container
        create_container_url = f'https://graph.facebook.com/v22.0/{account_id}/media'
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        }
        
        container_response = requests.post(create_container_url, data=payload)
        container_data = container_response.json()
        
        if 'id' not in container_data:
            return False
        
        container_id = container_data['id']
        
        # 2. Publish Container
        publish_url = f'https://graph.facebook.com/v22.0/{account_id}/media_publish'
        publish_payload = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        time.sleep(5)  # Wait before publishing
        
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_data = publish_response.json()
        
        return 'id' in publish_data
    
    return await loop.run_in_executor(publish_executor, sync_publish)

# Publish Instagram Stories
async def publish_instagram_story(account_id: str, access_token: str, image_url: str) -> bool:
    """Publish a story to Instagram - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        create_container_url = f'https://graph.facebook.com/v22.0/{account_id}/media'
        
        payload = {
            'image_url': image_url,
            'media_type': 'STORIES',
            'access_token': access_token
        }
        
        container_response = requests.post(create_container_url, data=payload)
        container_data = container_response.json()
        
        if 'id' not in container_data:
            return False
        
        container_id = container_data['id']
        
        publish_url = f'https://graph.facebook.com/v22.0/{account_id}/media_publish'
        publish_payload = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        time.sleep(5)
        
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_data = publish_response.json()
        
        return 'id' in publish_data
    
    return await loop.run_in_executor(publish_executor, sync_publish)

# Publish Instagram reels
async def publish_instagram_reel(account_id: str, access_token: str, video_url: str, caption: str, cover_url: Optional[str] = None) -> bool:
    """Publish a reel to Instagram - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        create_container_url = f'https://graph.facebook.com/v22.0/{account_id}/media'
        
        payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': access_token,
            'share_to_feed': True
        }
        
        if cover_url:
            payload['thumbnail_url'] = cover_url
        
        container_response = requests.post(create_container_url, data=payload)
        container_data = container_response.json()
        
        if 'id' not in container_data:
            return False
        
        container_id = container_data['id']
        
        # Check upload status
        status_url = f'https://graph.facebook.com/v22.0/{container_id}'
        status_payload = {
            'fields': 'status_code',
            'access_token': access_token
        }
        
        timeout = 60
        start_time = time.time()
        status_code = ''
        
        while status_code != 'FINISHED' and (time.time() - start_time) < timeout:
            time.sleep(5)
            status_response = requests.get(status_url, params=status_payload)
            status_data = status_response.json()
            
            if 'status_code' in status_data:
                status_code = status_data['status_code']
                if status_code == 'ERROR':
                    return False
                    
        if status_code != 'FINISHED':
            return False
        
        # Publish the reel
        publish_url = f'https://graph.facebook.com/v22.0/{account_id}/media_publish'
        publish_payload = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_data = publish_response.json()
        
        return 'id' in publish_data
    
    return await loop.run_in_executor(publish_executor, sync_publish)



#---------------------------------------------------------------------------------------
# ------------------------- Facebook Publish Functions --------------------------- #
#---------------------------------------------------------------------------------------

# Publish Facebook text posts
async def publish_facebook_text_post(page_id: str, access_token: str, message: str) -> bool:
    """Publish a text-only post to a Facebook page - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        logger.info(f"[FB] Starting text post publication to page {page_id}")
        
        try:
            url = f'https://graph.facebook.com/v22.0/{page_id}/feed'
            
            payload = {
                'message': message,
                'access_token': access_token
            }
            
            logger.info("[FB] Sending text post request...")
            response = requests.post(url, data=payload)
            response.raise_for_status()
            data = response.json()
            
            if 'id' in data:
                post_id = data['id']
                logger.info(f"[FB] Text post published successfully! Post ID: {post_id}")
                return True
            else:
                logger.error(f"[FB] Failed to publish text post. Response: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[FB] Text post request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[FB] Unexpected error in text post: {str(e)}")
            return False
    
    return await loop.run_in_executor(publish_executor, sync_publish)


# Publish Facebook Img posts
async def publish_facebook_image_post(page_id: str, access_token: str, image_url: str, message: Optional[str] = None) -> bool:
    """Publish an image post to a Facebook page - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        logger.info(f"[FB] Starting image post publication to page {page_id}")
        logger.info(f"[FB] Image URL: {image_url}")
        
        try:
            url = f'https://graph.facebook.com/v22.0/{page_id}/photos'
            
            payload = {
                'url': image_url,
                'access_token': access_token
            }
            
            if message:
                logger.info("[FB] Adding caption to image post")
                payload['caption'] = message
            
            logger.info("[FB] Sending image post request...")
            response = requests.post(url, data=payload)
            response.raise_for_status()
            data = response.json()
            
            if 'id' in data or 'post_id' in data:
                post_id = data.get('id') or data.get('post_id')
                logger.info(f"[FB] Image post published successfully! Post ID: {post_id}")
                return True
            else:
                logger.error(f"[FB] Failed to publish image post. Response: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[FB] Image post request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[FB] Unexpected error in image post: {str(e)}")
            return False
    
    return await loop.run_in_executor(publish_executor, sync_publish)


# Publish Facebook Vid posts
async def publish_facebook_video_post(page_id: str, access_token: str, video_url: str, title: Optional[str] = None, description: Optional[str] = None) -> bool:
    """Publish a video post to a Facebook page - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        logger.info(f"[FB] Starting video post publication to page {page_id}")
        logger.info(f"[FB] Video URL: {video_url}")
        
        try:
            url = f'https://graph.facebook.com/v22.0/{page_id}/videos'
            
            payload = {
                'file_url': video_url,
                'access_token': access_token
            }
            
            if title:
                logger.info("[FB] Adding title to video post")
                payload['title'] = title
            
            if description:
                logger.info("[FB] Adding description to video post")
                payload['description'] = description
            
            logger.info("[FB] Sending video post request...")
            response = requests.post(url, data=payload)
            response.raise_for_status()
            data = response.json()
            
            if 'id' in data:
                video_id = data['id']
                logger.info(f"[FB] Video post published successfully! Video ID: {video_id}")
                return True
            else:
                logger.error(f"[FB] Failed to publish video post. Response: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[FB] Video post request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[FB] Unexpected error in video post: {str(e)}")
            return False
    
    return await loop.run_in_executor(publish_executor, sync_publish)



#---------------------------------------------------------------------------------------
# ------------------------- LinkedIn Publish Functions --------------------------- #
#---------------------------------------------------------------------------------------

# Publish Linkedin text posts
async def publish_linkedin_text_post(access_token: str, user_id: str, text: str) -> bool:
    """Publish a text-only post to LinkedIn - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        try:
            # Validate inputs
            if not user_id.startswith("urn:li:person:"):
                raise ValueError("Invalid user_id format. Must start with 'urn:li:person:'")
            if not text.strip():
                raise ValueError("Text content cannot be empty")
            
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            payload = {
                "author": user_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0',
                'LinkedIn-Version': '202402'
            }
            
            logger.info("[LINKEDIN] Creating text post...")
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code != 201:
                raise Exception(f"API returned {response.status_code}: {response.text}")
            
            post_id = response.headers.get('X-RestLi-Id')
            logger.info(f"[LINKEDIN] Text post published successfully! Post ID: {post_id}")
            return True
                
        except requests.exceptions.RequestException as e:
            error_detail = f"Request failed: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_detail += f"\nResponse: {e.response.text}"
            raise Exception(f"LinkedIn text post failed: {error_detail}")
        except Exception as e:
            raise Exception(f"Unexpected error in text post: {str(e)}")
    
    return await loop.run_in_executor(publish_executor, sync_publish)

# Publish Linkedin Img posts
async def publish_linkedin_image_post(access_token: str, user_id: str, image_url: str, text: str) -> bool:
    """Publish an image post to LinkedIn - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        try:
            # Validate inputs
            if not user_id.startswith("urn:li:person:"):
                raise ValueError("Invalid user_id format. Must start with 'urn:li:person:'")
            if not image_url.startswith(('http://', 'https://')):
                raise ValueError("Invalid image URL format")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0',
                'LinkedIn-Version': '202402'
            }
            
            # 1. Register upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": user_id,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }]
                }
            }
            
            logger.info("[LINKEDIN] Registering image upload...")
            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                data=json.dumps(register_payload),
                timeout=10
            )
            register_response.raise_for_status()
            register_data = register_response.json()
            
            upload_url = register_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = register_data['value']['asset']
            
            # 2. Upload image with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with requests.Session() as session:
                        # Download image first
                        image_response = session.get(image_url, stream=True, timeout=30)
                        image_response.raise_for_status()
                        
                        # Upload to LinkedIn
                        upload_response = session.put(
                            upload_url,
                            headers={'Authorization': f'Bearer {access_token}'},
                            data=image_response.iter_content(chunk_size=8192),
                            timeout=30
                        )
                        upload_response.raise_for_status()
                    break  # Success - exit retry loop
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # 3. Create post
            post_payload = {
                "author": user_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "IMAGE",
                        "media": [{
                            "status": "READY",
                            "description": {"text": text[:200]},
                            "media": asset_urn,
                            "title": {"text": "Shared Image"}
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            logger.info("[LINKEDIN] Creating image post...")
            post_response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                data=json.dumps(post_payload),
                timeout=10
            )
            post_response.raise_for_status()
            
            return True
            
        except requests.exceptions.RequestException as e:
            error_detail = f"Request failed: {str(e)}"
            if e.response:
                error_detail += f"\nStatus: {e.response.status_code}\nResponse: {e.response.text[:500]}"
            raise Exception(f"LinkedIn image post failed: {error_detail}")
        except Exception as e:
            raise Exception(f"Unexpected error in image post: {str(e)}")
    
    return await loop.run_in_executor(publish_executor, sync_publish)

# Publish Linkedin Vid posts
async def publish_linkedin_video_post(access_token: str, user_id: str, video_url: str, text: str) -> bool:
    """Publish a video post to LinkedIn - Async version"""
    loop = asyncio.get_event_loop()
    
    def sync_publish():
        try:
            # Validate inputs
            if not user_id.startswith("urn:li:person:"):
                raise ValueError("Invalid user_id format")
            if not video_url.startswith(('http://', 'https://')):
                raise ValueError("Invalid video URL")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0',
                'LinkedIn-Version': '202402'
            }
            
            # 1. Register upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                    "owner": user_id,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }]
                }
            }
            
            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                data=json.dumps(register_payload),
                timeout=10
            )
            register_response.raise_for_status()
            register_data = register_response.json()
            
            upload_url = register_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = register_data['value']['asset']
            
            # 2. Upload video with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with requests.Session() as session:
                        # Stream video upload in chunks
                        with session.get(video_url, stream=True, timeout=30) as video_response:
                            video_response.raise_for_status()
                            
                            upload_response = session.put(
                                upload_url,
                                headers={'Authorization': f'Bearer {access_token}'},
                                data=video_response.iter_content(chunk_size=8192),
                                timeout=30
                            )
                            upload_response.raise_for_status()
                    
                    break  # Success - exit retry loop
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # 3. Create post
            post_payload = {
                "author": user_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "VIDEO",
                        "media": [{
                            "status": "READY",
                            "description": {"text": text[:200]},
                            "media": asset_urn,
                            "title": {"text": "Shared Video"}
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            post_response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                data=json.dumps(post_payload),
                timeout=10
            )
            post_response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"[LINKEDIN] Video post error: {str(e)}")
            raise Exception(f"LinkedIn video post failed: {str(e)}")
    
    return await loop.run_in_executor(publish_executor, sync_publish)