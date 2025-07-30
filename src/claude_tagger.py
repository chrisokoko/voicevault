import os
import logging
from typing import Dict, List, Optional
from anthropic import Anthropic
from config.config import CLAUDE_API_KEY

logger = logging.getLogger(__name__)

class ClaudeTagger:
    def __init__(self):
        if not CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY not found in configuration")
        
        self.client = Anthropic(api_key=CLAUDE_API_KEY)
        
        # Universal Voice Note Taxonomy - designed for 1M+ voice notes across all human experience
        self.taxonomy = {
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
            "content_nature": {
                "🤔 Questioning": "Inquiries, wondering, exploring unknowns, seeking answers",
                "💡 Insight": "Realizations, understanding, 'aha moments,' breakthroughs",
                "⚡ Planning": "Decisions, next steps, strategy, action items, goal setting",
                "📝 Processing": "Working through experiences, emotions, situations, integration",
                "🎯 Practice": "Exercises, mantras, skills, embodiment, routine activities",
                "🎭 Storytelling": "Narratives, experiences, memories, events, sharing stories",
                "🔮 Visioning": "Future possibilities, dreams, imagination, creative ideas",
                "📊 Analysis": "Breaking down, evaluating, comparing, studying, examining"
            },
            "energy_states": {
                "🔥 Activated": "High energy, motivated, passionate, urgent, excited",
                "💎 Clarity": "Clear thinking, confident knowing, focused, decisive",
                "🌊 Flow": "Ease, natural rhythm, effortless movement, in the zone",
                "🌱 Expansion": "Openness, growth, possibility, curiosity, exploration",
                "🪨 Stability": "Grounded, steady, calm, peaceful, centered",
                "🌫️ Confusion": "Uncertainty, overwhelm, unclear direction, mixed feelings",
                "⚡ Tension": "Stress, conflict, resistance, difficulty, struggle",
                "😴 Low Energy": "Tired, depleted, sluggish, withdrawn, unmotivated"
            }
        }
    
    def create_tagging_prompt(self, transcript: str) -> str:
        """Create a prompt for Claude to tag the transcript using our taxonomy"""
        
        life_domains_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["life_domains"].items()])
        content_nature_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["content_nature"].items()])
        energy_states_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["energy_states"].items()])
        
        # Build focus areas text for each domain
        focus_areas_text = ""
        for domain, areas in self.taxonomy["focus_areas"].items():
            focus_areas_text += f"\n**{domain}:**\n"
            focus_areas_text += "\n".join([f"  - {area}" for area in areas])
            focus_areas_text += "\n"
        
        prompt = f"""Please analyze this voice memo transcript using this comprehensive taxonomy designed for universal voice note categorization:

**STEP 1: LIFE DOMAIN** (Pick exactly 1 primary domain):
{life_domains_text}

**STEP 2: FOCUS AREA** (You MUST pick from the predefined list below based on your chosen Life Domain):
{focus_areas_text}

**STEP 3: CONTENT NATURE** (Pick exactly 1):
{content_nature_text}

**STEP 4: ENERGY STATE** (Pick 1 if clearly evident, or "None" if unclear):
{energy_states_text}

**TRANSCRIPT TO ANALYZE:**
"{transcript}"

**IMPORTANT:** For Focus Area, you MUST choose one of the exact options listed above for your chosen Life Domain. Do not create new focus area names.

**RESPOND IN THIS EXACT FORMAT:**
Life Domain: [chosen domain]
Focus Area: [specific sub-area within the domain]
Content Nature: [chosen type]
Energy State: [chosen state or "None"]

Explanation: [Brief reasoning for your choices, especially focus area selection]"""

        return prompt
    
    def parse_claude_response(self, response_text: str) -> Dict[str, str]:
        """Parse Claude's response into structured tags"""
        tags = {
            "life_domain": "",
            "focus_area": "",
            "content_nature": "",
            "energy_state": "",
            "explanation": ""
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Life Domain:"):
                tags["life_domain"] = line.replace("Life Domain:", "").strip()
            elif line.startswith("Focus Area:"):
                tags["focus_area"] = line.replace("Focus Area:", "").strip()
            elif line.startswith("Content Nature:"):
                tags["content_nature"] = line.replace("Content Nature:", "").strip()
            elif line.startswith("Energy State:"):
                tags["energy_state"] = line.replace("Energy State:", "").strip()
            elif line.startswith("Explanation:"):
                tags["explanation"] = line.replace("Explanation:", "").strip()
        
        return tags
    
    def generate_freeform_tags(self, transcript: str) -> Dict[str, str]:
        """Generate standardized multi-select tags from transcript"""
        try:
            prompt = f"""Analyze this voice memo and create standardized tags. Each tag should be 1-3 words, properly capitalized (Title Case), no slashes.

**TRANSCRIPT:**
"{transcript}"

**Generate tags for these categories:**

1. **Primary Themes** (1-3 words each, pick 1-2 main themes):
   Examples: "Inner Child Work", "Spiritual Practice", "Relationship Boundaries"

2. **Specific Focus** (1-3 words each, pick 1-2 specific aspects):
   Examples: "Male Emotional Intelligence", "Sacred Sexuality", "Personal Ceremony"

3. **Content Types** (1-3 words each, pick 1-2 types):
   Examples: "Personal Reflection", "Instructional Guidance", "Emotional Processing", "Philosophical Insight", "Affirmation Letter"

4. **Emotional Tones** (1-2 words each, pick 1-2 main tones):
   Examples: "Contemplative", "Vulnerable", "Nurturing", "Triggered", "Peaceful"

5. **Key Topics** (1-3 words each, pick 3-6 specific topics):
   Examples: "Physical Touch", "Inner Peace", "Spiritual Journey", "Emotional Safety"

**IMPORTANT FORMATTING RULES:**
- Each tag must be 1-3 words maximum
- Use Title Case (First Letter Capitalized)
- No slashes or special characters except spaces
- Be specific but concise

**Format your response as:**
Primary Themes: [tag1, tag2]
Specific Focus: [tag1, tag2] 
Content Types: [tag1, tag2]
Emotional Tones: [tag1, tag2]
Key Topics: [tag1, tag2, tag3, tag4, tag5, tag6]
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
            
            return self.parse_freeform_response(response_text)
            
        except Exception as e:
            logger.error(f"Error generating free-form tags: {e}")
            return {
                "primary_theme": "",
                "specific_focus": "",
                "content_type": "",
                "emotional_tone": "",
                "key_topics": "",
                "brief_summary": ""
            }

    def parse_freeform_response(self, response_text: str) -> Dict[str, str]:
        """Parse the standardized multi-select tagging response"""
        tags = {
            "primary_themes": "",
            "specific_focus": "",
            "content_types": "",
            "emotional_tones": "",
            "key_topics": "",
            "brief_summary": ""
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Primary Themes:"):
                tags["primary_themes"] = line.replace("Primary Themes:", "").strip()
            elif line.startswith("Specific Focus:"):
                tags["specific_focus"] = line.replace("Specific Focus:", "").strip()
            elif line.startswith("Content Types:"):
                tags["content_types"] = line.replace("Content Types:", "").strip()
            elif line.startswith("Emotional Tones:"):
                tags["emotional_tones"] = line.replace("Emotional Tones:", "").strip()
            elif line.startswith("Key Topics:"):
                tags["key_topics"] = line.replace("Key Topics:", "").strip()
            elif line.startswith("Brief Summary:"):
                tags["brief_summary"] = line.replace("Brief Summary:", "").strip()
        
        return tags

    def map_to_taxonomy(self, freeform_tags: Dict[str, str]) -> Dict[str, str]:
        """Second pass: Map free-form tags to our hierarchical taxonomy"""
        try:
            # Build taxonomy context
            life_domains_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["life_domains"].items()])
            content_nature_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["content_nature"].items()])
            energy_states_text = "\n".join([f"- {name}: {desc}" for name, desc in self.taxonomy["energy_states"].items()])
            
            # Build focus areas text for each domain
            focus_areas_text = ""
            for domain, areas in self.taxonomy["focus_areas"].items():
                focus_areas_text += f"\n**{domain}:**\n"
                focus_areas_text += "\n".join([f"  - {area}" for area in areas])
                focus_areas_text += "\n"

            prompt = f"""Based on these free-form tags, map them to our structured taxonomy:

**FREE-FORM ANALYSIS:**
Primary Theme: {freeform_tags.get('primary_theme', 'N/A')}
Specific Focus: {freeform_tags.get('specific_focus', 'N/A')}
Content Type: {freeform_tags.get('content_type', 'N/A')}
Emotional Tone: {freeform_tags.get('emotional_tone', 'N/A')}
Key Topics: {freeform_tags.get('key_topics', 'N/A')}

**MAP TO STRUCTURED TAXONOMY:**

**Life Domains** (choose 1):
{life_domains_text}

**Focus Areas** (choose from the appropriate domain):
{focus_areas_text}

**Content Nature** (choose 1):
{content_nature_text}

**Energy States** (choose 1 or "None"):
{energy_states_text}

**Respond in this exact format:**
Life Domain: [chosen domain]
Focus Area: [chosen focus area]
Content Nature: [chosen nature]
Energy State: [chosen state or "None"]
Mapping Reasoning: [brief explanation of mapping choices]"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.2,  # Lower temperature for consistent mapping
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text
            logger.info(f"Taxonomy mapping response: {response_text}")
            
            return self.parse_taxonomy_mapping(response_text)
            
        except Exception as e:
            logger.error(f"Error mapping to taxonomy: {e}")
            return {
                "life_domain": "",
                "focus_area": "",
                "content_nature": "",
                "energy_state": "",
                "explanation": f"Mapping error: {str(e)}"
            }

    def parse_taxonomy_mapping(self, response_text: str) -> Dict[str, str]:
        """Parse the taxonomy mapping response"""
        tags = {
            "life_domain": "",
            "focus_area": "",
            "content_nature": "",
            "energy_state": "",
            "explanation": ""
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Life Domain:"):
                tags["life_domain"] = line.replace("Life Domain:", "").strip()
            elif line.startswith("Focus Area:"):
                tags["focus_area"] = line.replace("Focus Area:", "").strip()
            elif line.startswith("Content Nature:"):
                tags["content_nature"] = line.replace("Content Nature:", "").strip()
            elif line.startswith("Energy State:"):
                tags["energy_state"] = line.replace("Energy State:", "").strip()
            elif line.startswith("Mapping Reasoning:"):
                tags["explanation"] = line.replace("Mapping Reasoning:", "").strip()
        
        # Clean up energy state
        if tags["energy_state"].lower() in ["none", "unclear", "n/a"]:
            tags["energy_state"] = ""
        
        return tags

    def generate_claude_tags(self, transcript: str) -> Dict[str, str]:
        """Program 1: Generate free-form tags only - no taxonomy mapping"""
        return self.generate_freeform_tags(transcript)
    
    def analyze_deletion_flag(self, transcript: str) -> Dict[str, any]:
        """Analyze if the voice memo should be flagged for deletion based on real patterns"""
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
            logger.info(f"Deletion analysis: {response_text}")
            
            # Parse the response
            deletion_flag = False
            confidence = "low"
            reason = "Analysis failed"
            
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("DELETION_FLAG:"):
                    deletion_flag = "true" in line.lower()
                elif line.startswith("CONFIDENCE:"):
                    confidence = line.split(":", 1)[1].strip().lower()
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
            
            return {
                "should_delete": deletion_flag,
                "confidence": confidence,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error analyzing deletion flag: {e}")
            return {
                "should_delete": False,
                "confidence": "low", 
                "reason": f"Analysis error: {str(e)}"
            }

    def format_transcript_for_readability(self, transcript: str) -> str:
        """Format transcript for better readability while preserving core content"""
        try:
            prompt = f"""Please improve the readability of this voice memo transcript. Fix grammar, typos, and formatting while preserving ALL the original ideas, words, and meaning. Do not change the core content or voice - just make it more readable.

Rules:
- Fix obvious typos and grammar mistakes
- Add appropriate punctuation and capitalization
- Break into paragraphs where natural
- Preserve all original words and ideas
- Keep the speaker's authentic voice and style
- Do not add, remove, or change any concepts

Original transcript: "{transcript}"

Formatted transcript:"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.2,  # Lower temperature for precise formatting
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
        """Generate a concise summary of the voice memo"""
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
            logger.info(f"Generated summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Unable to generate summary"
    
    def process_transcript(self, transcript: str, filename: str = '') -> Dict:
        """Complete processing: format transcript + tags + summary + deletion flag"""
        if not transcript:
            return {
                'claude_tags': {'life_domain': '', 'focus_area': '', 'content_nature': '', 'energy_state': '', 'explanation': ''},
                'summary': '',
                'deletion_analysis': {'should_delete': False, 'confidence': 'low', 'reason': 'Empty transcript'},
                'formatted_transcript': '',
                'filename_info': filename
            }
        
        logger.info("Processing transcript with Claude...")
        
        # Format transcript for readability
        formatted_transcript = self.format_transcript_for_readability(transcript)
        
        # Generate tags (using original transcript for accuracy)
        claude_tags = self.generate_claude_tags(transcript)
        
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