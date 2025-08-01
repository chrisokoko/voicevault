"""
Unit tests for async upload functionality - Fix for Issue #1
Tests the new async upload methods with both small and large files
"""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, AsyncMock, patch, call
from pathlib import Path
from typing import Dict, Any

from src.notion_service import NotionService
from .conftest import TestFileManager


class TestAsyncUpload:
    """Test the new async upload functionality"""
    
    @pytest.fixture
    def mock_notion_service(self):
        """Create NotionService with mocked clients"""
        with patch('src.notion_service.Client') as mock_sync_client, \
             patch('src.notion_service.AsyncClient') as mock_async_client:
            
            service = NotionService()
            service.client = Mock()
            service.async_client = AsyncMock()
            
            # Mock database connection
            service.check_database_exists = Mock(return_value=True)
            
            return service
    
    @pytest.fixture
    def test_file_manager(self):
        """Get test file manager"""
        return TestFileManager()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_small_file_async_upload_success(self, mock_notion_service, test_file_manager):
        """Test successful async upload with small file"""
        
        # Get small test file
        files = test_file_manager.get_categorized_files()
        small_file = files['small'][0]  # 30s test file
        
        # Mock the async upload pipeline
        mock_notion_service._validate_file_for_upload = Mock(return_value={
            "valid": True,
            "filename": small_file.name
        })
        mock_notion_service._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_service.upload_file_to_notion_storage = Mock(return_value="upload-small-123")
        
        # Mock successful verification
        mock_notion_service._verify_upload_completion_async = AsyncMock(return_value={
            "success": True,
            "status": "verified",
            "file_url": "https://notion.so/small-file-url"
        })
        
        # Test the async upload
        result = await mock_notion_service.add_audio_file_to_page_async("page-123", str(small_file))
        
        # Verify success
        assert result["success"] == True
        assert result["status"] == "upload_complete"
        assert "file_url" in result
        
        # Verify methods were called correctly
        mock_notion_service.upload_file_to_notion_storage.assert_called_once_with(str(small_file))
        mock_notion_service._verify_upload_completion_async.assert_called_once_with(
            "page-123", small_file.name, "upload-small-123", max_wait_seconds=120
        )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_large_file_async_upload_success(self, mock_notion_service, test_file_manager):
        """Test successful async upload with large file"""
        
        # Get large test file
        files = test_file_manager.get_categorized_files()
        large_file = files['large'][0]  # 40-min Odyssey file
        
        # Mock the async upload pipeline for large file
        mock_notion_service._validate_file_for_upload = Mock(return_value={
            "valid": True,
            "filename": large_file.name
        })
        mock_notion_service._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_service.upload_file_to_notion_storage = Mock(return_value="upload-large-456")
        
        # Mock successful verification (should take longer for large files)
        mock_notion_service._verify_upload_completion_async = AsyncMock(return_value={
            "success": True,
            "status": "verified", 
            "file_url": "https://notion.so/large-file-url"
        })
        
        # Test the async upload
        result = await mock_notion_service.add_audio_file_to_page_async("page-456", str(large_file))
        
        # Verify success
        assert result["success"] == True
        assert result["status"] == "upload_complete"
        assert "file_url" in result
        
        # Verify upload was attempted
        mock_notion_service.upload_file_to_notion_storage.assert_called_once_with(str(large_file))
        mock_notion_service._verify_upload_completion_async.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_upload_verification_failure(self, mock_notion_service, test_file_manager):
        """Test async upload with verification failure"""
        
        files = test_file_manager.get_categorized_files()
        test_file = files['small'][0]
        
        # Mock upload success but verification failure
        mock_notion_service._validate_file_for_upload = Mock(return_value={
            "valid": True,
            "filename": test_file.name
        })
        mock_notion_service._is_file_already_uploaded = Mock(return_value=False)
        mock_notion_service.upload_file_to_notion_storage = Mock(return_value="upload-123")
        
        # Mock verification failure
        mock_notion_service._verify_upload_completion_async = AsyncMock(return_value={
            "success": False,
            "status": "timeout",
            "reason": "Upload verification timed out after 120 seconds"
        })
        
        # Test the async upload
        result = await mock_notion_service.add_audio_file_to_page_async("page-123", str(test_file))
        
        # Verify failure is properly reported
        assert result["success"] == False
        assert result["error_type"] == "verification_failed"
        assert "timeout" in result["reason"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_upload_already_exists(self, mock_notion_service, test_file_manager):
        """Test async upload when file already exists"""
        
        files = test_file_manager.get_categorized_files()
        test_file = files['small'][0]
        
        # Mock file validation and existing file check
        mock_notion_service._validate_file_for_upload = Mock(return_value={
            "valid": True,
            "filename": test_file.name
        })
        mock_notion_service._is_file_already_uploaded = Mock(return_value=True)
        
        # Test the async upload
        result = await mock_notion_service.add_audio_file_to_page_async("page-123", str(test_file))
        
        # Verify early return for existing file
        assert result["success"] == True
        assert result["status"] == "already_uploaded"
        
        # Verify upload was not attempted
        mock_notion_service.upload_file_to_notion_storage.assert_not_called()


class TestAsyncUploadVerification:
    """Test the async verification methods specifically"""
    
    @pytest.fixture
    def mock_notion_service(self):
        """Create NotionService with mocked clients"""
        with patch('src.notion_service.Client') as mock_sync_client, \
             patch('src.notion_service.AsyncClient') as mock_async_client:
            
            service = NotionService()
            service.client = Mock()
            service.async_client = AsyncMock()
            return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_for_upload_status_success(self, mock_notion_service):
        """Test successful upload status polling"""
        
        # Mock upload status progression: pending -> uploaded
        mock_notion_service._check_upload_status_async = AsyncMock(side_effect=[
            {"status": "pending"},  # First check
            {"status": "pending"},  # Second check
            {"status": "uploaded"}  # Third check - success
        ])
        
        # Test the status waiting
        result = await mock_notion_service._wait_for_upload_status("upload-123", max_wait_seconds=10)
        
        assert result["success"] == True
        assert result["status"] == "uploaded"
        assert mock_notion_service._check_upload_status_async.call_count == 3
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_for_upload_status_failure(self, mock_notion_service):
        """Test upload status polling with failure"""
        
        # Mock upload failure
        mock_notion_service._check_upload_status_async = AsyncMock(return_value={
            "status": "failed",
            "error_message": "Upload processing failed"
        })
        
        # Test the status waiting
        result = await mock_notion_service._wait_for_upload_status("upload-123", max_wait_seconds=10)
        
        assert result["success"] == False
        assert result["status"] == "failed"
        assert "Upload processing failed" in result["reason"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_for_upload_status_timeout(self, mock_notion_service):
        """Test upload status polling timeout"""
        
        # Mock upload that never completes
        mock_notion_service._check_upload_status_async = AsyncMock(return_value={
            "status": "pending"
        })
        
        # Test with very short timeout
        result = await mock_notion_service._wait_for_upload_status("upload-123", max_wait_seconds=0.1)
        
        assert result["success"] == False
        assert result["status"] == "timeout"
        assert "timed out" in result["reason"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_file_in_page_properties_success(self, mock_notion_service):
        """Test successful file verification in page properties"""
        
        # Mock page response with valid file
        mock_page_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': 'test.m4a',
                            'file': {'url': 'https://notion.so/file-url'}
                        }
                    ]
                }
            }
        }
        mock_notion_service.async_client.pages.retrieve.return_value = mock_page_response
        
        # Test file verification
        result = await mock_notion_service._verify_file_in_page_properties("page-123", "test.m4a")
        
        assert result["success"] == True
        assert result["status"] == "verified"
        assert result["file_url"] == "https://notion.so/file-url"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_file_in_page_properties_no_url(self, mock_notion_service):
        """Test file verification when file exists but has no URL"""
        
        # Mock page response with file but no URL
        mock_page_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': 'test.m4a',
                            'file': {}  # No URL - incomplete upload
                        }
                    ]
                }
            }
        }
        mock_notion_service.async_client.pages.retrieve.return_value = mock_page_response
        
        # Test file verification
        result = await mock_notion_service._verify_file_in_page_properties("page-123", "test.m4a")
        
        assert result["success"] == False
        assert result["status"] == "no_url"
        assert "no accessible URL" in result["reason"]


class TestBackwardsCompatibility:
    """Test that sync wrapper maintains backwards compatibility"""
    
    @pytest.mark.unit
    def test_sync_wrapper_returns_boolean(self):
        """Test that sync wrapper returns boolean for backwards compatibility"""
        
        with patch('src.notion_service.Client') as mock_sync_client, \
             patch('src.notion_service.AsyncClient') as mock_async_client:
            
            service = NotionService()
            
            # Mock validation failure (should return False quickly)
            service._validate_file_for_upload = Mock(return_value={
                "valid": False,
                "reason": "file_not_found"
            })
            
            # Test sync wrapper
            result = service.add_audio_file_to_page("page-123", "/nonexistent/file.m4a")
            
            # Should return boolean, not dict
            assert isinstance(result, bool)
            assert result == False


# Integration with existing test markers
pytestmark = [pytest.mark.notion, pytest.mark.upload]