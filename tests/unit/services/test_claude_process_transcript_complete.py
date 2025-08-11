"""
Unit tests for ClaudeService.process_transcript_complete function

These tests focus specifically on the comprehensive transcript processing method
that handles intelligent model selection, streaming, and response parsing.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the service we're testing
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from claude_service import ClaudeService


class TestClaudeProcessTranscriptComplete:
    """Test suite for ClaudeService.process_transcript_complete method"""
    
    @pytest.fixture
    def claude_service(self):
        """Create a ClaudeService instance for testing"""
        with patch('claude_service.CLAUDE_API_KEY', 'test-api-key'):
            return ClaudeService()
    
    @pytest.fixture
    def large_transcript_fixture(self):
        """Load large transcript fixture data"""
        fixture_path = Path(__file__).parent.parent.parent / 'fixtures' / 'transcripts' / 'large_transcript_fixture.txt'
        if fixture_path.exists():
            with open(fixture_path, 'r') as f:
                return f.read().strip()
        else:
            # Fallback for when fixture file is created but not populated yet
            return "PLACEHOLDER_LARGE_TRANSCRIPT - Replace this with actual large transcript data"
    
    @pytest.fixture  
    def normal_transcript_fixture(self):
        """Load normal transcript fixture data"""
        fixture_path = Path(__file__).parent.parent.parent / 'fixtures' / 'transcripts' / 'normal_transcript_fixture.txt'
        if fixture_path.exists():
            with open(fixture_path, 'r') as f:
                return f.read().strip()
        else:
            # Fallback for when fixture file is created but not populated yet
            return "PLACEHOLDER_NORMAL_TRANSCRIPT - Replace this with actual normal transcript data"
    
    @pytest.fixture
    def empty_transcript_fixture(self):
        """Load empty transcript fixture data"""
        fixture_path = Path(__file__).parent.parent.parent / 'fixtures' / 'transcripts' / 'empty_transcript_fixture.txt'
        if fixture_path.exists():
            with open(fixture_path, 'r') as f:
                return f.read().strip()
        else:
            # Fallback - empty transcript should actually be empty or nearly empty
            return ""
    
    @pytest.fixture
    def mock_claude_response(self):
        """Mock Claude API response in expected format"""
        return {
            'content': [{
                'text': """TITLE: Test Voice Memo

PROCESSED_CONTENT:
This is a test processed transcript with improved formatting and readability.

SUMMARY: This is a test voice memo for unit testing purposes.

TAGS: Test, Unit Testing, Voice Memo, Claude Processing

KEYWORDS: test, voice memo, Claude

