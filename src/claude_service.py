"""
Claude Service - All Claude AI operations
Handles freeform tagging, transcript formatting, bucket classification, and analysis
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from config.config import CLAUDE_API_KEY
from config.prompts import get_analysis_prompt

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self, taxonomy_file: str = None):
        if not CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY not found in configuration")
        
        self.client = Anthropic(api_key=CLAUDE_API_KEY)
        
        # Load taxonomy from config file or use default
        self.taxonomy = self._load_taxonomy(taxonomy_file)
    
    def _load_taxonomy(self, taxonomy_file: str = None) -> Dict[str, Any]:
        """Load taxonomy from config file or return default"""
        
        # Try to load from provided file
        if taxonomy_file and os.path.exists(taxonomy_file):
            try:
                with open(taxonomy_file, 'r') as f:
                    taxonomy_data = json.load(f)
                
                # Extract life domains and focus areas from the config structure
                classification_buckets = taxonomy_data.get('classification_buckets', {})
                life_domains = classification_buckets.get('life_domains', [])
                focus_areas = classification_buckets.get('focus_areas', [])
                
                # Convert to the expected format
                life_domains_dict = {}
                for domain in life_domains:
                    life_domains_dict[domain] = f"Classification domain: {domain}"
                
                focus_areas_dict = {}
                # Group focus areas by domain (not currently used in Phase 1, but kept for consistency)
                for domain in life_domains:
                    focus_areas_dict[domain] = []
                
                # Add all focus areas as ungrouped for now
                for area in focus_areas:
                    if not any(area in areas for areas in focus_areas_dict.values()):
                        # Add to first domain or create ungrouped category
                        if life_domains:
                            if "Ungrouped" not in focus_areas_dict:
                                focus_areas_dict["Ungrouped"] = []
                            focus_areas_dict["Ungrouped"].append(area)
                
                logger.info(f"📥 Loaded taxonomy from {taxonomy_file}: {len(life_domains)} domains, {len(focus_areas)} focus areas")
                
                return {
                    "life_domains": life_domains_dict,
                    "focus_areas": focus_areas_dict,
                    "content_nature": self._get_default_content_nature(),
                    "energy_states": self._get_default_energy_states()
                }
                
            except Exception as e:
                logger.warning(f"Failed to load taxonomy from {taxonomy_file}: {e}. Using default taxonomy.")
        
        # Try to load from default location
        default_taxonomy_file = "classification_taxonomy.json"
        if os.path.exists(default_taxonomy_file):
            try:
                return self._load_taxonomy(default_taxonomy_file)
            except:
                pass
        
        # Fall back to default hardcoded taxonomy
        logger.info("Using default hardcoded taxonomy")
        return self._get_default_taxonomy()
    
    def _get_default_taxonomy(self) -> Dict[str, Any]:
        """Default hardcoded taxonomy as fallback"""
        return {
            "life_domains": {
                "🧠 Personal Development": "Self-improvement, growth, learning, inner work, psychology",
                "💕 Relationships": "Human connections, social bonds, family, friends, romance",  
                "💼 Work & Career": "Professional life, business, jobs, career development",
                "🏠 Life Management": "Daily operations, practical matters, logistics, administration",
                "🌱 Health & Wellbeing": "Physical, mental, emotional health, medical, self-care",
                "🎨 Creativity & Expression": "Art, creation, innovation, intellectual pursuits",
                "🕊️ Spirituality & Meaning": "Faith, purpose, consciousness, existential questions",
                "🌍 World & Society": "External events, communities, social issues, current events"
            },
            "focus_areas": {
                "🧠 Personal Development": [
                    "Self-Reflection", "Skill Building", "Goal Setting", "Mindset & Psychology", "Personal Systems"
                ],
                "💕 Relationships": [
                    "Romantic/Partnership", "Family", "Friendships", "Professional", "Community"
                ],
                "💼 Work & Career": [
                    "Job Performance", "Career Planning", "Business Operations", "Financial/Commercial", "Professional Growth"
                ],
                "🏠 Life Management": [
                    "Home & Living", "Finances & Money", "Time & Scheduling", "Health & Medical", "Legal & Administrative"
                ],
                "🌱 Health & Wellbeing": [
                    "Physical Health", "Mental Health", "Emotional Processing", "Self-Care", "Substance & Addiction"
                ],
                "🎨 Creativity & Expression": [
                    "Artistic Creation", "Innovation & Ideas", "Performance & Entertainment", "Craft & Making", "Intellectual Pursuits"
                ],
                "🕊️ Spirituality & Meaning": [
                    "Faith & Religion", "Personal Spirituality", "Life Purpose", "Death & Mortality", "Transcendence"
                ],
                "🌍 World & Society": [
                    "Current Events", "Community Service", "Cultural & Social", "Environment & Nature", "Technology & Future"
                ]
            },
            "content_nature": self._get_default_content_nature(),
            "energy_states": self._get_default_energy_states()
        }
    
    def _get_default_content_nature(self) -> Dict[str, str]:
        """Default content nature categories"""
        return {
            "🤔 Questioning": "Inquiries, wondering, exploring unknowns, seeking answers",
            "💡 Insight": "Realizations, understanding, 'aha moments,' breakthroughs",
            "⚡ Planning": "Decisions, next steps, strategy, action items, goal setting",
            "📝 Processing": "Working through experiences, emotions, situations, integration",
            "🎯 Practice": "Exercises, mantras, skills, embodiment, routine activities",
            "🎭 Storytelling": "Narratives, experiences, memories, events, sharing stories",
            "🔮 Visioning": "Future possibilities, dreams, imagination, creative ideas",
            "📊 Analysis": "Breaking down, evaluating, comparing, studying, examining"
        }
    
    def _get_default_energy_states(self) -> Dict[str, str]:
        """Default energy state categories"""
        return {
            "🔥 Activated": "High energy, motivated, passionate, urgent, excited",
            "💎 Clarity": "Clear thinking, confident knowing, focused, decisive",
            "🌊 Flow": "Ease, natural rhythm, effortless movement, in the zone",
            "🌱 Expansion": "Openness, growth, possibility, curiosity, exploration",
            "🪨 Stability": "Grounded, steady, calm, peaceful, centered",
            "🌫️ Confusion": "Uncertainty, overwhelm, unclear direction, mixed feelings",
            "⚡ Tension": "Stress, conflict, resistance, difficulty, struggle",
            "😴 Low Energy": "Tired, depleted, sluggish, withdrawn, unmotivated"
        }

    # PHASE 1 FUNCTIONS

    def process_transcript_complete(self, transcript: str, filename: str = '', audio_type: str = None, audio_classification: Dict = None) -> Dict[str, Any]:
        """Single comprehensive Claude API call to get everything we need from a transcript"""
        try:
            # Get the appropriate prompt template based on audio type
            prompt = get_analysis_prompt(
                audio_type=audio_type or 'Unknown',
                transcript=transcript,
                filename=filename,
                audio_classification=audio_classification
            )
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,  # Increased for comprehensive response
                temperature=0.3,  # Balanced for creativity and consistency
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text
            logger.info(f"Comprehensive transcript analysis complete: {len(response_text)} characters")
            
            return self._parse_comprehensive_response(response_text)
            
        except Exception as e:
            logger.error(f"Error in comprehensive transcript processing: {e}")
            return {
                "title": filename or "Voice Memo",
                "formatted_transcript": transcript,
                "summary": "",
                "claude_tags": {
                    "tags": "",
                    "keywords": ""
                },
                "deletion_analysis": {
                    'should_delete': False,
                    'confidence': 'low',
                    'reason': 'Analysis error'
                }
            }

    def _parse_comprehensive_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the comprehensive Claude response into structured data"""
        result = {
            "title": "Voice Memo",
            "formatted_transcript": "",
            "summary": "",
            "claude_tags": {
                "tags": "",
                "keywords": ""
            },
            "deletion_analysis": {
                'should_delete': False,
                'confidence': 'low',
                'reason': 'Unknown'
            }
        }
        
        lines = response_text.strip().split('\n')
        current_section = None
        processed_content_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith("TITLE:"):
                result["title"] = line_stripped.replace("TITLE:", "").strip()
            elif line_stripped.startswith("PROCESSED_CONTENT:"):
                current_section = "processed_content"
                continue
            elif line_stripped.startswith("SUMMARY:"):
                current_section = None
                result["summary"] = line_stripped.replace("SUMMARY:", "").strip()
            elif line_stripped.startswith("TAGS:"):
                result["claude_tags"]["tags"] = line_stripped.replace("TAGS:", "").strip()
            elif line_stripped.startswith("KEYWORDS:"):
                result["claude_tags"]["keywords"] = line_stripped.replace("KEYWORDS:", "").strip()
            elif line_stripped.startswith("DELETION_FLAG:"):
                flag_value = line_stripped.replace("DELETION_FLAG:", "").strip().lower()
                result["deletion_analysis"]["should_delete"] = flag_value == 'true'
            elif line_stripped.startswith("DELETION_CONFIDENCE:"):
                result["deletion_analysis"]["confidence"] = line_stripped.replace("DELETION_CONFIDENCE:", "").strip().lower()
            elif line_stripped.startswith("DELETION_REASON:"):
                result["deletion_analysis"]["reason"] = line_stripped.replace("DELETION_REASON:", "").strip()
            elif current_section == "processed_content":
                # Collect all lines for processed content
                processed_content_lines.append(line)
        
        # Join processed content lines
        if processed_content_lines:
            result["formatted_transcript"] = '\n'.join(processed_content_lines).strip()
        
        return result

    def generate_freeform_tags(self, transcript: str) -> Dict[str, str]:
        """Generate standardized multi-select tags from transcript (Phase 1)"""
        try:
            prompt = f"""Analyze this voice memo and create 5-10 relevant tags that best describe the content.

**TRANSCRIPT:**
"{transcript}"

**TAGGING INSTRUCTIONS:**
- Create 5-10 tags total (not more, not less)
- Each tag should be 1-3 words maximum
- Use Title Case (First Letter Capitalized)
- No slashes or special characters except spaces
- Choose the most important and descriptive tags covering themes, focus areas, content types, emotional tones, and key topics
- Be specific but concise

**Examples of good tags:**
"Inner Child Work", "Spiritual Practice", "Personal Reflection", "Contemplative", "Vulnerable", "Physical Touch", "Inner Peace", "Relationship Boundaries"

**Format your response as:**
Tags: [tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8]
Brief Summary: [1-2 sentence summary]"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                temperature=0.4,  # Higher temperature for more creative/natural tags
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text
            logger.info(f"Free-form tags response: {response_text}")
            
            return self._parse_freeform_response(response_text)
            
        except Exception as e:
            logger.error(f"Error generating free-form tags: {e}")
            return {
                "tags": "",
                "brief_summary": ""
            }

    def _parse_freeform_response(self, response_text: str) -> Dict[str, str]:
        """Parse the standardized multi-select tagging response"""
        tags = {
            "tags": "",
            "brief_summary": ""
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Tags:"):
                tags["tags"] = line.replace("Tags:", "").strip()
            elif line.startswith("Brief Summary:"):
                tags["brief_summary"] = line.replace("Brief Summary:", "").strip()
        
        return tags

    def format_transcript(self, transcript: str) -> str:
        """Format transcript for better readability while preserving core content (Phase 1)"""
        try:
            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len(transcript) // 4
            
            # Choose model and max_tokens based on transcript size
            if estimated_tokens < 7500:  # Small file - use cheaper Haiku 3.5
                model = "claude-3-5-haiku-20241022"
                max_tokens = 8192
                logger.info(f"Using Claude 3.5 Haiku for small transcript ({estimated_tokens} estimated tokens)")
            else:  # Large file - use Sonnet 3.5 with higher token limit
                model = "claude-3-5-sonnet-20241022"  # Use regular Sonnet 3.5 
                max_tokens = 8192  # Sonnet 3.5 max tokens
                logger.info(f"Using Claude 3.5 Sonnet for large transcript ({estimated_tokens} estimated tokens)")

            prompt = f"""Please improve the readability of this voice memo transcript. Fix grammar, typos, and formatting while preserving ALL the original ideas, words, and meaning. Do not change the core content or voice - just make it more readable.

