import logging
import os
import requests
import mimetypes
import base64
import shutil
import subprocess
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError
from config.config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_PARENT_PAGE_ID, save_database_id
from mutagen import File

logger = logging.getLogger(__name__)

class NotionUploader:
    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN not found in environment variables")
            
        self.client = Client(auth=NOTION_TOKEN)
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
    
    def extract_audio_metadata(self, file_path: str) -> Dict[str, any]:
        """Extract metadata from audio file"""
        try:
            # Get file system metadata
            stat = os.stat(file_path)
            file_size = stat.st_size
            
            # Try to get actual recording date from ffprobe
            file_created = None
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if 'format' in data and 'tags' in data['format']:
                        creation_time = data['format']['tags'].get('creation_time')
                        if creation_time:
                            # Parse ISO 8601 format: 2025-04-12T17:36:58.000000Z
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
    
    def generate_headline_from_transcript(self, transcript: str, summary: str, claude_tags: Dict[str, str]) -> str:
        """Generate a specific, properly capitalized headline from content"""
        if not transcript:
            return "Voice Memo"
        
        # Use Claude to generate a proper headline that's specific and well-formatted
        try:
            headline_prompt = f"""Create a specific, compelling title for this voice memo. The title should:
1. Be 3-8 words long
2. Capture the specific essence of the content
3. Use proper capitalization (Title Case)
4. Be specific, not generic

Content context:
Primary Theme: {claude_tags.get('primary_theme', '')}
Specific Focus: {claude_tags.get('specific_focus', '')}
Key Topics: {claude_tags.get('key_topics', '')}
Summary: {summary[:200]}
First 100 chars of transcript: {transcript[:100]}

Generate just the title, nothing else."""

            from anthropic import Anthropic
            from config.config import CLAUDE_API_KEY
            
            if CLAUDE_API_KEY:
                client = Anthropic(api_key=CLAUDE_API_KEY)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    temperature=0.3,
                    messages=[{"role": "user", "content": headline_prompt}]
                )
                
                generated_title = response.content[0].text.strip()
                # Clean up any quotes or extra formatting
                generated_title = generated_title.replace('"', '').replace("'", "").strip()
                
                if 3 <= len(generated_title.split()) <= 8:
                    return generated_title
            
        except Exception as e:
            logger.warning(f"Could not generate Claude headline: {e}")
        
        # Fallback to improved extraction method
        return self._extract_title_from_content(transcript, summary, claude_tags)
    
    def _extract_title_from_content(self, transcript: str, summary: str, claude_tags: Dict[str, str]) -> str:
        """Fallback method to extract title from content"""
        # Try to use primary theme + specific focus for a good title
        primary_theme = claude_tags.get('primary_theme', '')
        specific_focus = claude_tags.get('specific_focus', '')
        
        if primary_theme and specific_focus:
            # Combine theme and focus into a title
            combined = f"{primary_theme}: {specific_focus}"
            if len(combined) <= 50:
                return self._title_case_properly(combined)
        
        # Try extracting from first sentence
        sentences = transcript.split('.')
        first_sentence = sentences[0].strip() if sentences else transcript.strip()
        first_sentence = first_sentence.replace('"', '').replace("'", "")
        
        if 15 <= len(first_sentence) <= 50:
            return self._title_case_properly(first_sentence)
        
        # Use primary theme if available
        if primary_theme:
            return self._title_case_properly(primary_theme)
        
        return "Voice Memo"
    
    def _title_case_properly(self, text: str) -> str:
        """Apply proper title case capitalization"""
        # Words that should remain lowercase unless they're the first word
        lowercase_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet'}
        
        words = text.split()
        title_cased = []
        
        for i, word in enumerate(words):
            # Clean the word
            clean_word = word.strip('.,!?:;')
            punctuation = word[len(clean_word):]
            
            # First word is always capitalized, others follow rules
            if i == 0 or clean_word.lower() not in lowercase_words:
                title_cased.append(clean_word.capitalize() + punctuation)
            else:
                title_cased.append(clean_word.lower() + punctuation)
        
        return ' '.join(title_cased)
        
    def create_page(self, 
                   title: str,
                   transcript: str,
                   claude_tags: Dict[str, str],
                   summary: str,
                   filename: str,
                   audio_file_path: str,
                   audio_duration: Optional[float] = None,
                   deletion_analysis: Optional[Dict] = None,
                   original_transcript: Optional[str] = None) -> Optional[str]:
        """
        Create a new page in the Notion database with the voice memo data
        """
        try:
            # Extract audio metadata
            metadata = self.extract_audio_metadata(audio_file_path)
            
            # Generate headline from transcript
            headline = self.generate_headline_from_transcript(transcript, summary, claude_tags)
            
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
                                "content": headline
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
            
            # Create the page content with formatted transcript and Claude analysis
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
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": transcript[:32000]  # Using formatted transcript - increased limit
                                }
                            }
                        ]
                    }
                }
            ]
            
            # Add original transcript in a toggle if provided
            if original_transcript and original_transcript != transcript:
                children.extend([
                    {
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
                            "children": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": original_transcript[:32000]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ])
            
            # Add Claude analysis in a toggle
            toggle_children = []
            
            # Add each standardized tag type
            tag_items = [
                ("Primary Themes", claude_tags.get('primary_themes', 'N/A')),
                ("Specific Focus", claude_tags.get('specific_focus', 'N/A')),
                ("Content Types", claude_tags.get('content_types', 'N/A')),
                ("Emotional Tones", claude_tags.get('emotional_tones', 'N/A')),
                ("Key Topics", claude_tags.get('key_topics', 'N/A'))
            ]
            
            for tag_name, tag_value in tag_items:
                if tag_value and tag_value != 'N/A':
                    toggle_children.append({
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
            
            # Add brief summary if available
            if claude_tags.get('brief_summary'):
                toggle_children.append({
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
            
            # Create the toggle block
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
                    "children": toggle_children
                }
            })
            
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
            self.add_audio_file_to_properties(page_id, audio_file_path)
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Notion page: {e}")
            return None
    
    def update_page(self, page_id: str, properties: Dict) -> bool:
        """
        Update an existing Notion page
        """
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
    
    def check_database_exists(self) -> bool:
        """
        Check if the specified database exists and is accessible
        """
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
        """
        Create a new database for voice memos if needed
        This requires a parent page ID where the database will be created
        """
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
    
    def upload_file_to_notion_storage(self, file_path: str) -> Optional[str]:
        """
        Upload file to Notion's storage using their official API
        """
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
        """
        Upload small file (≤20MB) using single-part upload
        """
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
        """
        Upload large file (>20MB) using multi-part upload
        """
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
    
    # ===== LOGIC FUNCTIONS (Pure logic, no API calls - can be unit tested) =====
    
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
    
    def _should_use_multipart_upload(self, file_size_bytes: int) -> bool:
        """Determine if file should use multipart upload strategy"""
        return (file_size_bytes / (1024 * 1024)) > 20  # 20MB threshold
    
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
    
    # ===== API FUNCTIONS (Makes actual API calls - integration tested) =====
    
    def add_audio_file_to_properties(self, page_id: str, audio_file_path: str) -> bool:
        """
        Upload audio file to Notion storage and add to page properties with completion verification
        """
        # Validate file first (pure logic)
        validation = self._validate_file_for_upload(audio_file_path)
        if not validation["valid"]:
            logger.error(f"File validation failed: {validation['reason']}")
            return False
        
        filename = validation["filename"]
        logger.info(f"Starting upload process for {filename}")
        
        attempt_count = 0
        
        # Keep trying until file is successfully uploaded and verified
        while True:
            attempt_count += 1
            
            try:
                # Check if file is already uploaded by checking page properties
                if self._is_file_already_uploaded(page_id, filename):
                    logger.info(f"File {filename} already uploaded successfully")
                    return True
                
                # Upload file to Notion storage
                upload_id = self.upload_file_to_notion_storage(audio_file_path)
                
                if not upload_id:
                    error_type = "upload_failed"
                    if self._should_retry_upload(error_type, False):
                        delay = self._calculate_retry_delay(attempt_count, False)
                        logger.warning(f"Upload attempt {attempt_count} failed for {filename}, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Upload failed and not retryable for {filename}")
                        return False
                
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
                
                self.client.pages.update(
                    page_id=page_id,
                    properties=properties
                )
                
                # Verify the upload completed by checking if file appears in page properties
                if self._verify_upload_completion(page_id, filename):
                    logger.info(f"Successfully uploaded and verified: {filename}")
                    return True
                else:
                    error_type = "verification_failed"
                    if self._should_retry_upload(error_type, False):
                        delay = self._calculate_retry_delay(attempt_count, False)
                        logger.warning(f"Upload completed but verification failed for {filename}, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Verification failed and not retryable for {filename}")
                        return False
                    
            except (APIResponseError, RequestTimeoutError) as e:
                error_type = self._extract_error_type_from_exception(e)
                is_timeout = error_type == "timeout"
                
                if self._should_retry_upload(error_type, is_timeout):
                    delay = self._calculate_retry_delay(attempt_count, is_timeout)
                    logger.warning(f"Error during upload of {filename} (attempt {attempt_count}): {error_type}, retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Non-recoverable error uploading {filename}: {e}")
                    return False
            except Exception as e:
                error_type = self._extract_error_type_from_exception(e)
                logger.error(f"Unexpected error uploading {filename}: {e}")
                
                if self._should_retry_upload(error_type, False):
                    delay = self._calculate_retry_delay(attempt_count, False)
                    time.sleep(delay)
                    continue
                else:
                    return False
    
    def _is_file_already_uploaded(self, page_id: str, filename: str) -> bool:
        """Check if file is already successfully uploaded to the page"""
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            file_info = self._parse_file_info_from_response(response, filename)
            return file_info["upload_complete"]
        except Exception as e:
            logger.debug(f"Error checking existing upload: {e}")
            return False
    
    def _verify_upload_completion(self, page_id: str, filename: str) -> bool:
        """Verify that the file upload completed successfully by checking page properties"""
        try:
            # Wait a moment for Notion to process the upload
            time.sleep(2)
            
            response = self.client.pages.retrieve(page_id=page_id)
            file_info = self._parse_file_info_from_response(response, filename)
            
            if file_info["upload_complete"]:
                logger.debug(f"Upload verification successful: {filename} has valid URL")
                return True
            elif file_info["found"]:
                logger.debug(f"Upload verification failed: {filename} found but no URL")
                return False
            else:
                logger.debug(f"Upload verification failed: {filename} not found in page properties")
                return False
            
        except Exception as e:
            logger.error(f"Error verifying upload completion: {e}")
            return False
    
    def create_file_block(self, file_url: str, filename: str) -> dict:
        """
        Create a file block for Notion page
        """
        return {
            "object": "block",
            "type": "file",
            "file": {
                "type": "external",
                "external": {
                    "url": file_url
                },
                "caption": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"Audio: {filename}"
                        }
                    }
                ]
            }
        }
