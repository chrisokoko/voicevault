"""
Pytest configuration and fixtures for VoiceVault testing
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import json
import time

# Import our modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.notion_uploader import NotionUploader
from src.claude_tagger import ClaudeTagger
from config.config import AUDIO_FOLDER

class TestFileManager:
    """Manages static test audio files with known characteristics"""
    
    def __init__(self):
        self.fixtures_dir = Path(__file__).parent / 'fixtures' / 'audio_samples'
        self._static_files = {
            'tiny': [
                'test_0kb_0sec_voice.m4a',  # 0KB edge case
            ],
            'small': [
                '30s test - NE Cully Blvd.m4a',  # ~0.27MB, 32s
                'no text - Edificio Paso Moná  .m4a',  # ~0.07MB, 8.3s
            ],
            'medium': [
                'background noise - Wallflower Coffee Company 19.m4a',  # ~0.49MB, 59.6s
            ],
            'large': [
                '40 min test - Odyssey - Interview Questions.m4a',  # ~19.19MB, 2312.4s
            ],
            'xlarge': [
                'test_corrupted_voice.m4a',  # Corrupted edge case
            ]
        }
        
        # Also support fallback to dynamic discovery for integration tests
        self.audio_folder = Path(AUDIO_FOLDER) if AUDIO_FOLDER else None
    
    def get_categorized_files(self) -> Dict[str, List[Path]]:
        """Get static test files, with fallback to dynamic discovery"""
        files = {category: [] for category in self._static_files.keys()}
        
        # Try to use static test files first
        for category, filenames in self._static_files.items():
            for filename in filenames:
                file_path = self.fixtures_dir / filename
                if file_path.exists():
                    files[category].append(file_path)
        
        # If no static files found, fall back to dynamic discovery from audio_files
        total_static_files = sum(len(file_list) for file_list in files.values())
        if total_static_files == 0 and self.audio_folder and self.audio_folder.exists():
            print("No static test files found, falling back to dynamic discovery")
            return self._discover_files_dynamically()
        
        return files
    
    def _discover_files_dynamically(self) -> Dict[str, List[Path]]:
        """Fallback method to discover files from audio_files directory"""
        files = {
            'tiny': [],      # < 50KB
            'small': [],     # 50KB - 1MB
            'medium': [],    # 1MB - 5MB
            'large': [],     # 5MB - 15MB
            'xlarge': []     # > 15MB
        }
        
        for file_path in self.audio_folder.glob('*.m4a'):
            if not file_path.is_file():
                continue
                
            size_bytes = file_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            
            if size_bytes < 50 * 1024:  # < 50KB
                files['tiny'].append(file_path)
            elif size_mb < 1:  # < 1MB
                files['small'].append(file_path)
            elif size_mb < 5:  # < 5MB
                files['medium'].append(file_path)
            elif size_mb < 15:  # < 15MB
                files['large'].append(file_path)
            else:  # >= 15MB
                files['xlarge'].append(file_path)
        
        # Sort by size within each category and limit to 3 per category
        for category in files:
            files[category].sort(key=lambda f: f.stat().st_size)
            files[category] = files[category][:3]  # Limit for performance
        
        return files
    
    def get_test_file(self, size_category: str, index: int = 0) -> Path:
        """Get a specific test file by size category"""
        files = self.get_categorized_files()
        category_files = files.get(size_category, [])
        
        if not category_files:
            pytest.skip(f"No {size_category} files available for testing")
        
        if index >= len(category_files):
            index = 0  # Use first file if index out of range
        
        return category_files[index]
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get detailed info about a test file"""
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        
        return {
            'path': file_path,
            'name': file_path.name,
            'size_bytes': stat.st_size,
            'size_mb': round(size_mb, 2),
            'size_category': self._get_size_category(stat.st_size)
        }
    
    def _get_size_category(self, size_bytes: int) -> str:
        """Determine size category for a file"""
        size_mb = size_bytes / (1024 * 1024)
        
        if size_bytes < 50 * 1024:
            return 'tiny'
        elif size_mb < 1:
            return 'small'
        elif size_mb < 5:
            return 'medium'
        elif size_mb < 15:
            return 'large'
        else:
            return 'xlarge'

@pytest.fixture(scope="session")
def file_manager():
    """Provide a file manager for the entire test session"""
    return TestFileManager()

@pytest.fixture(scope="session")
def categorized_files(file_manager):
    """Provide categorized test files for the session"""
    files = file_manager.get_categorized_files()
    
    # Print file summary for debugging
    print(f"\n📁 Test Files Available:")
    for category, file_list in files.items():
        print(f"  {category}: {len(file_list)} files")
        if file_list:
            sizes = [f.stat().st_size / (1024 * 1024) for f in file_list[:3]]
            print(f"    Sample sizes: {[f'{s:.2f}MB' for s in sizes]}")
    
    return files

@pytest.fixture
def tiny_file(file_manager):
    """Provide a tiny test file (< 50KB)"""
    return file_manager.get_test_file('tiny')

@pytest.fixture  
def small_file(file_manager):
    """Provide a small test file (50KB - 1MB)"""
    return file_manager.get_test_file('small')

@pytest.fixture
def medium_file(file_manager):
    """Provide a medium test file (1MB - 5MB)"""
    return file_manager.get_test_file('medium')

@pytest.fixture
def large_file(file_manager):
    """Provide a large test file (5MB - 15MB)"""
    return file_manager.get_test_file('large')

@pytest.fixture
def xlarge_file(file_manager):
    """Provide an extra large test file (> 15MB)"""
    return file_manager.get_test_file('xlarge')