Rules:
- Fix obvious typos and grammar mistakes
- Add appropriate punctuation and capitalization
- Break into paragraphs where natural
- Preserve all original words and ideas
- Keep the speaker's authentic voice and style
- Do not add, remove, or change any concepts
- Only output the formatted text and nothing else - no preambles, explanations, or additional text

Original transcript: "{transcript}"

Only output the formatted transcript:"""
            
            # Use streaming for large transcripts with Claude 3.5 Sonnet
            if model == "claude-3-5-sonnet-20241022" and estimated_tokens >= 7500:
                logger.info("Using streaming mode for large transcript")
                formatted_chunks = []
                
                with self.client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        formatted_chunks.append(text)
                
                formatted = ''.join(formatted_chunks).strip()
            else:
                # Regular non-streaming for smaller transcripts
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ]
                )
                formatted = response.content[0].text.strip()
            logger.info(f"Formatted transcript: {len(formatted)} characters")
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting transcript: {e}")
            return transcript  # Return original if formatting fails

    def generate_summary(self, transcript: str) -> str:
        """Generate a concise summary of the voice memo (Phase 1)"""
        try:
            prompt = f"""Please create a concise 2-3 sentence summary of this voice memo transcript. Focus on the key insights, questions, or experiences shared.

Transcript: "{transcript}"

