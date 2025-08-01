"""
Unit tests for NotionUploader - Focus on the upload completion verification fix for Issue #1
"""
import pytest
import time
from unittest.mock import Mock, patch, call
from pathlib import Path
import os
from notion_client.errors import APIResponseError, RequestTimeoutError

from src.notion_uploader import NotionUploader
from .conftest import create_mock_page_response, TEST_CONFIG


class TestNotionUploaderInit:
    """Test NotionUploader initialization"""
    
    @pytest.mark.unit
    def test_init_with_valid_config(self, mock_notion_client):
        """Test initialization with valid configuration"""
        with patch('src.notion_uploader.Client') as mock_client_class:
            mock_client_class.return_value = mock_notion_client
            
            uploader = NotionUploader()
            
            assert uploader.client == mock_notion_client
            assert uploader.api_calls == 0
            assert uploader.cache_hits == 0
    
    @pytest.mark.unit  
    def test_init_without_token(self):
        """Test initialization fails without NOTION_TOKEN"""
        with patch('src.notion_uploader.NOTION_TOKEN', None):
            with pytest.raises(ValueError, match="NOTION_TOKEN not found"):
                NotionUploader()


class TestDatabaseConnection:
    """Test database connectivity"""
    
    @pytest.mark.unit
    def test_check_database_exists_success(self, mock_notion_uploader):
        """Test successful database connection check"""
        result = mock_notion_uploader.check_database_exists()
        assert result is True
    
    @pytest.mark.unit
    def test_check_database_exists_failure(self, mock_notion_client):
        """Test database connection failure"""
        mock_notion_client.databases.retrieve.side_effect = APIResponseError(
            "Database not found", None, None
        )
        
        with patch('src.notion_uploader.Client') as mock_client_class:
            mock_client_class.return_value = mock_notion_client
            uploader = NotionUploader()
            
            result = uploader.check_database_exists()
            assert result is False


class TestFileUploadCompletion:
    """Test the new upload completion verification logic - the core fix for Issue #1"""
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_file_already_uploaded_detection_success(self, mock_notion_uploader, temp_audio_file):
        """Test detection of already uploaded files"""
        page_id = "test-page-id"
        filename = temp_audio_file.name
        
        # Mock page response showing file is already uploaded
        mock_response = create_mock_page_response(page_id, filename, has_file=True)
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        result = mock_notion_uploader._is_file_already_uploaded(page_id, filename)
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_file_already_uploaded_detection_missing(self, mock_notion_uploader, temp_audio_file):
        """Test detection when file is not uploaded"""
        page_id = "test-page-id"
        filename = temp_audio_file.name
        
        # Mock page response showing no file
        mock_response = create_mock_page_response(page_id, filename, has_file=False)
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        result = mock_notion_uploader._is_file_already_uploaded(page_id, filename)
        assert result is False
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_upload_verification_success(self, mock_notion_uploader, temp_audio_file):
        """Test successful upload verification"""
        page_id = "test-page-id"
        filename = temp_audio_file.name
        
        # Mock page response showing uploaded file with URL
        mock_response = create_mock_page_response(page_id, filename, has_file=True)
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_upload_verification_failure_no_url(self, mock_notion_uploader, temp_audio_file):
        """Test upload verification failure when file has no URL"""
        page_id = "test-page-id"
        filename = temp_audio_file.name
        
        # Mock page response showing file without URL (incomplete upload)
        mock_response = {
            'id': page_id,
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': filename,
                            'file': {}  # No URL indicates incomplete upload
                        }
                    ]
                }
            }
        }
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        assert result is False


class TestUploadRetryLogic:
    """Test the new retry logic that checks completion instead of using max attempts"""
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_upload_succeeds_first_try(self, mock_notion_uploader, temp_audio_file):
        """Test upload succeeds on first attempt"""
        page_id = "test-page-id"
        
        # Mock successful upload and verification
        mock_notion_uploader._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_uploader._verify_upload_completion = Mock(return_value=True)
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader.add_audio_file_to_properties(page_id, str(temp_audio_file))
        
        assert result is True
        mock_notion_uploader.upload_file_to_notion_storage.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_upload_retries_on_failure_until_success(self, mock_notion_uploader, temp_audio_file):
        """Test upload retries until successful completion"""
        page_id = "test-page-id"
        
        # Mock upload failure then success
        mock_notion_uploader._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_uploader.upload_file_to_notion_storage.side_effect = [
            None,  # First attempt fails
            None,  # Second attempt fails  
            'upload-id-success'  # Third attempt succeeds
        ]
        mock_notion_uploader._verify_upload_completion = Mock(return_value=True)
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader.add_audio_file_to_properties(page_id, str(temp_audio_file))
        
        assert result is True
        assert mock_notion_uploader.upload_file_to_notion_storage.call_count == 3
    
    @pytest.mark.unit
    @pytest.mark.file_upload  
    def test_upload_handles_timeout_and_retries(self, mock_notion_uploader, temp_audio_file):
        """Test upload handles timeouts and retries appropriately"""
        page_id = "test-page-id"
        
        # Mock timeout then success
        mock_notion_uploader._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_uploader.upload_file_to_notion_storage.side_effect = [
            'upload-id'  # Upload succeeds
        ]
        mock_notion_uploader.client.pages.update.side_effect = [
            RequestTimeoutError("Timeout", None, None),  # First update times out
            Mock()  # Second update succeeds
        ]
        mock_notion_uploader._verify_upload_completion.side_effect = [
            False,  # First verification fails (due to timeout)
            True    # Second verification succeeds
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader.add_audio_file_to_properties(page_id, str(temp_audio_file))
        
        assert result is True
        assert mock_notion_uploader.client.pages.update.call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_upload_skips_if_already_uploaded(self, mock_notion_uploader, temp_audio_file):
        """Test upload skips if file is already uploaded"""
        page_id = "test-page-id"
        
        # Mock file already uploaded
        mock_notion_uploader._is_file_already_uploaded = Mock(return_value=True)
        
        result = mock_notion_uploader.add_audio_file_to_properties(page_id, str(temp_audio_file))
        
        assert result is True
        mock_notion_uploader.upload_file_to_notion_storage.assert_not_called()


class TestUploadVerificationMethods:
    """Test the specific verification methods"""
    
    @pytest.mark.unit
    def test_verify_upload_completion_with_file_url(self, mock_notion_uploader):
        """Test verification succeeds when file has file URL"""
        page_id = "test-page-id"
        filename = "test.m4a"
        
        mock_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': filename,
                            'file': {'url': 'https://notion.so/file-url'}
                        }
                    ]
                }
            }
        }
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        
        assert result is True
    
    @pytest.mark.unit
    def test_verify_upload_completion_with_external_url(self, mock_notion_uploader):
        """Test verification succeeds when file has external URL"""
        page_id = "test-page-id"
        filename = "test.m4a"
        
        mock_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': filename,
                            'external': {'url': 'https://external.com/file-url'}
                        }
                    ]
                }
            }
        }
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        
        assert result is True
    
    @pytest.mark.unit
    def test_verify_upload_completion_no_files(self, mock_notion_uploader):
        """Test verification fails when no files in properties"""
        page_id = "test-page-id"
        filename = "test.m4a"
        
        mock_response = {
            'properties': {
                'Audio File': {'files': []}
            }
        }
        mock_notion_uploader.client.pages.retrieve.return_value = mock_response
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        
        assert result is False


