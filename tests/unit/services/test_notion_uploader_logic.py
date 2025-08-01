"""
Unit tests for NotionUploader - Testing ACTUAL LOGIC (no API calls, no mocks)

These tests verify the pure logic functions work correctly.
Integration tests in test_integration.py verify the real API functionality.
"""
import pytest
import tempfile
import os
from pathlib import Path
from notion_client.errors import APIResponseError, RequestTimeoutError

from src.notion_uploader import NotionUploader


class TestFileValidationLogic:
    """Test file validation logic - no API calls needed"""
    
    def test_validate_valid_file(self, temp_audio_file):
        """Test validation logic with valid file"""
        uploader = NotionUploader()
        
        result = uploader._validate_file_for_upload(str(temp_audio_file))
        
        assert result["valid"] is True
        assert result["filename"] == temp_audio_file.name
        assert result["file_size_mb"] > 0
        assert "use_multipart" in result
    
    def test_validate_nonexistent_file(self):
        """Test validation logic with nonexistent file"""
        uploader = NotionUploader()
        
        result = uploader._validate_file_for_upload("/path/that/does/not/exist.m4a")
        
        assert result["valid"] is False
        assert result["reason"] == "file_not_found"
    
    def test_validate_empty_file(self):
        """Test validation logic with empty file"""
        uploader = NotionUploader()
        
        # Create empty file
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as f:
            empty_file_path = f.name
        
        try:
            result = uploader._validate_file_for_upload(empty_file_path)
            
            assert result["valid"] is False
            assert result["reason"] == "empty_file"
        finally:
            os.unlink(empty_file_path)
    
    def test_validate_wrong_extension(self):
        """Test validation logic with wrong file extension"""
        uploader = NotionUploader()
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not audio data")
            txt_file_path = f.name
        
        try:
            result = uploader._validate_file_for_upload(txt_file_path)
            
            assert result["valid"] is False
            assert result["reason"] == "invalid_format"
        finally:
            os.unlink(txt_file_path)
    
    def test_validate_large_file_size(self):
        """Test validation detects when to use multipart upload"""
        uploader = NotionUploader()
        
        # Create file info that simulates a 25MB file
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as f:
            # Write enough data to simulate large file
            f.write(b'x' * (25 * 1024 * 1024))  # 25MB
            large_file_path = f.name
        
        try:
            result = uploader._validate_file_for_upload(large_file_path)
            
            assert result["valid"] is True
            assert result["use_multipart"] is True
            assert result["file_size_mb"] > 20
        finally:
            os.unlink(large_file_path)


class TestUploadStrategyLogic:
    """Test upload strategy decision logic"""
    
    def test_multipart_threshold_logic(self):
        """Test logic that decides when to use multipart upload"""
        uploader = NotionUploader()
        
        # Small files should use single-part
        assert uploader._should_use_multipart_upload(10 * 1024 * 1024) is False  # 10MB
        assert uploader._should_use_multipart_upload(19 * 1024 * 1024) is False  # 19MB
        
        # Large files should use multipart  
        assert uploader._should_use_multipart_upload(21 * 1024 * 1024) is True   # 21MB
        assert uploader._should_use_multipart_upload(50 * 1024 * 1024) is True   # 50MB


class TestRetryLogic:
    """Test retry decision logic - the core of Issue #1 fix"""
    
    def test_should_retry_timeout_errors(self):
        """Test that timeout errors should always be retried"""
        uploader = NotionUploader()
        
        assert uploader._should_retry_upload("timeout", True) is True
        assert uploader._should_retry_upload("request_timeout", False) is True
        assert uploader._should_retry_upload("connection_timeout", False) is True
    
    def test_should_retry_upload_failures(self):
        """Test that upload failures should be retried"""
        uploader = NotionUploader()
        
        assert uploader._should_retry_upload("upload_failed", False) is True
        assert uploader._should_retry_upload("verification_failed", False) is True
        assert uploader._should_retry_upload("storage_error", False) is True
    
    def test_should_not_retry_auth_errors(self):
        """Test that auth/permission errors should not be retried"""
        uploader = NotionUploader()
        
        assert uploader._should_retry_upload("unauthorized", False) is False
        assert uploader._should_retry_upload("forbidden", False) is False
        assert uploader._should_retry_upload("not_found", False) is False
    
    def test_should_retry_unknown_errors(self):
        """Test that unknown errors default to retry (safer)"""
        uploader = NotionUploader()
        
        assert uploader._should_retry_upload("weird_unknown_error", False) is True
        assert uploader._should_retry_upload("something_unexpected", False) is True
    
    def test_calculate_retry_delay_for_timeouts(self):
        """Test exponential backoff for timeout errors"""
        uploader = NotionUploader()
        
        # Timeout delays should grow exponentially
        delay1 = uploader._calculate_retry_delay(1, is_timeout=True)
        delay2 = uploader._calculate_retry_delay(2, is_timeout=True)
        delay3 = uploader._calculate_retry_delay(3, is_timeout=True)
        
        assert delay1 == 10.0  # 5 * 2^1
        assert delay2 == 20.0  # 5 * 2^2
        assert delay3 == 30.0  # 5 * 2^3, capped at 30
        
        # Should not exceed maximum
        delay_large = uploader._calculate_retry_delay(10, is_timeout=True)
        assert delay_large == 30.0
    
    def test_calculate_retry_delay_for_regular_errors(self):
        """Test linear backoff for regular errors"""
        uploader = NotionUploader()
        
        # Regular errors should grow linearly
        delay1 = uploader._calculate_retry_delay(1, is_timeout=False)
        delay2 = uploader._calculate_retry_delay(2, is_timeout=False)
        delay3 = uploader._calculate_retry_delay(3, is_timeout=False)
        
        assert delay1 == 2.0   # 2 * 1
        assert delay2 == 4.0   # 2 * 2
        assert delay3 == 6.0   # 2 * 3
        
        # Should not exceed maximum
        delay_large = uploader._calculate_retry_delay(10, is_timeout=False)
        assert delay_large == 10.0