Summary:"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                temperature=0.4,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            summary = response.content[0].text.strip()
            logger.info(f"Generated summary: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return ""

    def analyze_deletion_flag(self, transcript: str) -> Dict[str, any]:
        """Analyze if the voice memo should be flagged for deletion based on real patterns (Phase 1)"""
        try:
            prompt = f"""Analyze this voice memo transcript to determine if it should be flagged for deletion.

Based on analysis of real examples, FLAG FOR DELETION if the content appears to be:

1. **CONTENT RECORDED FOR SOMEONE ELSE:**
   - Profile/dating app responses (answering "how would friends describe you" type questions)
   - Team communications ("Hey y'all", "Hey team", addressing colleagues)
   - Role/process explanations (describing job roles, procedures for others)
   - Community/event descriptions (explaining concepts for external use)

2. **ADDRESSING OTHERS DIRECTLY:**
   - Uses "Hey [group]", "So the [role] is...", "You would..." (to external audience)
   - Explanation mode: teaching or describing something for someone else
   - Response format: answering implied questions or prompts for others

3. **DRAFT/RECORDING FOR OTHER PLATFORMS:**
   - Content clearly intended to be rewritten/used elsewhere
   - Sounds like preparation for emails, messages, or posts

DEFINITELY KEEP (don't flag) if the content is:
- Personal reflections, insights, or spiritual/emotional processing
- Inner dialogue or self-compassion work ("inner child", "little heart")
- Contemplative, meandering thoughts without clear external audience
- Creative ideas, vision work, or meaningful experiences
- First-person introspective processing ("I feel", "I realized", "I'm thinking")
- Philosophical insights or personal realizations
- Authentic emotional exploration or therapeutic self-talk

IMPORTANT: If "you" refers to the speaker's own inner self/child rather than an external audience, this should be KEPT, not flagged.

Transcript: "{transcript}"

Respond with exactly this format:
DELETION_FLAG: [true/false]
CONFIDENCE: [high/medium/low]
REASON: [brief explanation of why this should/shouldn't be flagged]
"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=150,
                temperature=0.1,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            logger.info(f"Deletion analysis response: {response_text}")
            
            return self._parse_deletion_response(response_text)
            
        except Exception as e:
            logger.error(f"Error analyzing deletion flag: {e}")
            return {
                'should_delete': False,
                'confidence': 'low',
                'reason': 'Error in analysis'
            }

    def _parse_deletion_response(self, response_text: str) -> Dict[str, any]:
        """Parse deletion analysis response"""
        result = {
            'should_delete': False,
            'confidence': 'low',
            'reason': 'Unknown'
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("DELETION_FLAG:"):
                flag_value = line.replace("DELETION_FLAG:", "").strip().lower()
                result['should_delete'] = flag_value == 'true'
            elif line.startswith("CONFIDENCE:"):
                result['confidence'] = line.replace("CONFIDENCE:", "").strip().lower()
            elif line.startswith("REASON:"):
                result['reason'] = line.replace("REASON:", "").strip()
        
        return result

    # PHASE 2 FUNCTIONS

    def analyze_all_tags_for_classification(self, all_freeform_tags: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Analyze all freeform tags to create master classification buckets (Phase 2)"""
        try:
            # Compile all unique tags
            all_tags = set()
            for tag_set in all_freeform_tags:
                for category, tags in tag_set.items():
                    if tags and category != 'brief_summary':
                        # Split comma-separated tags and clean them
                        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                        all_tags.update(tag_list)
            
            tags_text = ', '.join(sorted(all_tags))
            
            life_domains_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["life_domains"].items()])
            
            # Build focus areas text for each domain
            focus_areas_text = ""
            for domain, areas in self.taxonomy["focus_areas"].items():
                focus_areas_text += f"\n**{domain}:**\n"
                focus_areas_text += "\n".join([f"  - {area}" for area in areas])
                focus_areas_text += "\n"
            
            prompt = f"""Based on analysis of all voice memo tags from our collection, create the final master classification system.

**ALL TAGS FROM VOICE MEMOS:**
{tags_text}

**AVAILABLE LIFE DOMAINS:**
{life_domains_text}

**AVAILABLE FOCUS AREAS:**
{focus_areas_text}

Based on the actual tags we have, determine:
1. Which Life Domains are actually relevant (only include domains that have voice memos)
2. Which Focus Areas are actually relevant within those domains
3. Any additional Focus Areas we should add based on the tags we see

**IMPORTANT: Respond with EXACTLY this format using comma-separated lists:**

RELEVANT_LIFE_DOMAINS: domain1, domain2, domain3, domain4, domain5
RELEVANT_FOCUS_AREAS: area1, area2, area3, area4, area5, area6
ADDITIONAL_FOCUS_AREAS_NEEDED: new_area1, new_area2, new_area3

Use comma-separated values on single lines. Do not use bullet points or multiple lines per section.
"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                temperature=0.2,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            logger.info(f"Classification analysis response: {response_text}")
            
            return self._parse_classification_response(response_text)
            
        except Exception as e:
            logger.error(f"Error analyzing tags for classification: {e}")
            return {
                'life_domains': list(self.taxonomy["life_domains"].keys()),
                'focus_areas': []
            }

    def _parse_classification_response(self, response_text: str) -> Dict[str, List[str]]:
        """Parse classification analysis response with comma-separated values"""
        result = {
            'life_domains': [],
            'focus_areas': []
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("RELEVANT_LIFE_DOMAINS:"):
                domains_text = line.replace("RELEVANT_LIFE_DOMAINS:", "").strip()
                if domains_text:
                    result['life_domains'] = [d.strip() for d in domains_text.split(',') if d.strip()]
                    
            elif line.startswith("RELEVANT_FOCUS_AREAS:"):
                areas_text = line.replace("RELEVANT_FOCUS_AREAS:", "").strip()
                if areas_text:
                    result['focus_areas'] = [a.strip() for a in areas_text.split(',') if a.strip()]
                    
            elif line.startswith("ADDITIONAL_FOCUS_AREAS_NEEDED:"):
                additional_text = line.replace("ADDITIONAL_FOCUS_AREAS_NEEDED:", "").strip()
                if additional_text:
                    additional_areas = [a.strip() for a in additional_text.split(',') if a.strip()]
                    result['focus_areas'].extend(additional_areas)
        
        return result

    # PHASE 3 FUNCTIONS

    def assign_bucket_tags_batch(self, batch_pages: List[Dict[str, Any]], available_life_domains: List[str], 
                                available_focus_areas: List[str], batch_number: int = 1) -> Dict[str, Any]:
        """Send a batch of voice memos to Claude for bucket tag assignment (Phase 3)"""
        try:
            prompt = self._build_batch_assignment_prompt(batch_pages, available_life_domains, 
                                                       available_focus_areas, batch_number)
            
            logger.info(f"🤖 Sending batch {batch_number} to Claude ({len(batch_pages)} memos)...")
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent classification
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            
            try:
                # Extract JSON from response (Claude may include additional text)
                import json
                
                # Find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise json.JSONDecodeError("No JSON found in response", response_text, 0)
                
                json_str = response_text[json_start:json_end]
                classifications = json.loads(json_str)
                
                logger.info(f"✅ Successfully classified batch {batch_number}")
                
                return {
                    'success': True,
                    'classifications': classifications,
                    'batch_size': len(batch_pages)
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for batch {batch_number}: {e}")
                logger.error(f"Raw response: {response_text}")
                return {
                    'success': False,
                    'error': f'JSON parsing failed: {e}',
                    'raw_response': response_text
                }
                
        except Exception as e:
            error_msg = f"Claude API error for batch {batch_number}: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def _build_batch_assignment_prompt(self, batch_pages: List[Dict[str, Any]], 
                                     available_life_domains: List[str], 
                                     available_focus_areas: List[str], 
                                     batch_number: int) -> str:
        """Build prompt for batch bucket assignment using new format"""
        import json
        
        # Format life domains and topics as JSON arrays
        life_areas_json = json.dumps(available_life_domains, indent=2)
        topics_json = json.dumps(available_focus_areas, indent=2)
        
        batch_prompt = f"""You are classifying voice notes to make them easily searchable by humans. Assign two fields to each note: life_areas and topics. Use the predefined options below.

