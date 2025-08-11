# Transcript Fixtures for Unit Testing

This directory contains transcript fixtures for testing the `ClaudeService.process_transcript_complete` function.

## Fixture Files

### `large_transcript_fixture.txt`
**Purpose**: Test large transcript processing with Claude 3.5 Sonnet and streaming
**Requirements**: Should be 30,000+ characters to trigger large transcript processing path
**What to put here**: 
- Use the transcript from the 40-minute test file (`/tests/fixtures/data/large_file_transcipt.md`)
- Or combine multiple smaller transcripts to reach the size threshold
- Should represent actual voice memo content (personal reflections, long-form thinking, etc.)

### `normal_transcript_fixture.txt`  
**Purpose**: Test normal transcript processing with Claude 3.5 Haiku
**Requirements**: Should be under 30,000 characters to trigger normal processing path
**What to put here**:
- Use a transcript from a 2-5 minute voice memo
- Should be substantial content but not huge
- Examples: personal reflections, planning sessions, insights
- Should trigger realistic tag generation and processing

### `empty_transcript_fixture.txt`
**Purpose**: Test edge case handling for empty/minimal transcripts
**Requirements**: Should be empty or nearly empty
**Current state**: Already set up as empty file - no changes needed

## How to Populate Fixtures

1. **For large_transcript_fixture.txt**:
   ```bash
   # Copy from existing large transcript
   cp tests/fixtures/data/large_file_transcipt.md tests/fixtures/transcripts/large_transcript_fixture.txt
   ```

2. **For normal_transcript_fixture.txt**:
   - Choose any voice memo transcript that's meaningful but under 30,000 characters
   - You can extract from successful test runs or use existing audio file transcripts

## Running the Tests

Once you've populated the fixtures:

```bash
# Run just the Claude service tests
pytest tests/unit/services/test_claude_process_transcript_complete.py -v

# Run with coverage
pytest tests/unit/services/test_claude_process_transcript_complete.py --cov=claude_service -v
```

## Test Coverage

The test suite covers:
- ✅ Small transcript processing (Haiku model selection)
- ✅ Large transcript processing (Sonnet + streaming)
- ✅ Empty transcript edge cases
- ✅ Audio classification integration
- ✅ Error handling and fallbacks
- ✅ Response parsing and field extraction
- ✅ Token estimation logic
- ✅ Model selection based on transcript size