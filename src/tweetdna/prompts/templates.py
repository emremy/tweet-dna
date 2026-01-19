"""Prompt templates for persona profiling, generation, and review."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from tweetdna.schemas import Persona, SpiceLevel

# Guardrails included in all prompts
GUARDRAILS = """
GUARDRAILS (always follow):
- No slurs, threats, or harassment
- No illegal instructions
- No doxxing or personal data
- Keep language consistent with persona constraints
- Respect safety mode if enabled
"""

# Style guidance for natural Twitter content
TWITTER_STYLE = """
CRITICAL STYLE RULES (follow these exactly):
- Write like a real person posting casually, NOT like marketing copy
- Use incomplete sentences, fragments, and natural speech patterns
- lowercase starts are fine. so is skipping punctuation sometimes
- Sound like you're texting a friend or thinking out loud
- AVOID: corporate buzzwords, "excited to announce", formal structures
- AVOID: overly polished prose, essay-like flow, listicles with emojis
- Real tweets are messy, spontaneous, opinionated
- It's okay to be blunt, vague, or leave thoughts hanging...
- Match how people actually tweet: short, punchy, human
"""

# Engagement rules - ALWAYS APPLY
ENGAGEMENT_RULES = """
ENGAGEMENT (every tweet MUST do this):
- Hook in first 5-7 words: make them stop scrolling
- Create curiosity gap: hint at something without revealing all
- Trigger emotion: surprise, relatability, controversy, humor, or "wait what?"
- Make it quotable: something people want to screenshot or reply to
- End with energy: punchline, open question, or mic-drop moment
- Pattern interrupt: say something unexpected or flip a common take

ATTENTION HOOKS that work:
- Contrarian takes: "unpopular opinion..." "everyone's wrong about..."
- Personal stories: "learned this the hard way..." "nobody told me..."
- Bold claims: "this one thing changed..." "the secret is..."
- Direct callouts: "if you're still doing X..." "most people won't..."
- Curiosity gaps: "here's what happens when..." "the real reason..."
- Relatable pain: "why does no one talk about..." "am I the only one..."
"""

PERSONA_SCHEMA_HINT = """
Output must be a valid JSON object matching this structure:
{
  "version": 1,
  "display_name": "string",
  "voice_rules": {
    "sentence_length": "short|medium|long",
    "hook_styles": ["string array"],
    "humor_style": ["string array"],
    "jargon_level": "low|medium|high",
    "directness": "low|medium|high"
  },
  "tone": {
    "spice_default": "low|medium|high",
    "safe_mode": true
  },
  "topics": [{"name": "string", "weight": 0.0-1.0}],
  "formatting": {
    "emoji_rate": "none|low|medium|high",
    "punctuation_style": "minimal|standard|expressive",
    "line_breaks": "none|rare|frequent"
  },
  "constraints": {
    "no_slurs": true,
    "no_threats": true,
    "max_chars": 280
  },
  "examples": {
    "signature_patterns": ["string array describing writing patterns"]
  }
}
"""


def build_profile_prompt(
    tweets: List[Dict[str, Any]],
    bio: Optional[str] = None,
    pinned_tweet: Optional[str] = None,
) -> str:
    """
    Build the persona profiling prompt.
    
    This prompt is sent ONCE during profiling to extract a reusable persona.
    The full tweet history is only sent during this step.
    """
    tweet_texts = [t.get("text", "") for t in tweets if t.get("text")]
    tweets_block = "\n---\n".join(tweet_texts[:400])  # Cap at 400 tweets

    context_block = ""
    if bio:
        context_block += f"Bio: {bio}\n"
    if pinned_tweet:
        context_block += f"Pinned tweet: {pinned_tweet}\n"

    prompt = f"""Analyze the following tweets and extract a detailed persona profile.

{context_block}
TWEETS:
{tweets_block}

TASK:
Extract a persona JSON that captures:
1. Voice rules: sentence length, hook styles, humor, jargon level, directness
2. Tone: default spice level, safety preferences
3. Topics: weighted list of main topics covered
4. Formatting: emoji usage, punctuation style, line breaks
5. Constraints: content restrictions
6. Examples: 2-5 signature writing patterns (not full tweets, just patterns)