@pytest.fixture
def mock_notion_client():
    """Mock Notion client for unit tests"""
    mock_client = Mock()
    
    # Mock successful database retrieval
    mock_client.databases.retrieve.return_value = {
        'id': 'test-db-id',
        'title': [{'plain_text': 'Test Voice Memos'}]
    }
    
    # Mock successful page creation
    mock_client.pages.create.return_value = {
        'id': 'test-page-id',
        'properties': {}
    }
    
    # Mock successful page update
    mock_client.pages.update.return_value = {
        'id': 'test-page-id',
        'properties': {
            'Audio File': {
                'files': [
                    {
                        'name': 'test.m4a',
                        'file': {'url': 'https://notion.so/test-file-url'}
                    }
                ]
            }
        }
    }
    
    # Mock successful page retrieval
    mock_client.pages.retrieve.return_value = {
        'id': 'test-page-id',
        'properties': {
            'Audio File': {
                'files': [
                    {
                        'name': 'test.m4a',
                        'file': {'url': 'https://notion.so/test-file-url'}
                    }
                ]
            }
        }
    }
    
    return mock_client

@pytest.fixture
def mock_notion_uploader(mock_notion_client):
    """Mock NotionUploader for unit tests"""
    with patch('src.notion_uploader.Client') as mock_client_class:
        mock_client_class.return_value = mock_notion_client
        
        # Mock the upload_file_to_notion_storage method
        with patch.object(NotionUploader, 'upload_file_to_notion_storage') as mock_upload:
            mock_upload.return_value = 'test-upload-id'
            
            uploader = NotionUploader()
            yield uploader

@pytest.fixture
def real_notion_uploader():
    """Real NotionUploader for integration tests"""
    try:
        uploader = NotionUploader()
        if not uploader.check_database_exists():
            pytest.skip("Notion database not accessible for integration tests")
        return uploader
    except Exception as e:
        pytest.skip(f"Cannot initialize real NotionUploader: {e}")

@pytest.fixture
def mock_claude_tagger():
    """Mock ClaudeTagger for testing"""
    mock_tagger = Mock()
    mock_tagger.process_transcript.return_value = {
        'claude_tags': {
            'primary_themes': 'Test Theme',
            'specific_focus': 'Test Focus',
            'content_types': 'Voice Note',
            'emotional_tones': 'Neutral',
            'key_topics': 'Testing'
        },
        'summary': 'This is a test voice memo for testing purposes.',
        'deletion_analysis': {
            'should_delete': False,
            'confidence': 'low',
            'reason': 'Contains valuable test content'
        },
        'formatted_transcript': 'This is a formatted test transcript.'
    }
    return mock_tagger

@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
        # Write some dummy data
        temp_file.write(b'fake audio data for testing' * 1000)
        temp_file.flush()
        
        yield Path(temp_file.name)
        
        # Cleanup
        try:
            os.unlink(temp_file.name)
        except FileNotFoundError:
            pass

@pytest.fixture
def test_transcript_data():
    """Sample transcript data for testing"""
    return {
        'transcript': 'This is a test transcript of a voice memo recording.',
        'original_transcript': 'This is a test transcript of a voice memo recording.',
        'claude_tags': {
            'primary_themes': 'Testing, Voice Processing',
            'specific_focus': 'Audio File Upload Testing',
            'content_types': 'Voice Note, Technical Test',
            'emotional_tones': 'Neutral, Professional',
            'key_topics': 'File Upload, Notion Integration, Testing'
        },
        'summary': 'A test voice memo used for validating the upload functionality.',
        'deletion_analysis': {
            'should_delete': False,
            'confidence': 'low',
            'reason': 'Test content with valuable validation data'
        }
    }

@pytest.fixture(scope="session")
def performance_metrics():
    """Track performance metrics across tests"""
    metrics = {
        'upload_times': [],
        'file_sizes': [],
        'success_rates': {},
        'timeouts': [],
        'retries': []
    }
    return metrics

class TimeoutSimulator:
    """Simulate various timeout scenarios"""
    
    def __init__(self):
        self.timeout_count = 0
        self.max_timeouts = 2
    
    def should_timeout(self) -> bool:
        """Determine if this call should timeout"""
        if self.timeout_count < self.max_timeouts:
            self.timeout_count += 1
            return True
        return False
    
    def reset(self):
        """Reset timeout counter"""
        self.timeout_count = 0

@pytest.fixture
def timeout_simulator():
    """Provide timeout simulation for tests"""
    return TimeoutSimulator()

# Helper functions for test data
def create_mock_page_response(page_id: str = "test-page-id", 
                            filename: str = "test.m4a",
                            has_file: bool = True) -> Dict[str, Any]:
    """Create a mock Notion page response"""
    response = {
        'id': page_id,
        'properties': {
            'Title': {
                'title': [{'plain_text': 'Test Voice Memo'}]
            }
        }
    }
    
    if has_file:
        response['properties']['Audio File'] = {
            'files': [
                {
                    'name': filename,
                    'file': {'url': 'https://notion.so/test-file-url'}
                }
            ]
        }
    else:
        response['properties']['Audio File'] = {'files': []}
    
    return response

# Test configuration
TEST_CONFIG = {
    'timeout_test_duration': 30,  # seconds
    'max_test_file_size_mb': 50,  # MB
    'performance_test_iterations': 3,
    'concurrent_upload_limit': 5,
}

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test requiring real API"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance test" 
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark integration tests
        if 'integration' in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark performance tests  
        if 'performance' in item.nodeid:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # Mark file upload tests
        if 'upload' in item.name.lower():
            item.add_marker(pytest.mark.file_upload)