You may select multiple tags for each field, but only if it improves searchability.

Input: A summary and comma-separated list of general classification tags for each voice memo.
Output: A JSON in this exact format:

life_areas = [a, b, c]
topics = [a, b, c]

Available Life Areas:
{life_areas_json}

Available Topics:
{topics_json}

Voice Memos To Classify:

"""
        
        for i, page in enumerate(batch_pages, 1):
            title = page.get('title', 'Untitled')
            tags = page.get('tags', {})
            summary = page.get('summary', '')
            
            # Extract comma-separated tags
            tags_list = []
            for category, tag_values in tags.items():
                if tag_values and category != 'brief_summary':
                    # Parse comma-separated tags
                    parsed_tags = [tag.strip() for tag in str(tag_values).split(',') if tag.strip()]
                    tags_list.extend(parsed_tags)
            
            tags_text = ", ".join(tags_list) if tags_list else "No tags available"
            summary_text = summary if summary else "No summary available"
            
            batch_prompt += f"""**Voice Memo {i}:**
Title: "{title}"
Summary: {summary_text}
General Classification Tags: {tags_text}

"""

        batch_prompt += """Return JSON with this exact format for each memo (numbered 1, 2, 3...):

{
  "1": {
    "life_areas": ["Life Area 1", "Life Area 2"],
    "topics": ["Topic 1", "Topic 2", "Topic 3"]
  },
  "2": {
    "life_areas": ["Life Area 1"],
    "topics": ["Topic 1", "Topic 2"]
  }
}

