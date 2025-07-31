"""
Notion Service - All Notion API operations
Handles database creation, page creation/updates, file uploads, and property management
"""

import os
import logging
import requests
import json
import time
import hashlib
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from notion_client import Client, AsyncClient
from notion_client.errors import APIResponseError, RequestTimeoutError
from config.config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_PARENT_PAGE_ID, save_database_id
from mutagen import File

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN not found in environment variables")
            
        self.client = Client(auth=NOTION_TOKEN)
        self.async_client = AsyncClient(auth=NOTION_TOKEN)
        self.database_id = NOTION_DATABASE_ID
        
        # Performance tracking
        self.api_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Intelligent caching system
        self.cache = {}
        self.cache_ttl = {}
        self.default_cache_duration = 300  # 5 minutes
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # If no database ID, create one using the parent page
        if not self.database_id and NOTION_PARENT_PAGE_ID:
            logger.info("No database ID provided, creating new Voice Memos database...")
            self.database_id = self.create_database_if_needed(NOTION_PARENT_PAGE_ID)
            if not self.database_id:
                raise ValueError("Failed to create Notion database")
            else:
                # Save the database ID for future use
                if save_database_id(self.database_id):
                    logger.info(f"Saved database ID {self.database_id} to config file")
                else:
                    logger.warning("Failed to save database ID to config file")
        elif not self.database_id:
            raise ValueError("NOTION_DATABASE_ID or NOTION_PARENT_PAGE_ID must be provided")

    # PERFORMANCE AND CACHING FUNCTIONS
    
    def _rate_limit(self):
        """Intelligent rate limiting to avoid API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation"""
        key_data = f"{operation}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if not expired"""
        if cache_key in self.cache:
            if time.time() < self.cache_ttl.get(cache_key, 0):
                self.cache_hits += 1
                return self.cache[cache_key]
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
                if cache_key in self.cache_ttl:
                    del self.cache_ttl[cache_key]
        
        self.cache_misses += 1
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl_seconds: Optional[int] = None):
        """Set data in cache with TTL"""
        if ttl_seconds is None:
            ttl_seconds = self.default_cache_duration
        
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = time.time() + ttl_seconds
    
    def _make_api_call(self, operation: str, use_cache: bool = True, cache_ttl: Optional[int] = None, **kwargs) -> Any:
        """Make API call with caching and rate limiting"""
        cache_key = self._cache_key(operation, **kwargs) if use_cache else None
        
        # Check cache first
        if cache_key:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result
        
        # Rate limit
        self._rate_limit()
        
        # Make the API call
        try:
            if operation == "get_database":
                result = self.client.databases.retrieve(**kwargs)
            elif operation == "update_page":
                result = self.client.pages.update(**kwargs)
            elif operation == "create_page":
                result = self.client.pages.create(**kwargs)
            elif operation == "get_page":
                result = self.client.pages.retrieve(**kwargs)
            elif operation == "query_database":
                result = self.client.databases.query(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            self.api_calls += 1
            
            # Cache the result
            if cache_key and use_cache:
                self._set_cache(cache_key, result, cache_ttl)
            
            return result
            
        except (APIResponseError, RequestTimeoutError) as e:
            logger.error(f"API call failed for {operation}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API call {operation}: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / cache_total * 100) if cache_total > 0 else 0
        
        return {
            'api_calls_made': self.api_calls,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'cached_items': len(self.cache),
            'estimated_cost_savings': self.cache_hits * 0.01  # Rough estimate
        }

    # DATABASE FUNCTIONS
    
    def check_database_exists(self) -> bool:
        """Check if the specified database exists and is accessible"""
        try:
            self._make_api_call(
                "get_database",
                database_id=self.database_id,
                use_cache=True,
                cache_ttl=3600  # Cache database info for 1 hour
            )
            logger.info("Successfully connected to Notion database")
            return True
        except APIResponseError as e:
            logger.error(f"Cannot access Notion database: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking Notion database: {e}")
            return False

    def create_database_if_needed(self, parent_page_id: str) -> Optional[str]:
        """Create a new database for voice memos if needed"""
        try:
            database_properties = {
                "Title": {
                    "title": {}
                },
                "Primary Themes": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Specific Focus": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Content Types": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Emotional Tones": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Key Topics": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Tags": {
                    "multi_select": {
                        "options": []
                    }
                },
                "Summary": {
                    "rich_text": {}
                },
                "Duration": {
                    "rich_text": {}
                },
                "Duration (Seconds)": {
                    "number": {}
                },
                "File Created": {
                    "date": {}
                },
                "File Size": {
                    "rich_text": {}
                },
                "Audio File": {
                    "files": {}
                },
                "Flagged for Deletion": {
                    "checkbox": {}
                },
                "Deletion Confidence": {
                    "select": {
                        "options": [
                            {"name": "High", "color": "red"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Low", "color": "green"}
                        ]
                    }
                },
                "Deletion Reason": {
                    "rich_text": {}
                }
            }
            
            response = self.client.databases.create(
                parent={
                    "type": "page_id",
                    "page_id": parent_page_id
                },
                title=[
                    {
                        "type": "text",
                        "text": {
                            "content": "Voice Memos"
                        }
                    }
                ],
                properties=database_properties
            )
            
            database_id = response["id"]
            logger.info(f"Created new Notion database: {database_id}")
            return database_id
            
        except APIResponseError as e:
            logger.error(f"Error creating Notion database: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Notion database: {e}")
            return None

    def query_all_pages(self) -> List[Dict[str, Any]]:
        """Query all pages from the database"""
        try:
            all_pages = []
            has_more = True
            start_cursor = None
            
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self._make_api_call("query_database", **query_params, use_cache=False)
                
                all_pages.extend(response["results"])
                has_more = response["has_more"]
                start_cursor = response.get("next_cursor")
            
            logger.info(f"Retrieved {len(all_pages)} pages from database")
            return all_pages
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []

    # PAGE FUNCTIONS
    
    def create_page(self, 
                   title: str,
                   transcript: str,
                   claude_tags: Dict[str, str],
                   summary: str,
                   filename: str,
                   audio_file_path: str,
                   audio_duration: Optional[float] = None,
                   deletion_analysis: Optional[Dict] = None,
                   original_transcript: Optional[str] = None,
                   content_type: Optional[str] = None) -> Optional[str]:
        """Create a new page in the Notion database with the voice memo data"""
        try:
            # Extract audio metadata
            metadata = self.extract_audio_metadata(audio_file_path)
            
            # Helper function to parse comma-separated tags into multi-select format
            def parse_tags_to_multiselect(tag_string: str) -> List[Dict[str, str]]:
                if not tag_string:
                    return []
                # Parse tags, clean brackets if present, and format for Notion
                tags = tag_string.replace('[', '').replace(']', '').split(',')
                return [{"name": tag.strip()} for tag in tags if tag.strip()]
            
            # Process each tag category
            primary_themes_tags = parse_tags_to_multiselect(claude_tags.get('primary_themes', ''))
            specific_focus_tags = parse_tags_to_multiselect(claude_tags.get('specific_focus', ''))
            content_types_tags = parse_tags_to_multiselect(claude_tags.get('content_types', ''))
            emotional_tones_tags = parse_tags_to_multiselect(claude_tags.get('emotional_tones', ''))
            key_topics_tags = parse_tags_to_multiselect(claude_tags.get('key_topics', ''))
            
            # Combine all tags for the main Tags field (for backward compatibility)
            all_tags = []
            for tag_list in [primary_themes_tags, specific_focus_tags, content_types_tags, emotional_tones_tags, key_topics_tags[:6]]:
                all_tags.extend(tag_list)
            unique_tags = list({tag['name']: tag for tag in all_tags}.values())[:15]  # Remove duplicates, limit to 15
            
            # Prepare properties for the Notion page
            properties = {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Primary Themes": {
                    "multi_select": primary_themes_tags
                } if primary_themes_tags else None,
                "Specific Focus": {
                    "multi_select": specific_focus_tags
                } if specific_focus_tags else None,
                "Content Types": {
                    "multi_select": content_types_tags
                } if content_types_tags else None,
                "Emotional Tones": {
                    "multi_select": emotional_tones_tags
                } if emotional_tones_tags else None,
                "Key Topics": {
                    "multi_select": key_topics_tags
                } if key_topics_tags else None,
                "Tags": {
                    "multi_select": unique_tags[:10]  # Already formatted as list of dicts
                },
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": summary
                            }
                        }
                    ]
                },
                "Duration": {
                    "rich_text": [
                        {
                            "text": {
                                "content": self.format_duration(metadata['duration_seconds'])
                            }
                        }
                    ]
                },
                "Duration (Seconds)": {
                    "number": metadata['duration_seconds']
                },
                "File Created": {
                    "date": {
                        "start": metadata['file_created'].isoformat() if metadata['file_created'] else None
                    } if metadata['file_created'] else None
                },
                "File Size": {
                    "rich_text": [
                        {
                            "text": {
                                "content": self.format_file_size(metadata['file_size'])
                            }
                        }
                    ]
                },
                "Audio File": {
                    "files": []  # Will be populated after file upload
                },
                "Audio Content Type": {
                    "select": {
                        "name": content_type if content_type else "Unknown"
                    }
                },
                "Flagged for Deletion": {
                    "checkbox": deletion_analysis.get('should_delete', False) if deletion_analysis else False
                },
                "Deletion Confidence": {
                    "select": {
                        "name": deletion_analysis.get('confidence', 'low').title() if deletion_analysis and deletion_analysis.get('should_delete') else None
                    }
                } if deletion_analysis and deletion_analysis.get('should_delete') else None,
                "Deletion Reason": {
                    "rich_text": [
                        {
                            "text": {
                                "content": deletion_analysis.get('reason', '') if deletion_analysis else ''
                            }
                        }
                    ]
                }
            }
            
            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            # Create the page content with formatted transcript
            children = self._build_page_content(transcript, original_transcript, claude_tags)
            
            # Create the page
            response = self._make_api_call(
                "create_page",
                parent={"database_id": self.database_id},
                properties=properties,
                children=children,
                use_cache=False  # Don't cache page creation
            )
            
            page_id = response["id"]
            logger.info(f"Successfully created Notion page: {page_id}")
            
            # Add audio file to the page properties
            self.add_audio_file_to_page(page_id, audio_file_path)
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Notion page: {e}")
            return None
    
    def update_page(self, page_id: str, properties: Dict) -> bool:
        """Update an existing Notion page"""
        try:
            self._make_api_call(
                "update_page",
                page_id=page_id,
                properties=properties,
                use_cache=False  # Don't cache page updates
            )
            logger.info(f"Successfully updated Notion page: {page_id}")
            return True
        except APIResponseError as e:
            logger.error(f"Notion API error updating page: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating Notion page: {e}")
            return False

    def update_page_bucket_tags(self, page_id: str, life_domain: str, focus_area: str) -> bool:
        """Update page with bucket classification tags (Phase 3) - single values (legacy)"""
        # Convert single values to arrays and use the multiple version
        life_domains = [life_domain] if life_domain else []
        focus_areas = [focus_area] if focus_area else []
        return self.update_page_bucket_tags_multiple(page_id, life_domains, focus_areas)
    
    def update_page_bucket_tags_multiple(self, page_id: str, life_domains: List[str], focus_areas: List[str]) -> bool:
        """Update page with multiple bucket classification tags"""
        try:
            properties = {}
            
            if life_domains:
                properties["Life Area"] = {
                    "multi_select": [
                        {"name": domain} for domain in life_domains
                    ]
                }
            
            if focus_areas:
                properties["Topic"] = {
                    "multi_select": [
                        {"name": area} for area in focus_areas
                    ]
                }
            
            if properties:
                return self.update_page(page_id, properties)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating bucket tags for page {page_id}: {e}")
            return False

    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a page by ID"""
        try:
            response = self._make_api_call(
                "get_page",
                page_id=page_id,
                use_cache=True,
                cache_ttl=300  # Cache page data for 5 minutes
            )
            return response
        except Exception as e:
            logger.error(f"Error getting page {page_id}: {e}")
            return None

    # CONTENT AND FORMATTING FUNCTIONS
    
    def _build_page_content(self, transcript: str, original_transcript: Optional[str], claude_tags: Dict[str, str]) -> List[Dict]:
        """Build page content blocks with transcript and analysis"""
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Formatted Transcript"
                            }
                        }
                    ]
                }
            }
        ]
        
        # Split transcript into chunks of 2000 characters (Notion's paragraph limit)
        chunk_size = 2000
        
        for i in range(0, len(transcript), chunk_size):
            chunk = transcript[i:i + chunk_size]
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ]
                }
            })
        
        # Add original transcript in a toggle if provided
        if original_transcript and original_transcript != transcript:
            toggle_children = []
            for i in range(0, len(original_transcript), chunk_size):
                chunk = original_transcript[i:i + chunk_size]
                toggle_children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": chunk
                                }
                            }
                        ]
                    }
                })
            
            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Original Transcript"
                            }
                        }
                    ],
                    "children": toggle_children
                }
            })
        
        # Add Claude analysis in a toggle
        analysis_children = []
        
        tag_items = [
            ("Primary Themes", claude_tags.get('primary_themes', 'N/A')),
            ("Specific Focus", claude_tags.get('specific_focus', 'N/A')),
            ("Content Types", claude_tags.get('content_types', 'N/A')),
            ("Emotional Tones", claude_tags.get('emotional_tones', 'N/A')),
            ("Key Topics", claude_tags.get('key_topics', 'N/A'))
        ]
        
        for tag_name, tag_value in tag_items:
            if tag_value and tag_value != 'N/A':
                analysis_children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{tag_name}: {tag_value}"
                                }
                            }
                        ]
                    }
                })
        
        if claude_tags.get('brief_summary'):
            analysis_children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Analysis Summary: {claude_tags['brief_summary']}"
                            },
                            "annotations": {
                                "italic": True
                            }
                        }
                    ]
                }
            })
        
        children.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "Claude Reasoning Summary"
                        }
                    }
                ],
                "children": analysis_children
            }
        })
        
        return children

    # UTILITY FUNCTIONS
    
    def extract_audio_metadata(self, file_path: str) -> Dict[str, any]:
        """Extract metadata from audio file"""
        try:
            # Get file system metadata
            stat = os.stat(file_path)
            file_size = stat.st_size
            
            # Try to get actual recording date from metadata
            file_created = None
            try:
                import subprocess
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if 'format' in data and 'tags' in data['format']:
                        creation_time = data['format']['tags'].get('creation_time')
                        if creation_time:
                            file_created = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                            logger.info(f"Found actual recording date: {file_created}")
            except Exception as e:
                logger.warning(f"Could not extract recording date with ffprobe: {e}")
            
            # Fallback to file system creation time if ffprobe fails
            if not file_created:
                file_created = datetime.fromtimestamp(stat.st_birthtime)
                logger.info(f"Using file system creation date: {file_created}")
            
            # Get audio metadata
            audio_file = File(file_path)
            duration_seconds = 0
            recording_device = ""
            
            if audio_file:
                duration_seconds = audio_file.info.length if hasattr(audio_file.info, 'length') else 0
                
                # Extract recording device info from Apple Voice Memos
                if '©too' in audio_file:
                    tool_info = str(audio_file['©too'][0]) if audio_file['©too'] else ""
                    if 'VoiceMemos' in tool_info:
                        recording_device = "Apple Voice Memos"
            
            return {
                'duration_seconds': duration_seconds,
                'file_created': file_created,
                'file_size': file_size,
                'recording_device': recording_device
            }
            
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
            return {
                'duration_seconds': 0,
                'file_created': None,
                'file_size': 0,
                'recording_device': ""
            }
    
    def format_duration(self, seconds: float) -> str:
        """Format duration from seconds to 'Xm Ys' format"""
        if seconds <= 0:
            return "0s"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes > 0:
            return f"{minutes}m {remaining_seconds}s"
        else:
            return f"{remaining_seconds}s"
    
    def format_file_size(self, bytes_size: int) -> str:
        """Format file size in human readable format"""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        else:
            return f"{bytes_size / (1024 * 1024):.1f} MB"

    # FILE UPLOAD FUNCTIONS
    
    async def add_audio_file_to_page_async(self, page_id: str, audio_file_path: str) -> Dict[str, Any]:
        """
        Upload audio file with async verification - no hardcoded delays
        Returns detailed result instead of just True/False
        """
        # Validate file first
        validation = self._validate_file_for_upload(audio_file_path)
        if not validation["valid"]:
            return {
                "success": False,
                "error_type": "validation_failed",
                "reason": validation["reason"]
            }
        
        filename = validation["filename"]
        logger.info(f"Starting async upload process for {filename}")
        
        try:
            # Check if file is already uploaded
            if self._is_file_already_uploaded(page_id, filename):
                return {
                    "success": True,
                    "status": "already_uploaded",
                    "reason": f"File {filename} already exists"
                }
            
            # Upload file to Notion storage
            upload_id = self.upload_file_to_notion_storage(audio_file_path)
            
            if not upload_id:
                return {
                    "success": False,
                    "error_type": "upload_failed",
                    "reason": "Failed to upload file to Notion storage"
                }
            
            # Update page properties to include the audio file
            properties = {
                "Audio File": {
                    "files": [
                        {
                            "type": "file_upload",
                            "file_upload": {
                                "id": upload_id
                            },
                            "name": filename
                        }
                    ]
                }
            }
            
            try:
                await self.async_client.pages.update(
                    page_id=page_id,
                    properties=properties
                )
            except Exception as e:
                return {
                    "success": False,
                    "error_type": "page_update_failed",
                    "reason": f"Failed to update page properties: {str(e)}"
                }
            
            # Verify upload completion using async polling - NO HARDCODED DELAYS
            verification_result = await self._verify_upload_completion_async(
                page_id, filename, upload_id, max_wait_seconds=120
            )
            
            if verification_result["success"]:
                logger.info(f"Successfully uploaded and verified: {filename}")
                return {
                    "success": True,
                    "status": "upload_complete",
                    "file_url": verification_result.get("file_url"),
                    "reason": f"Successfully uploaded and verified {filename}"
                }
            else:
                logger.error(f"Upload verification failed for {filename}: {verification_result['reason']}")
                return {
                    "success": False,
                    "error_type": "verification_failed",
                    "reason": verification_result["reason"]
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in async upload for {filename}: {e}")
            return {
                "success": False,
                "error_type": "unexpected_error",
                "reason": str(e)
            }

    def add_audio_file_to_page(self, page_id: str, audio_file_path: str) -> bool:
        """
        Synchronous wrapper for async upload method - maintains backwards compatibility
        """
        try:
            # Run the async method in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.add_audio_file_to_page_async(page_id, audio_file_path)
                )
                return result["success"]
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync wrapper for upload: {e}")
            return False

    def upload_file_to_notion_storage(self, file_path: str) -> Optional[str]:
        """Upload file to Notion's storage using their official API"""
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Uploading {filename} ({file_size / 1024 / 1024:.2f} MB) to Notion storage...")
            
            # Check if file is small enough for single-part upload
            if file_size <= 20 * 1024 * 1024:  # 20MB
                return self._upload_single_part_file(file_path)
            else:
                return self._upload_multi_part_file(file_path)
                
        except Exception as e:
            logger.error(f"Error uploading file to Notion: {e}")
            return None

    def _upload_single_part_file(self, file_path: str) -> Optional[str]:
        """Upload small file (≤20MB) using single-part upload"""
        try:
            filename = os.path.basename(file_path)
            
            # Step 1: Create file upload
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            create_upload_data = {
                "mode": "single_part",
                "filename": filename
            }
            
            response = requests.post(
                'https://api.notion.com/v1/file_uploads',
                headers=headers,
                json=create_upload_data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to create file upload: {response.text}")
                return None
            
            upload_data = response.json()
            upload_id = upload_data['id']
            upload_url = upload_data['upload_url']
            
            logger.info(f"Created file upload with ID: {upload_id}")
            
            # Step 2: Upload the file
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'audio/mp4')}
                upload_headers = {
                    'Authorization': f'Bearer {NOTION_TOKEN}',
                    'Notion-Version': '2022-06-28'
                }
                
                upload_response = requests.post(upload_url, files=files, headers=upload_headers)
                
                if upload_response.status_code not in [200, 201]:
                    logger.error(f"Failed to upload file: {upload_response.text}")
                    return None
            
            logger.info(f"Successfully uploaded file: {filename}")
            return upload_id
            
        except Exception as e:
            logger.error(f"Error in single-part upload: {e}")
            return None

    def _upload_multi_part_file(self, file_path: str) -> Optional[str]:
        """Upload large file (>20MB) using multi-part upload"""
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Calculate number of parts (10MB each)
            part_size = 10 * 1024 * 1024  # 10MB
            number_of_parts = (file_size + part_size - 1) // part_size
            
            logger.info(f"Uploading {filename} in {number_of_parts} parts...")
            
            # Step 1: Create multi-part file upload
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            create_upload_data = {
                "mode": "multi_part",
                "number_of_parts": number_of_parts,
                "filename": filename
            }
            
            response = requests.post(
                'https://api.notion.com/v1/file_uploads',
                headers=headers,
                json=create_upload_data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to create multi-part upload: {response.text}")
                return None
            
            upload_data = response.json()
            upload_id = upload_data['id']
            upload_url = upload_data['upload_url']
            
            logger.info(f"Created multi-part upload with ID: {upload_id}")
            
            # Step 2: Upload each part
            with open(file_path, 'rb') as f:
                for part_number in range(1, number_of_parts + 1):
                    # Read the part
                    if part_number == number_of_parts:
                        # Last part - read remaining bytes
                        part_data = f.read()
                    else:
                        # Regular part - read 10MB
                        part_data = f.read(part_size)
                    
                    # Upload the part
                    files = {
                        'file': (f'{filename}_part_{part_number}', part_data, 'application/octet-stream'),
                        'part_number': (None, str(part_number))
                    }
                    
                    upload_headers = {
                        'Authorization': f'Bearer {NOTION_TOKEN}',
                        'Notion-Version': '2022-06-28'
                    }
                    
                    part_response = requests.post(upload_url, files=files, headers=upload_headers)
                    
                    if part_response.status_code not in [200, 201]:
                        logger.error(f"Failed to upload part {part_number}: {part_response.text}")
                        return None
                    
                    logger.info(f"Uploaded part {part_number}/{number_of_parts}")
            
            # Step 3: Complete the upload
            complete_url = f'https://api.notion.com/v1/file_uploads/{upload_id}/complete'
            complete_response = requests.post(complete_url, headers=headers)
            
            if complete_response.status_code != 200:
                logger.error(f"Failed to complete upload: {complete_response.text}")
                return None
            
            logger.info(f"Successfully completed multi-part upload: {filename}")
            return upload_id
            
        except Exception as e:
            logger.error(f"Error in multi-part upload: {e}")
            return None

    # UPLOAD LOGIC FUNCTIONS (Pure logic, no API calls)
    
    def _should_retry_upload(self, error_type: str, is_timeout: bool) -> bool:
        """Determine if an upload should be retried based on error type"""
        # Always retry timeouts and upload failures, never retry auth/permission errors
        timeout_errors = ["timeout", "request_timeout", "connection_timeout"]
        retryable_errors = ["upload_failed", "verification_failed", "storage_error"]
        non_retryable_errors = ["unauthorized", "forbidden", "not_found", "invalid_request"]
        
        if is_timeout or any(t in error_type.lower() for t in timeout_errors):
            return True
        if any(r in error_type.lower() for r in retryable_errors):
            return True
        if any(nr in error_type.lower() for nr in non_retryable_errors):
            return False
        
        # Default: retry unknown errors (better safe than sorry)
        return True
    
    def _calculate_retry_delay(self, attempt_count: int, is_timeout: bool) -> float:
        """Calculate delay before retry based on attempt count and error type"""
        if is_timeout:
            return min(5.0 * (2 ** attempt_count), 30.0)  # Exponential backoff, max 30s
        else:
            return min(2.0 * attempt_count, 10.0)  # Linear backoff, max 10s
    
    def _validate_file_for_upload(self, file_path: str) -> Dict[str, Any]:
        """Validate file is suitable for upload - pure logic, no API calls"""
        if not os.path.exists(file_path):
            return {"valid": False, "reason": "file_not_found"}
        
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Check file size limits
        if file_size == 0:
            return {"valid": False, "reason": "empty_file"}
        if file_size_mb > 100:  # 100MB limit
            return {"valid": False, "reason": "file_too_large"}
        
        # Check file extension
        filename = os.path.basename(file_path)
        valid_extensions = ['.m4a', '.mp3', '.wav', '.aiff', '.mp4', '.mov']
        if not any(filename.lower().endswith(ext) for ext in valid_extensions):
            return {"valid": False, "reason": "invalid_format"}
        
        return {
            "valid": True, 
            "file_size_mb": file_size_mb,
            "filename": filename,
            "use_multipart": file_size_mb > 20  # Use multipart for files > 20MB
        }
    
    def _extract_error_type_from_exception(self, exception: Exception) -> str:
        """Extract standardized error type from exception for retry logic"""
        error_str = str(exception).lower()
        
        if isinstance(exception, RequestTimeoutError):
            return "timeout"
        elif "timeout" in error_str:
            return "timeout"
        elif "413" in error_str or "payload too large" in error_str:
            return "file_too_large"
        elif "401" in error_str or "unauthorized" in error_str:
            return "unauthorized"
        elif "403" in error_str or "forbidden" in error_str:
            return "forbidden"
        elif "404" in error_str or "not found" in error_str:
            return "not_found"
        elif "429" in error_str or "rate limit" in error_str:
            return "rate_limit"
        else:
            return "unknown_error"
    
    def _parse_file_info_from_response(self, response: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Parse file information from Notion API response - pure data processing"""
        audio_files = response.get('properties', {}).get('Audio File', {}).get('files', [])
        
        for file_info in audio_files:
            if file_info.get('name') == filename:
                file_url = file_info.get('file', {}).get('url')
                external_url = file_info.get('external', {}).get('url')
                
                return {
                    "found": True,
                    "has_url": bool(file_url or external_url),
                    "file_url": file_url,
                    "external_url": external_url,
                    "upload_complete": bool(file_url or external_url)
                }
        
        return {"found": False, "has_url": False, "upload_complete": False}

    # UPLOAD API FUNCTIONS (Makes actual API calls)
    
    def _is_file_already_uploaded(self, page_id: str, filename: str) -> bool:
        """Check if file is already successfully uploaded to the page"""
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            file_info = self._parse_file_info_from_response(response, filename)
            return file_info["upload_complete"]
        except Exception as e:
            logger.debug(f"Error checking existing upload: {e}")
            return False
    
    async def _verify_upload_completion_async(self, page_id: str, filename: str, upload_id: str, max_wait_seconds: int = 120) -> Dict[str, Any]:
        """
        Verify upload completion by checking upload status and page properties
        Uses proper async/await instead of hardcoded delays
        """
        try:
            # Step 1: Wait for upload to be processed by Notion
            upload_status = await self._wait_for_upload_status(upload_id, max_wait_seconds)
            
            if not upload_status["success"]:
                return upload_status
            
            # Step 2: Verify file appears in page properties
            page_verification = await self._verify_file_in_page_properties(page_id, filename)
            
            return page_verification
            
        except Exception as e:
            logger.error(f"Error in async upload verification: {e}")
            return {
                "success": False,
                "status": "verification_error",
                "reason": str(e)
            }

    async def _wait_for_upload_status(self, upload_id: str, max_wait_seconds: int) -> Dict[str, Any]:
        """
        Wait for upload to reach 'uploaded' status using exponential backoff
        This replaces hardcoded time.sleep() with proper async waiting
        """
        start_time = time.time()
        check_interval = 0.1  # Start with 100ms
        max_interval = 2.0    # Cap at 2 seconds
        
        logger.info(f"Waiting for upload {upload_id} to complete...")
        
        while time.time() - start_time < max_wait_seconds:
            try:
                # Check upload status via Notion API
                status_response = await self._check_upload_status_async(upload_id)
                
                if status_response["status"] == "uploaded":
                    logger.info(f"Upload {upload_id} completed successfully")
                    return {
                        "success": True,
                        "status": "uploaded"
                    }
                elif status_response["status"] == "failed":
                    logger.error(f"Upload {upload_id} failed: {status_response.get('error_message', 'Unknown error')}")
                    return {
                        "success": False,
                        "status": "failed",
                        "reason": status_response.get("error_message", "Upload failed")
                    }
                elif status_response["status"] == "pending":
                    # Still processing, wait and check again
                    logger.debug(f"Upload {upload_id} still pending, checking again in {check_interval}s")
                    await asyncio.sleep(check_interval)
                    
                    # Exponential backoff - but cap the interval
                    check_interval = min(check_interval * 1.5, max_interval)
                else:
                    # Unknown status, wait and try again
                    logger.debug(f"Upload {upload_id} has unknown status: {status_response.get('status')}")
                    await asyncio.sleep(check_interval)
                    check_interval = min(check_interval * 1.5, max_interval)
                    
            except Exception as e:
                logger.warning(f"Error checking upload status, retrying: {e}")
                await asyncio.sleep(check_interval)
                check_interval = min(check_interval * 1.5, max_interval)
        
        return {
            "success": False,
            "status": "timeout",
            "reason": f"Upload status check timed out after {max_wait_seconds} seconds"
        }

    async def _check_upload_status_async(self, upload_id: str) -> Dict[str, Any]:
        """Check upload status using Notion's async API"""
        try:
            # Use Notion's file upload status endpoint
            headers = {
                'Authorization': f'Bearer {NOTION_TOKEN}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://api.notion.com/v1/file_uploads/{upload_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": data.get("status", "unknown"),
                    "error_message": data.get("error_message"),
                    "expiry_time": data.get("expiry_time")
                }
            else:
                logger.warning(f"Upload status check returned {response.status_code}: {response.text}")
                return {
                    "status": "unknown",
                    "error_message": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error checking upload status via API: {e}")
            return {
                "status": "error", 
                "error_message": str(e)
            }

    async def _verify_file_in_page_properties(self, page_id: str, filename: str) -> Dict[str, Any]:
        """Verify file appears in page properties with valid URL"""
        try:
            response = await self.async_client.pages.retrieve(page_id=page_id)
            file_info = self._parse_file_info_from_response(response, filename)
            
            if file_info["upload_complete"]:
                logger.info(f"File verification successful: {filename} has valid URL")
                return {
                    "success": True,
                    "status": "verified",
                    "file_url": file_info.get("file_url") or file_info.get("external_url")
                }
            elif file_info["found"]:
                logger.warning(f"File verification failed: {filename} found but no URL")
                return {
                    "success": False,
                    "status": "no_url",
                    "reason": "File found in page but has no accessible URL"
                }
            else:
                logger.warning(f"File verification failed: {filename} not found in page properties")
                return {
                    "success": False,
                    "status": "not_found",
                    "reason": "File not found in page properties"
                }
                
        except Exception as e:
            logger.error(f"Error verifying file in page properties: {e}")
            return {
                "success": False,
                "status": "verification_error", 
                "reason": str(e)
            }