{PERSONA_SCHEMA_HINT}

{GUARDRAILS}

Output JSON only, no explanation:"""

    return prompt


def build_generation_prompt(
    persona: Persona,
    topic: str,
    n: int = 5,
    spice: SpiceLevel = "medium",
    min_chars: int = 0,
    max_chars: int = 280,
    examples: Optional[List[str]] = None,
) -> str:
    """
    Build the tweet generation prompt.
    
    IMPORTANT: This prompt only receives the persona JSON (few KB),
    NOT the full tweet history. Examples are optional and limited to 3-5.
    """
    persona_json = persona.to_prompt_context()

    examples_block = ""
    if examples:
        examples_block = f"""
REFERENCE EXAMPLES (match this style):
{chr(10).join(f"- {ex}" for ex in examples[:5])}
"""

    # Build character constraint instruction
    char_constraint = f"MAX CHARACTERS: {max_chars}"
    if min_chars > 0:
        char_constraint = f"CHARACTER RANGE: {min_chars}-{max_chars} characters (tweets must be at least {min_chars} chars)"

    prompt = f"""Generate {n} tweet drafts that grab attention and keep people reading.

PERSONA:
{persona_json}

TOPIC: {topic}
SPICE LEVEL: {spice}
{char_constraint}
{examples_block}

{TWITTER_STYLE}

{ENGAGEMENT_RULES}

{GUARDRAILS}

Output a JSON object with this structure:
{{
  "drafts": [
    {{
      "text": "tweet text here",
      "tags": ["tag1", "tag2"],
      "hook_type": "what attention hook was used",
      "rationale": "one line explaining the approach",
      "confidence": 0.0-1.0
    }}
  ]
}}

Generate exactly {n} drafts. Each MUST hook attention in the first few words. JSON only:"""

    return prompt


def build_thread_prompt(
    persona: Persona,
    topic: str,
    tweet_count: int = 5,
    spice: SpiceLevel = "medium",
    full_draft: bool = False,
    min_chars: int = 0,
    max_chars: int = 280,
) -> str:
    """
    Build the thread generation prompt.
    
    Can generate either an outline or full thread drafts.
    """
    persona_json = persona.to_prompt_context()

    # Build character constraint string
    char_constraint = f"under {max_chars} characters"
    if min_chars > 0:
        char_constraint = f"between {min_chars}-{max_chars} characters"

    output_instruction = ""
    if full_draft:
        output_instruction = f"""
Generate {tweet_count} connected tweets forming a natural thread.
Each tweet must be {char_constraint}.
First tweet: MUST hook hard - make people stop scrolling and read the whole thread
Middle tweets: keep momentum, each adds value or builds tension
Last tweet: end with impact - punchline, insight, or open thought (NOT "follow for more")
"""
    else:
        output_instruction = f"""
Generate a {tweet_count}-part thread outline.
Each part describes what that tweet covers.
First part must hook attention. Last part must land with impact.
"""

    prompt = f"""Generate a Twitter thread that grabs attention and keeps readers til the end.

PERSONA:
{persona_json}

TOPIC: {topic}
SPICE LEVEL: {spice}
TWEETS IN THREAD: {tweet_count}

{output_instruction}

{TWITTER_STYLE}

{ENGAGEMENT_RULES}

{GUARDRAILS}

Output a JSON object:
{{
  "thread": [
    {{
      "position": 1,
      "text": "tweet text or outline point",
      "purpose": "hook|body|closer",
      "hook_type": "what keeps readers engaged here"
    }}
  ],
  "rationale": "brief thread strategy"
}}

Every tweet must earn the next click. JSON only:"""

    return prompt


def build_review_prompt(
    persona: Persona,
    draft_text: str,
    auto_refine: bool = False,
) -> str:
    """
    Build the review/refinement prompt.
    
    Scores persona alignment and optionally rewrites the draft.
    """
    persona_json = persona.to_prompt_context()

    refine_instruction = ""
    if auto_refine:
        refine_instruction = """