class TestErrorHandling:
    """Test error handling in upload process"""
    
    @pytest.mark.unit
    @pytest.mark.file_upload
    def test_handles_non_recoverable_api_error(self, mock_notion_uploader, temp_audio_file):
        """Test handling of non-recoverable API errors"""
        page_id = "test-page-id"
        
        # Mock non-recoverable error
        mock_notion_uploader._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_uploader.upload_file_to_notion_storage.side_effect = APIResponseError(
            "Invalid request", None, None
        )
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader.add_audio_file_to_properties(page_id, str(temp_audio_file))
        
        assert result is False
    
    @pytest.mark.unit
    def test_handles_verification_api_error(self, mock_notion_uploader):
        """Test handling of API errors during verification"""
        page_id = "test-page-id"
        filename = "test.m4a"
        
        mock_notion_uploader.client.pages.retrieve.side_effect = APIResponseError(
            "Page not found", None, None
        )
        
        with patch('time.sleep'):  # Speed up test
            result = mock_notion_uploader._verify_upload_completion(page_id, filename)
        
        assert result is False


class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    @pytest.mark.unit
    def test_get_performance_stats(self, mock_notion_uploader):
        """Test performance statistics tracking"""
        # Simulate some API calls and cache hits
        mock_notion_uploader.api_calls = 10
        mock_notion_uploader.cache_hits = 3
        mock_notion_uploader.cache_misses = 7
        mock_notion_uploader.cache = {'key1': 'value1', 'key2': 'value2'}
        
        stats = mock_notion_uploader.get_performance_stats()
        
        assert stats['api_calls_made'] == 10
        assert stats['cache_hits'] == 3
        assert stats['cache_misses'] == 7
        assert stats['cache_hit_rate_percent'] == 30.0
        assert stats['cached_items'] == 2
    
    @pytest.mark.unit
    def test_rate_limiting(self, mock_notion_uploader):
        """Test rate limiting functionality"""
        # Test that rate limiting adds delays between calls
        start_time = time.time()
        
        mock_notion_uploader._rate_limit()
        mock_notion_uploader._rate_limit()
        
        elapsed = time.time() - start_time
        
        # Should have at least one interval delay
        assert elapsed >= mock_notion_uploader.min_request_interval


class TestCacheSystem:
    """Test the intelligent caching system"""
    
    @pytest.mark.unit
    def test_cache_hit(self, mock_notion_uploader):
        """Test cache hit functionality"""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set cache data
        mock_notion_uploader._set_cache(cache_key, test_data, ttl_seconds=60)
        
        # Retrieve from cache
        cached_data = mock_notion_uploader._get_from_cache(cache_key)
        
        assert cached_data == test_data
        assert mock_notion_uploader.cache_hits == 1
        assert mock_notion_uploader.cache_misses == 0
    
    @pytest.mark.unit
    def test_cache_miss(self, mock_notion_uploader):
        """Test cache miss functionality"""
        cache_key = "nonexistent_key"
        
        # Try to retrieve non-existent key
        cached_data = mock_notion_uploader._get_from_cache(cache_key)
        
        assert cached_data is None
        assert mock_notion_uploader.cache_hits == 0
        assert mock_notion_uploader.cache_misses == 1
    
    @pytest.mark.unit
    def test_cache_expiration(self, mock_notion_uploader):
        """Test cache expiration functionality"""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set cache data with very short TTL
        mock_notion_uploader._set_cache(cache_key, test_data, ttl_seconds=0.1)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Try to retrieve expired data
        cached_data = mock_notion_uploader._get_from_cache(cache_key)
        
        assert cached_data is None
        assert cache_key not in mock_notion_uploader.cache