"""
Claude Prompts Configuration
Centralized location for all Claude prompts with template variable substitution
"""

from string import Template
from typing import Dict, Any

class PromptTemplates:
    """Centralized prompt templates with variable substitution"""
    
    # Generic building blocks for reuse across prompts
    DELETION_ANALYSIS_BLOCK = """**DELETION ANALYSIS** - You are a thoughtful curator helping someone maintain a meaningful personal voice note archive. 

Your job is to evaluate voice note transcripts and recommend whether they should be KEPT or DELETED based on their potential future value.

DELETE a voice note if it contains:

1. Pure logistics: Temporary reminders that are no longer relevant ("pick up milk," "meeting at 3pm")
2. Technical testing: "Testing 1, 2, 3" or checking if the recording works
3. Incomplete thoughts: Fragment recordings with no meaningful content or context
4. Mundane status updates: Routine daily activities with no emotional or intellectual depth
5. Superseded information: Details that have been updated or replaced by newer information
6. Purely transactional: Basic coordination that served its immediate purpose ("running 5 minutes late")
7. Background noise/accidents: Recordings with no intentional content
8. Repetitive content: Ideas or thoughts already captured more fully in other notes

**For creative/musical content:** KEEP all music/creative recordings unless they are clearly test recordings or accidental captures. Creative expression is valuable and should be preserved.

When in doubt, lean toward KEEPING - future you might find unexpected value in what seems mundane today. Consider the voice note's potential for:

- Triggering forgotten memories
- Revealing patterns in thinking/behavior
- Providing emotional comfort during difficult times
- Inspiring future creative work"""
    
    TAGS_INSTRUCTION_BLOCK = """**TAGS** - Create up to 20 relevant tags (1-3 words each, Title Case, no slashes) that best describe this voice memo. Choose the most important and descriptive tags covering themes, focus areas, content types, emotional tones, and key topics. Ensure that all people, places, companies, location, and other important details are included as tags."""
    
    KEYWORDS_INSTRUCTION_BLOCK = """**KEYWORDS** - Extract a concise list of the most important named entities and symbolic figures that someone might search for later. Extract only: People's names, Organizations/companies/institutions, Cities or specific places, Symbolic figures/metaphors/archetypes (e.g., "lion," "chief," "fire," "mother wound"), Named events or rituals (e.g., "wedding," "Solstice," "interview," "brothers' circle"). Do not include: Emotional states, common actions, relationship terms, or general experiences. Output a flat comma-separated list (Up to 8 terms max)."""
    
    SUMMARY_INSTRUCTION_BLOCK = """**SUMMARY** - Create a concise 2-3 sentence summary that a human could read in 7s or less to understand the content (content_type, content_purpose, content_tone, audience, and key_insights). Write it in short hand so that's it's easy to read quickly."""
    
    STANDARD_OUTPUT_FORMAT = """**FORMAT YOUR RESPONSE EXACTLY AS:**

TITLE: [compelling title here]

PROCESSED_CONTENT:
[appropriate content processing]

SUMMARY: [2-3 sentence summary here]

TAGS: [tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8]

KEYWORDS: [keyword1, keyword2, keyword3, keyword4, keyword5]

DELETION_FLAG: [KEEP/DELETE]
DELETION_REASON: [brief explanation of your reasoning]"""
    
    # Music/Creative Content Processing Prompt
    MUSIC_ANALYSIS_PROMPT = Template(f"""Analyze this audio file that has been classified as music/creative content. Please provide ALL of the following in your response:

**ORIGINAL TRANSCRIPT:**
"${{transcript}}"

**FILENAME:** ${{filename}}

**AUDIO CLASSIFICATION:**
- Content Type: ${{audio_type}}
- Confidence: ${{confidence}}
- Top Predictions: ${{top_predictions}}

**IMPORTANT:** This audio was classified as "${{audio_type}}" with ${{confidence}} confidence. The transcript above may be garbled, repetitive, or nonsensical because this is a musical recording without clear vocals.

Please analyze this creative content and provide:

1. **TITLE** - Create a compelling title based on the filename and any discernible content. If the filename has meaningful information, use and improve it. Use proper Title Case capitalization.

2. **PROCESSED CONTENT** - Since this is a music file:
   - If the transcript is garbled/repetitive (like "24 24 24" or nonsensical patterns): Replace with "No transcript available - this is a music file without clear vocals"
   - If the transcript has some recognizable lyrics/words: Provide those lyrics cleaned up, noting "Partial lyrics from music file:"
   - If completely unclear: "No transcript available - this is an instrumental music file"

3. {SUMMARY_INSTRUCTION_BLOCK}

4. {TAGS_INSTRUCTION_BLOCK}

5. {KEYWORDS_INSTRUCTION_BLOCK}

6. {DELETION_ANALYSIS_BLOCK}

{STANDARD_OUTPUT_FORMAT}""")

    # Speech/Voice Memo Processing Prompt  
    SPEECH_ANALYSIS_PROMPT = Template(f"""Analyze this voice memo transcript and provide a comprehensive analysis. Please provide ALL of the following in your response:

**ORIGINAL TRANSCRIPT:**
"${{transcript}}"

**FILENAME:** ${{filename}}

**AUDIO CLASSIFICATION:**
- Content Type: ${{audio_type}}
- Confidence: ${{confidence}}
- Top Predictions: ${{top_predictions}}

This audio was classified as "${{audio_type}}" with ${{confidence}} confidence, indicating clear speech content.

Please analyze this voice memo and provide:

1. **TITLE** - Create a specific, compelling title (3-8 words) that captures the essence of the content. If the filename contains meaningful information, incorporate and improve it. Use proper Title Case capitalization.

2. **FORMATTED TRANSCRIPT** - Take the transcript and improve readability by fixing grammar, typos, and format for easy human readability (appropriate punctuation, capitalization, and paragraph breaks).  

3. {SUMMARY_INSTRUCTION_BLOCK}

4. {TAGS_INSTRUCTION_BLOCK}

5. {KEYWORDS_INSTRUCTION_BLOCK}

6. {DELETION_ANALYSIS_BLOCK}

**IMPORTANT:** ALWAYS provide the processed content regardless of deletion flag. The deletion analysis is separate from content processing.

{STANDARD_OUTPUT_FORMAT}""")

    # Fallback prompt for unknown/unclassified audio
    UNKNOWN_ANALYSIS_PROMPT = Template(f"""Analyze this voice memo transcript. The audio classification was uncertain.

**ORIGINAL TRANSCRIPT:**
"${{transcript}}"

**FILENAME:** ${{filename}}

**AUDIO CLASSIFICATION:**
- Content Type: ${{audio_type}}
- Confidence: ${{confidence}}

Please analyze this content and provide:

1. **TITLE** - Create a compelling title based on the content and filename. Use proper Title Case capitalization.

2. **PROCESSED_CONTENT** - Improve readability by fixing grammar, typos, and formatting while preserving ALL original ideas, words, and meaning. If the content appears to be garbled music, note that appropriately.

3. {SUMMARY_INSTRUCTION_BLOCK}

4. {TAGS_INSTRUCTION_BLOCK}

5. {KEYWORDS_INSTRUCTION_BLOCK}

6. {DELETION_ANALYSIS_BLOCK}

{STANDARD_OUTPUT_FORMAT}""")

    # Transcript Formatting Prompt - for formatting-only operations
    TRANSCRIPT_FORMAT_PROMPT = Template("""Format this transcript for better readability while preserving ALL original content.

**ORIGINAL TRANSCRIPT:**
"${transcript}"

**FILENAME:** ${filename}

**FORMATTING INSTRUCTIONS:**
You are a thoughtful, voice-centered editor. Transform this raw transcript into clear, emotionally resonant writing that feels like someone thinking out loud, supported by light structure to aid readability.

Guidelines:
1. Write with a natural, expressive voice that matches the speaker's tone and emotional arc
2. Use short to medium-length paragraphs (3–6 lines) with steady, flowing rhythm
3. Add ## section headings for major conceptual or emotional shifts (2–5 headings max)
4. Use **bold** sparingly for phrases with real emotional or thematic weight
5. Use > for deep, reflective thoughts (once or twice maximum)
6. Preserve ALL original ideas, words, and meaning - do not add, remove, or change concepts
7. Keep headings simple and clear - no clever titles

**RESPOND WITH VALID JSON:**
{
  "formatted_transcript": "Your formatted markdown text here"
}""")

    @classmethod
    def get_prompt_for_audio_type(cls, audio_type: str, **kwargs) -> str:
        """
        Get the appropriate prompt template for the audio type and substitute variables
        
        Args:
            audio_type: The classified audio type (Music, Speech, etc.)
            **kwargs: Variables to substitute in the template
            
        Returns:
            Fully substituted prompt string
        """
        # Normalize audio type
        audio_type_lower = audio_type.lower() if audio_type else 'unknown'
        
        # Select appropriate template
        if any(music_term in audio_type_lower for music_term in ['music', 'singing', 'song', 'instrumental']):
            template = cls.MUSIC_ANALYSIS_PROMPT
        elif any(speech_term in audio_type_lower for speech_term in ['speech', 'narration', 'monologue', 'conversation']):
            template = cls.SPEECH_ANALYSIS_PROMPT
        else:
            template = cls.UNKNOWN_ANALYSIS_PROMPT
        
        # Ensure all required variables have defaults
        substitution_vars = {
            'transcript': kwargs.get('transcript', ''),
            'filename': kwargs.get('filename', 'Voice Memo'),
            'audio_type': kwargs.get('audio_type', 'Unknown'),
            'confidence': f"{kwargs.get('confidence', 0.0):.3f}",
            'top_predictions': ', '.join([pred[0] for pred in kwargs.get('top_yamnet_predictions', [])[:3]]) or 'None available'
        }
        
        # Substitute variables in template
        try:
            return template.substitute(**substitution_vars)
        except KeyError as e:
            raise ValueError(f"Missing required template variable: {e}")

def get_analysis_prompt(audio_type: str, transcript: str, filename: str = '', 
                       audio_classification: Dict[str, Any] = None) -> str:
    """
    Convenience function to get a fully substituted analysis prompt
    
    Args:
        audio_type: The classified audio type
        transcript: The audio transcript
        filename: Original filename
        audio_classification: Full audio classification results
        
    Returns:
        Ready-to-use prompt string
    """
    classification_data = audio_classification or {}
    
    return PromptTemplates.get_prompt_for_audio_type(
        audio_type=audio_type,
        transcript=transcript,
        filename=filename,
        confidence=classification_data.get('confidence', 0.0),
        top_yamnet_predictions=classification_data.get('top_yamnet_predictions', [])
    )