If alignment score is below 80, provide a revised version that better matches the persona.
"""

    prompt = f"""Review this draft against the persona.

PERSONA:
{persona_json}

DRAFT TO REVIEW:
{draft_text}

TASK:
1. Score alignment (0-100) based on voice, tone, and formatting match
2. List any violations of persona constraints
3. Suggest improvements
{refine_instruction}

{GUARDRAILS}

Output a JSON object:
{{
  "alignment_score": 0-100,
  "violations": ["list of violations if any"],
  "suggestions": ["list of suggestions"],
  "revised_text": "revised version or null if not needed"
}}

JSON only, no explanation:"""

    return prompt


# Reply-specific style rules
REPLY_STYLE = """
REPLY-SPECIFIC RULES (critical for natural replies):
- DO NOT end with a question (this is a reply, not starting a convo)
- DO NOT be preachy or lecture the original poster
- Respond directly to what they said - show you actually read it
- Match the energy of the original tweet
- Keep it conversational, like you're talking TO them
- It's okay to be brief - replies don't need to be essays
- Add value: agree+extend, disagree+why, share experience, or just react
- Avoid generic phrases like "great point!" or "totally agree!"
- Sound like a real person jumping into a conversation
"""

# Emotion/tone descriptions for replies
REPLY_TONE_DESCRIPTIONS = {
    "neutral": "balanced and conversational, neither too positive nor negative",
    "supportive": "encouraging, agreeing, building on their point positively",
    "curious": "genuinely interested, wanting to learn more (but don't ask questions at the end)",
    "playful": "teasing, witty, light humor - friendly banter",
    "sarcastic": "dry humor, ironic, deadpan - but not mean-spirited",
    "critical": "respectfully disagreeing, pushing back with reasoning",
    "angry": "frustrated, calling out BS - but staying within your persona's boundaries",
    "excited": "enthusiastic, hyped, energetic agreement or reaction",
    "thoughtful": "adding nuance, seeing another angle, reflective take",
}


def build_reply_prompt(
    persona: Persona,
    original_tweet: str,
    tone: str = "neutral",
    n: int = 3,
    min_chars: int = 0,
    max_chars: int = 280,
    context: Optional[str] = None,
) -> str:
    """
    Build a reply generation prompt.
    
    Args:
        persona: User's persona profile
        original_tweet: The tweet being replied to
        tone: Emotional tone for the reply (neutral, supportive, angry, etc.)
        n: Number of reply drafts to generate
        min_chars: Minimum characters per reply
        max_chars: Maximum characters per reply
        context: Optional additional context (e.g., who posted it, thread context)
    """
    persona_json = persona.to_prompt_context()
    
    # Get tone description
    tone_desc = REPLY_TONE_DESCRIPTIONS.get(tone, REPLY_TONE_DESCRIPTIONS["neutral"])
    
    # Build character constraint
    char_constraint = f"MAX CHARACTERS: {max_chars}"
    if min_chars > 0:
        char_constraint = f"CHARACTER RANGE: {min_chars}-{max_chars} characters"
    
    # Optional context block
    context_block = ""
    if context:
        context_block = f"\nADDITIONAL CONTEXT: {context}\n"

    prompt = f"""Generate {n} reply drafts to this tweet, matching your persona's voice.

PERSONA:
{persona_json}

ORIGINAL TWEET (replying to this):
"{original_tweet}"
{context_block}
REPLY TONE: {tone} - {tone_desc}
{char_constraint}

{TWITTER_STYLE}

{REPLY_STYLE}

{GUARDRAILS}

Output a JSON object:
{{
  "replies": [
    {{
      "text": "your reply text here",
      "tone_executed": "how the tone was expressed",
      "approach": "agree|disagree|extend|react|challenge|joke",
      "rationale": "why this reply works",
      "confidence": 0.0-1.0
    }}
  ]
}}

Generate exactly {n} replies. Each must feel like a natural response, NOT a standalone tweet. JSON only:"""

    return prompt