DELETION_FLAG: false
DELETION_CONFIDENCE: high  
DELETION_REASON: Personal reflection content should be kept"""
            }]
        }
    
    @pytest.fixture
    def mock_audio_classification(self):
        """Mock audio classification data"""
        return {
            'primary_class': 'Speech',
            'confidence': 0.95,
            'top_yamnet_predictions': [
                ('Speech', 0.95),
                ('Narration', 0.85),
                ('Conversation', 0.75)
            ]
        }

    def test_small_transcript_uses_haiku_model(self, claude_service, normal_transcript_fixture):
        """Test that small transcripts use Claude 3.5 Haiku model without streaming"""
        # Create a small transcript (under 7500 estimated tokens = 30,000 characters)
        small_transcript = normal_transcript_fixture[:20000] if len(normal_transcript_fixture) > 20000 else normal_transcript_fixture
        
        with patch.object(claude_service.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(content=[Mock(text="TITLE: Test\nPROCESSED_CONTENT:\nTest content\nSUMMARY: Test\nTAGS: Test\nKEYWORDS: test\nDELETION_FLAG: false\nDELETION_CONFIDENCE: high\nDELETION_REASON: Test")])
            
            result = claude_service.process_transcript_complete(
                transcript=small_transcript,
                filename="test.m4a"
            )
            
            # Verify Haiku model was used
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['model'] == "claude-3-5-haiku-20241022"
            assert call_args[1]['max_tokens'] == 8192
            
            # Verify result structure
            assert 'title' in result
            assert 'formatted_transcript' in result
            assert 'summary' in result
            assert 'claude_tags' in result
            assert 'deletion_analysis' in result

    def test_large_transcript_uses_sonnet_with_streaming(self, claude_service, large_transcript_fixture):
        """Test that large transcripts use Claude 3.5 Sonnet with streaming"""
        # Ensure we have a large transcript (over 7500 estimated tokens = 30,000 characters)
        large_transcript = large_transcript_fixture
        if len(large_transcript) < 30000:
            # Pad the transcript to make it large enough for testing
            large_transcript = large_transcript + " " + ("Additional content for testing. " * 1000)
        
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        mock_stream.__exit__.return_value = None
        mock_stream.text_stream = iter([
            "TITLE: Large Test\n",
            "PROCESSED_CONTENT:\n",
            "This is a large processed transcript.\n",
            "SUMMARY: Large test summary\n",
            "TAGS: Large, Test\n",
            "KEYWORDS: large, test\n",
            "DELETION_FLAG: false\n",
            "DELETION_CONFIDENCE: high\n",
            "DELETION_REASON: Test content"
        ])
        
        with patch.object(claude_service.client.messages, 'stream', return_value=mock_stream):
            result = claude_service.process_transcript_complete(
                transcript=large_transcript,
                filename="large_test.m4a"
            )
            
            # Verify streaming was used
            claude_service.client.messages.stream.assert_called_once()
            call_args = claude_service.client.messages.stream.call_args
            assert call_args[1]['model'] == "claude-3-5-sonnet-20241022"
            assert call_args[1]['max_tokens'] > 8192  # Should be higher for large transcripts
            
            # Verify result structure
            assert result['title'] == "Large Test"
            assert 'formatted_transcript' in result
            assert result['summary'] == "Large test summary"

    def test_empty_transcript_handling(self, claude_service, empty_transcript_fixture):
        """Test handling of empty or very short transcripts"""
        with patch.object(claude_service.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(content=[Mock(text="TITLE: Empty\nPROCESSED_CONTENT:\nNo content\nSUMMARY: Empty\nTAGS: Empty\nKEYWORDS: \nDELETION_FLAG: true\nDELETION_CONFIDENCE: high\nDELETION_REASON: Empty transcript")])
            
            result = claude_service.process_transcript_complete(
                transcript=empty_transcript_fixture,
                filename="empty_test.m4a"
            )
            
            # Verify it still processes but uses Haiku model
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['model'] == "claude-3-5-haiku-20241022"
            
            # Verify result structure is maintained
            assert 'title' in result
            assert 'formatted_transcript' in result
            assert 'deletion_analysis' in result

    def test_audio_classification_integration(self, claude_service, normal_transcript_fixture, mock_audio_classification):
        """Test that audio classification data is properly integrated into the prompt"""
        with patch.object(claude_service.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(content=[Mock(text="TITLE: Speech Test\nPROCESSED_CONTENT:\nSpeech content\nSUMMARY: Speech test\nTAGS: Speech\nKEYWORDS: speech\nDELETION_FLAG: false\nDELETION_CONFIDENCE: high\nDELETION_REASON: Speech content")])
            
            result = claude_service.process_transcript_complete(
                transcript=normal_transcript_fixture,
                filename="speech_test.m4a",
                audio_type="Speech",
                audio_classification=mock_audio_classification
            )
            
            # Verify the prompt includes audio classification data
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            prompt_content = call_args[1]['messages'][0]['content']
            
            # Check that audio classification info is in the prompt
            assert "Speech" in prompt_content
            assert "0.950" in prompt_content  # Confidence formatted to 3 decimal places
            assert "Speech, Narration, Conversation" in prompt_content  # Top predictions

    def test_error_handling_api_failure(self, claude_service, normal_transcript_fixture):
        """Test error handling when Claude API fails"""
        with patch.object(claude_service.client.messages, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = claude_service.process_transcript_complete(
                transcript=normal_transcript_fixture,
                filename="error_test.m4a"
            )
            
            # Verify it returns a fallback result
            assert result['title'] == "error_test.m4a"
            assert result['formatted_transcript'] == normal_transcript_fixture
            assert result['summary'] == ""
            assert result['deletion_analysis']['should_delete'] == False
            assert result['deletion_analysis']['confidence'] == 'low'
            assert result['deletion_analysis']['reason'] == 'Analysis error'

    def test_response_parsing_comprehensive(self, claude_service, normal_transcript_fixture):
        """Test comprehensive response parsing with all expected fields"""
        mock_response_text = """TITLE: Comprehensive Test Voice Memo