class TestErrorClassificationLogic:
    """Test error type extraction logic"""
    
    def test_extract_timeout_errors(self):
        """Test identification of timeout errors"""
        uploader = NotionUploader()
        
        timeout_error = RequestTimeoutError("Request timed out")
        assert uploader._extract_error_type_from_exception(timeout_error) == "timeout"
        
        generic_timeout = Exception("Connection timeout occurred")
        assert uploader._extract_error_type_from_exception(generic_timeout) == "timeout"
    
    def test_extract_file_size_errors(self):
        """Test identification of file size errors"""
        uploader = NotionUploader()
        
        size_error = Exception("413 Payload too large")
        assert uploader._extract_error_type_from_exception(size_error) == "file_too_large"
        
        payload_error = Exception("payload too large for upload")
        assert uploader._extract_error_type_from_exception(payload_error) == "file_too_large"
    
    def test_extract_auth_errors(self):
        """Test identification of authentication errors"""
        uploader = NotionUploader()
        
        auth_error = Exception("401 Unauthorized access")
        assert uploader._extract_error_type_from_exception(auth_error) == "unauthorized"
        
        forbidden_error = Exception("403 Forbidden")
        assert uploader._extract_error_type_from_exception(forbidden_error) == "forbidden"
    
    def test_extract_rate_limit_errors(self):
        """Test identification of rate limit errors"""
        uploader = NotionUploader()
        
        rate_error = Exception("429 Too Many Requests")
        assert uploader._extract_error_type_from_exception(rate_error) == "rate_limit"
        
        limit_error = Exception("Rate limit exceeded")
        assert uploader._extract_error_type_from_exception(limit_error) == "rate_limit"
    
    def test_extract_unknown_errors(self):
        """Test classification of unknown errors"""
        uploader = NotionUploader()
        
        weird_error = Exception("Something completely unexpected happened")
        assert uploader._extract_error_type_from_exception(weird_error) == "unknown_error"


class TestResponseParsingLogic:
    """Test Notion API response parsing logic"""
    
    def test_parse_file_info_found_with_url(self):
        """Test parsing when file is found with URL"""
        uploader = NotionUploader()
        
        mock_response = {
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
        
        result = uploader._parse_file_info_from_response(mock_response, 'test.m4a')
        
        assert result["found"] is True
        assert result["has_url"] is True
        assert result["upload_complete"] is True
        assert result["file_url"] == 'https://notion.so/file-url'
    
    def test_parse_file_info_found_without_url(self):
        """Test parsing when file is found but has no URL (incomplete upload)"""
        uploader = NotionUploader()
        
        mock_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': 'test.m4a',
                            'file': {}  # No URL
                        }
                    ]
                }
            }
        }
        
        result = uploader._parse_file_info_from_response(mock_response, 'test.m4a')
        
        assert result["found"] is True
        assert result["has_url"] is False
        assert result["upload_complete"] is False
    
    def test_parse_file_info_not_found(self):
        """Test parsing when file is not found in response"""
        uploader = NotionUploader()
        
        mock_response = {
            'properties': {
                'Audio File': {
                    'files': []
                }
            }
        }
        
        result = uploader._parse_file_info_from_response(mock_response, 'test.m4a')
        
        assert result["found"] is False
        assert result["has_url"] is False
        assert result["upload_complete"] is False
    
    def test_parse_file_info_external_url(self):
        """Test parsing when file has external URL"""
        uploader = NotionUploader()
        
        mock_response = {
            'properties': {
                'Audio File': {
                    'files': [
                        {
                            'name': 'test.m4a',
                            'external': {'url': 'https://external.com/file-url'}
                        }
                    ]
                }
            }
        }
        
        result = uploader._parse_file_info_from_response(mock_response, 'test.m4a')
        
        assert result["found"] is True
        assert result["has_url"] is True
        assert result["upload_complete"] is True
        assert result["external_url"] == 'https://external.com/file-url'


