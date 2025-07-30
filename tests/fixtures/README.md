# Test Fixtures Directory

This directory contains static test data for deterministic testing of the VoiceVault system.

## Testing Approach

- **Unit Tests**: Use mocks (no real API calls)
- **Integration Tests**: Use real APIs with your actual audio files
- **Test Data**: Copy specific files from `audio_files/` to ensure consistent test results

## Recommended Test Files

Based on your existing `audio_files/`, copy these specific files to `tests/fixtures/audio_samples/`:

### Size Categories (with exact file sizes)

**Tiny Files (< 50KB):**
- `5724 NE 60th Ave 101.m4a` (1,990 bytes - ~2KB)
- `The Den.m4a` (1,996 bytes - ~2KB)  
- `I-84 W 5.m4a` (3,162 bytes - ~3KB)
- `5724 NE 60th Ave 107.m4a` (4,828 bytes - ~5KB)

**Small Files (50KB - 1MB):**
- `University of Oregon Portland 21.m4a` (5,484 bytes - ~5KB)
- `Lucky Labrador 3.m4a` (15,799 bytes - ~16KB)
- `Soft Touch Dental 2.m4a` (19,878 bytes - ~20KB)
- `5724 NE 60th Ave 91.m4a` (26,200 bytes - ~26KB)

**Medium Files (1MB - 5MB):**
- `5724 NE 60th Ave 48.m4a` (1,074,155 bytes - ~1MB)
- `5724 NE 60th Ave 80.m4a` (1,584,332 bytes - ~1.5MB)
- `5724 NE 60th Ave 90.m4a` (2,822,914 bytes - ~2.8MB)
- `Dance - triggers & wounds.m4a` (4,267,095 bytes - ~4.3MB)

**Large Files (5MB - 15MB):**
- `NW Quimby St 31.m4a` (5,963,516 bytes - ~6MB)
- `5724 NE 60th Ave 27.m4a` (7,604,838 bytes - ~7.6MB)
- `NW Quimby St 6.m4a` (9,723,116 bytes - ~9.7MB)
- `5724 NE 60th Ave 83.m4a` (11,507,888 bytes - ~11.5MB)

**Extra Large Files (> 15MB):**
- `University of Oregon Portland 54.m4a` (19,240,346 bytes - ~19MB)
- `Personal mission:brand:religion.m4a` (22,447,466 bytes - ~22MB)  
- `Ours: Audience building & storytelling.m4a` (42,646,076 bytes - ~43MB)
- `New Recording 11.m4a` (158,394,989 bytes - ~158MB)

### Edge Case Files
- `empty_file.m4a` - Create a 0-byte file for error handling tests
- `corrupted.m4a` - Create a text file renamed to .m4a
- `non_audio.txt` - Text file to test format validation

## Directory Structure

```
tests/fixtures/
├── audio_samples/          # Copy specific files from audio_files/
│   ├── tiny_2kb.m4a       # Copy of "5724 NE 60th Ave 101.m4a"
│   ├── small_16kb.m4a     # Copy of "Lucky Labrador 3.m4a"  
│   ├── medium_1mb.m4a     # Copy of "5724 NE 60th Ave 48.m4a"
│   ├── large_11mb.m4a     # Copy of "5724 NE 60th Ave 83.m4a"
│   └── xlarge_19mb.m4a    # Copy of "University of Oregon Portland 54.m4a"
├── expected_outputs/       # Expected results for deterministic testing
└── mock_responses/         # Mock API responses (unit tests only)
```

## Expected Outputs

For each test file, create a JSON file with expected results to validate against:

```json
{
  "file_name": "tiny_2kb.m4a",
  "expected_duration_range": [1.0, 5.0],
  "expected_size_bytes": 1990,
  "upload_should_succeed": true,
  "transcription_should_succeed": true,
  "expected_transcript_length_range": [10, 100],
  "deletion_analysis_expected": {
    "should_delete": false,
    "confidence_options": ["low", "medium", "high"]
  }
}
```

## Usage in Tests

```python
# Unit tests use mocks
def test_upload_with_mock():
    with patch('notion_client.Client') as mock:
        # Test logic without real API calls
        pass

# Integration tests use real files and real APIs  
def test_real_upload_small_file():
    file_path = "tests/fixtures/audio_samples/small_16kb.m4a"
    result = uploader.create_page(..., audio_file_path=file_path)
    # Test with real Notion API
    assert result is not None
```

## Setup Instructions

1. **Copy test files**:
   ```bash
   # From your audio_files directory, copy these specific files:
   cp "audio_files/5724 NE 60th Ave 101.m4a" tests/fixtures/audio_samples/tiny_2kb.m4a
   cp "audio_files/Lucky Labrador 3.m4a" tests/fixtures/audio_samples/small_16kb.m4a
   cp "audio_files/5724 NE 60th Ave 48.m4a" tests/fixtures/audio_samples/medium_1mb.m4a
   cp "audio_files/5724 NE 60th Ave 83.m4a" tests/fixtures/audio_samples/large_11mb.m4a
   cp "audio_files/University of Oregon Portland 54.m4a" tests/fixtures/audio_samples/xlarge_19mb.m4a
   ```

2. **Create edge case files**:
   ```bash
   # Create empty file
   touch tests/fixtures/audio_samples/empty_file.m4a
   
   # Create corrupted file  
   echo "This is not audio data" > tests/fixtures/audio_samples/corrupted.m4a
   ```

3. **Run initial tests** to establish baseline expected outputs

This approach gives us:
- **Consistent test data** (same files every time)
- **Real API testing** (integration tests)
- **Fast unit tests** (with mocks)
- **Comprehensive size coverage** (2KB to 158MB range)
- **Known file characteristics** for validation