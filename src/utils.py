"""
Utils - Pure utility functions
Contains helper functions for data processing, formatting, and validation
"""

import os
import re
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

def validate_audio_file(file_path: str) -> Dict[str, Any]:
    """Validate if file is a supported audio file"""
    supported_formats = ['.m4a', '.mp3', '.wav', '.aiff', '.mp4', '.mov']
    
    if not os.path.exists(file_path):
        return {"valid": False, "reason": "file_not_found"}
    
    file_size = os.path.getsize(file_path)
    file_extension = Path(file_path).suffix.lower()
    
    if file_size == 0:
        return {"valid": False, "reason": "empty_file"}
    
    if file_extension not in supported_formats:
        return {"valid": False, "reason": "unsupported_format"}
    
    return {
        "valid": True,
        "file_size": file_size,
        "file_extension": file_extension,
        "filename": os.path.basename(file_path)
    }

def clean_filename(filename: str) -> str:
    """Clean filename for use as title"""
    # Remove extension
    base_name = Path(filename).stem
    
    # Replace underscores and hyphens with spaces
    cleaned = base_name.replace('_', ' ').replace('-', ' ')
    
    # Remove extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def format_duration_human(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds <= 0:
        return "0s"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {remaining_seconds}s"
    elif minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s"

def format_file_size_human(bytes_size: int) -> str:
    """Format file size in human-readable format"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB" 
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"

def parse_comma_separated_tags(tag_string: str) -> List[str]:
    """Parse comma-separated tags into clean list"""
    if not tag_string:
        return []
    
    # Remove brackets if present
    cleaned = tag_string.replace('[', '').replace(']', '')
    
    # Split by comma and clean each tag
    tags = [tag.strip() for tag in cleaned.split(',') if tag.strip()]
    
    return tags

def format_tags_for_notion(tags: List[str]) -> List[Dict[str, str]]:
    """Format tag list for Notion multi-select format"""
    return [{"name": tag} for tag in tags if tag]

def clean_text_for_notion(text: str, max_length: Optional[int] = None) -> str:
    """Clean text for Notion compatibility"""
    if not text:
        return ""
    
    # Remove or replace problematic characters
    cleaned = text.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
    
    # Truncate if max_length specified
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length-3] + "..."
    
    return cleaned

def chunk_text(text: str, chunk_size: int = 2000) -> List[str]:
    """Split text into chunks for Notion paragraph limits"""
    if not text:
        return []
    
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
    
    return chunks

def generate_cache_key(*args, **kwargs) -> str:
    """Generate consistent cache key from arguments"""
    key_data = f"{str(args)}:{json.dumps(kwargs, sort_keys=True, default=str)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def safe_get_nested_value(data: dict, path: str, default: Any = None) -> Any:
    """Safely get nested dictionary value using dot notation"""
    keys = path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

def merge_dictionaries(*dicts) -> Dict[str, Any]:
    """Merge multiple dictionaries, with later ones taking precedence"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result

def filter_empty_values(data: dict) -> dict:
    """Remove keys with None, empty string, or empty list values"""
    return {k: v for k, v in data.items() if v is not None and v != "" and v != []}

def title_case_text(text: str) -> str:
    """Apply proper title case capitalization"""
    if not text:
        return text
    
    # Words that should remain lowercase unless they're the first word
    lowercase_words = {
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'nor', 
        'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet'
    }
    
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

def extract_title_from_content(content: str, max_words: int = 8) -> str:
    """Extract a reasonable title from content"""
    if not content:
        return "Untitled"
    
    # Try to get first sentence
    sentences = content.split('.')
    first_sentence = sentences[0].strip() if sentences else content.strip()
    
    # Remove quotes and clean
    first_sentence = first_sentence.replace('"', '').replace("'", "")
    
    # Split into words and limit
    words = first_sentence.split()
    if len(words) <= max_words and 3 <= len(words):
        return title_case_text(' '.join(words))
    elif len(words) > max_words:
        return title_case_text(' '.join(words[:max_words]))
    
    # If too short, try to use more content
    all_words = content.replace('\n', ' ').split()
    if len(all_words) >= 3:
        title_words = all_words[:min(max_words, len(all_words))]
        return title_case_text(' '.join(title_words))
    
    return "Voice Memo"

def validate_notion_properties(properties: dict) -> Tuple[bool, List[str]]:
    """Validate Notion properties structure"""
    errors = []
    
    # Check required title property
    if 'Title' not in properties:
        errors.append("Missing required 'Title' property")
    elif 'title' not in properties['Title'] or not properties['Title']['title']:
        errors.append("Title property must have 'title' field with content")
    
    # Validate Tags field (now rich_text instead of multi_select)
    if 'Tags' in properties:
        if 'rich_text' not in properties['Tags']:
            errors.append("Tags must have 'rich_text' field")
        elif not isinstance(properties['Tags']['rich_text'], list):
            errors.append("Tags rich_text must be a list")
    
    # Validate rich text properties
    rich_text_props = ['Summary', 'Duration', 'File Size', 'Deletion Reason']
    for prop in rich_text_props:
        if prop in properties:
            if 'rich_text' not in properties[prop]:
                errors.append(f"{prop} must have 'rich_text' field")
            elif not isinstance(properties[prop]['rich_text'], list):
                errors.append(f"{prop} rich_text must be a list")
    
    return len(errors) == 0, errors

def normalize_tag_name(tag: str) -> str:
    """Normalize tag name for consistency"""
    if not tag:
        return ""
    
    # Remove extra spaces and capitalize properly
    normalized = ' '.join(tag.split())
    
    # Apply title case
    return title_case_text(normalized)

def deduplicate_tags(tags: List[str]) -> List[str]:
    """Remove duplicate tags while preserving order"""
    seen = set()
    deduped = []
    
    for tag in tags:
        normalized = normalize_tag_name(tag)
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            deduped.append(normalized)
    
    return deduped

def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split items into batches of specified size"""
    batches = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batches.append(batch)
    return batches

def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage with division by zero protection"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)

def format_timestamp(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    if not dt:
        return ""
    return dt.strftime(format_string)

def parse_iso_timestamp(timestamp_string: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime object"""
    if not timestamp_string:
        return None
    
    try:
        # Handle different ISO formats
        if timestamp_string.endswith('Z'):
            timestamp_string = timestamp_string.replace('Z', '+00:00')
        
        return datetime.fromisoformat(timestamp_string)
    except ValueError:
        return None

def sanitize_json_for_logging(data: Any, max_length: int = 500) -> str:
    """Safely convert data to JSON string for logging"""
    try:
        json_str = json.dumps(data, default=str, ensure_ascii=False)
        if len(json_str) > max_length:
            return json_str[:max_length] + "..."
        return json_str
    except Exception:
        return str(data)[:max_length]