**IMPORTANT:** 
- Use only the exact names from the Available Life Areas and Available Topics lists above
- Select multiple options only if it improves searchability
- Use arrays even for single values"""

        return batch_prompt

    # COMBINED PROCESSING FUNCTION (for backward compatibility)
    
    def process_transcript(self, transcript: str, filename: str = '') -> Dict:
        """Complete processing: format transcript + tags + summary + deletion flag"""
        if not transcript:
            return {
                'claude_tags': {},
                'summary': '',
                'deletion_analysis': {'should_delete': False, 'confidence': 'low', 'reason': 'Empty transcript'},
                'formatted_transcript': '',
                'filename_info': filename
            }
        
        logger.info("Processing transcript with Claude...")
        
        # Format transcript for readability
        formatted_transcript = self.format_transcript(transcript)
        
        # Generate freeform tags (using original transcript for accuracy)
        claude_tags = self.generate_freeform_tags(transcript)
        
        # Generate summary (using original transcript)
        summary = self.generate_summary(transcript)
        
        # Analyze deletion flag (using original transcript)
        deletion_analysis = self.analyze_deletion_flag(transcript)
        
        return {
            'claude_tags': claude_tags,
            'summary': summary,
            'deletion_analysis': deletion_analysis,
            'formatted_transcript': formatted_transcript,
            'filename_info': filename
        }