PROCESSED_CONTENT:
This is a comprehensive test of the transcript processing system.
It includes multiple paragraphs and proper formatting.

The system should handle this content correctly.

SUMMARY: A comprehensive test of transcript processing with multiple elements and proper formatting validation.

TAGS: Comprehensive Testing, Voice Processing, Multi-paragraph, System Validation, Transcript Analysis

KEYWORDS: comprehensive, test, transcript, processing, validation

DELETION_FLAG: false
DELETION_CONFIDENCE: high
DELETION_REASON: This is valuable personal reflection content that should be preserved"""
        
        with patch.object(claude_service.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(content=[Mock(text=mock_response_text)])
            
            result = claude_service.process_transcript_complete(
                transcript=normal_transcript_fixture,
                filename="comprehensive_test.m4a"
            )
            
            # Verify all fields are parsed correctly
            assert result['title'] == "Comprehensive Test Voice Memo"
            assert "comprehensive test of the transcript processing" in result['formatted_transcript']
            assert "multiple paragraphs" in result['formatted_transcript']
            assert result['summary'] == "A comprehensive test of transcript processing with multiple elements and proper formatting validation."
            assert result['claude_tags']['tags'] == "Comprehensive Testing, Voice Processing, Multi-paragraph, System Validation, Transcript Analysis"
            assert result['claude_tags']['keywords'] == "comprehensive, test, transcript, processing, validation"
            assert result['deletion_analysis']['should_delete'] == False
            assert result['deletion_analysis']['confidence'] == 'high'
            assert "valuable personal reflection" in result['deletion_analysis']['reason']

    def test_token_estimation_logic(self, claude_service):
        """Test the token estimation logic for model selection"""
        # Test small transcript (< 7500 tokens = < 30,000 chars)
        small_transcript = "Short transcript for testing." * 100  # ~3,000 chars
        
        # Test large transcript (>= 7500 tokens = >= 30,000 chars)  
        large_transcript = "Large transcript for testing model selection. " * 1000  # ~47,000 chars
        
        with patch.object(claude_service.client.messages, 'create') as mock_create_small, \
             patch.object(claude_service.client.messages, 'stream') as mock_stream_large:
            
            # Setup mocks
            mock_create_small.return_value = Mock(content=[Mock(text="TITLE: Small\nPROCESSED_CONTENT:\nSmall\nSUMMARY: Small\nTAGS: Small\nKEYWORDS: small\nDELETION_FLAG: false\nDELETION_CONFIDENCE: high\nDELETION_REASON: Small test")])
            
            mock_stream = MagicMock()
            mock_stream.__enter__.return_value = mock_stream
            mock_stream.__exit__.return_value = None
            mock_stream.text_stream = iter(["TITLE: Large\nPROCESSED_CONTENT:\nLarge\nSUMMARY: Large\nTAGS: Large\nKEYWORDS: large\nDELETION_FLAG: false\nDELETION_CONFIDENCE: high\nDELETION_REASON: Large test"])
            mock_stream_large.return_value = mock_stream
            
            # Test small transcript uses Haiku
            result_small = claude_service.process_transcript_complete(small_transcript, "small.m4a")
            mock_create_small.assert_called_once()
            assert mock_create_small.call_args[1]['model'] == "claude-3-5-haiku-20241022"
            
            # Test large transcript uses Sonnet with streaming
            result_large = claude_service.process_transcript_complete(large_transcript, "large.m4a")
            mock_stream_large.assert_called_once()
            assert mock_stream_large.call_args[1]['model'] == "claude-3-5-sonnet-20241022"
            assert mock_stream_large.call_args[1]['max_tokens'] >= 16384  # Should be 16384 or higher for large transcripts