class TestExistingLogicFunctions:
    """Test existing logic functions that were already in the codebase"""
    
    def test_format_duration_logic(self):
        """Test duration formatting logic"""
        uploader = NotionUploader()
        
        assert uploader.format_duration(0) == "0s"
        assert uploader.format_duration(30) == "30s"
        assert uploader.format_duration(65) == "1m 5s"
        assert uploader.format_duration(3661) == "61m 1s"
    
    def test_format_file_size_logic(self):
        """Test file size formatting logic"""
        uploader = NotionUploader()
        
        assert uploader.format_file_size(512) == "512 B"
        assert uploader.format_file_size(1024) == "1.0 KB"
        assert uploader.format_file_size(1536) == "1.5 KB"
        assert uploader.format_file_size(1048576) == "1.0 MB"
        assert uploader.format_file_size(2621440) == "2.5 MB"
    
    def test_title_case_logic(self):
        """Test title case formatting logic"""
        uploader = NotionUploader()
        
        assert uploader._title_case_properly("hello world") == "Hello World"
        assert uploader._title_case_properly("the cat in the hat") == "The Cat in the Hat"
        assert uploader._title_case_properly("a tale of two cities") == "A Tale of Two Cities"
        assert uploader._title_case_properly("war and peace") == "War and Peace"


class TestIntegratedLogicWorkflow:
    """Test how the logic functions work together"""
    
    def test_complete_validation_and_strategy_workflow(self):
        """Test the complete logic workflow for file processing"""
        uploader = NotionUploader()
        
        # Create a test file
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as f:
            f.write(b'x' * (15 * 1024 * 1024))  # 15MB file
            test_file = f.name
        
        try:
            # Test validation
            validation = uploader._validate_file_for_upload(test_file)
            assert validation["valid"] is True
            
            # Test multipart decision  
            should_multipart = uploader._should_use_multipart_upload(15 * 1024 * 1024)
            assert should_multipart is False  # 15MB < 20MB threshold
            
            # Test retry logic for a timeout
            should_retry = uploader._should_retry_upload("timeout", True)
            assert should_retry is True
            
            # Test delay calculation
            delay = uploader._calculate_retry_delay(1, True)
            assert delay == 10.0  # 5 * 2^1
            
        finally:
            os.unlink(test_file)
    
    def test_error_handling_workflow(self):
        """Test complete error handling logic workflow"""
        uploader = NotionUploader()
        
        # Simulate various error scenarios
        timeout_exception = RequestTimeoutError("Timeout")
        auth_exception = Exception("401 Unauthorized")
        unknown_exception = Exception("Something weird happened")
        
        # Test error classification
        timeout_type = uploader._extract_error_type_from_exception(timeout_exception)
        auth_type = uploader._extract_error_type_from_exception(auth_exception)
        unknown_type = uploader._extract_error_type_from_exception(unknown_exception)
        
        # Test retry decisions
        assert uploader._should_retry_upload(timeout_type, True) is True
        assert uploader._should_retry_upload(auth_type, False) is False
        assert uploader._should_retry_upload(unknown_type, False) is True  # Default to retry
        
        # Test delay calculations
        timeout_delay = uploader._calculate_retry_delay(2, True)
        regular_delay = uploader._calculate_retry_delay(2, False)
        
        assert timeout_delay == 20.0  # Exponential for timeouts
        assert regular_delay == 4.0   # Linear for regular errors


# Performance tests for logic functions
class TestLogicPerformance:
    """Test that logic functions are fast (they should be since they don't hit APIs)"""
    
    def test_validation_is_fast(self, temp_audio_file):
        """Test that file validation is fast"""
        uploader = NotionUploader()
        
        import time
        start = time.time()
        
        # Run validation 100 times
        for _ in range(100):
            uploader._validate_file_for_upload(str(temp_audio_file))
        
        elapsed = time.time() - start
        
        # Should be very fast since no API calls
        assert elapsed < 1.0, f"Validation took {elapsed:.2f}s for 100 calls - should be much faster"
    
    def test_retry_logic_is_fast(self):
        """Test that retry logic is fast"""
        uploader = NotionUploader()
        
        import time
        start = time.time()
        
        # Run retry logic 1000 times
        for i in range(1000):
            uploader._should_retry_upload("timeout", True)
            uploader._calculate_retry_delay(i % 10, i % 2 == 0)
        
        elapsed = time.time() - start
        
        # Should be very fast since pure logic
        assert elapsed < 0.5, f"Retry logic took {elapsed:.2f}s for 1000 calls - should be much faster"