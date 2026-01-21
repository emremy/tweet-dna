"""Prompt templates for persona profiling, generation, and review."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from tweetdna.schemas import Persona, SpiceLevel

# =============================================================================
# X ALGORITHM CONSTRAINTS
# Derived from x-official-repo/ - these reflect the official ranking signals
# =============================================================================

# Engagement types the algorithm predicts (from phoenix_scorer.rs)
# Positive signals that boost ranking
ALGORITHM_POSITIVE_SIGNALS = {
    "favorite": "Likes indicate content resonance",
    "reply": "Replies signal conversation value - HIGHLY WEIGHTED",
    "repost": "Reposts indicate share-worthy content",
    "quote": "Quote tweets show engagement worth expanding on",
    "click": "Clicks show curiosity and interest",
    "profile_click": "Profile visits indicate author interest",
    "video_quality_view": "Video completion signals quality content",
    "share": "Shares to DM/copy link show high value",
    "dwell": "Time spent reading indicates substance",
    "follow_author": "Follow signals strong interest in creator",
}

# Negative signals that suppress ranking (from weighted_scorer.rs)
ALGORITHM_NEGATIVE_SIGNALS = {
    "not_interested": "User marked as not interested",
    "block_author": "Author blocked - severe penalty",
    "mute_author": "Author muted - significant penalty",
    "report": "Content reported - highest penalty",
}

# Content patterns that trigger suppression (derived from filters/)
SUPPRESSION_TRIGGERS = [
    "Excessive hashtags (more than 2-3)",
    "Excessive mentions/tagging",
    "Repetitive/duplicate content patterns",
    "Spam-like link density",
    "Engagement bait phrases ('like if you agree', 'RT for', 'follow for follow')",
    "Empty/low-effort content (single emoji, 'this', 'same')",
    "Inflammatory content designed purely to provoke",
    "Muted keyword patterns",
    "Previously seen/stale content",
    "Question-heavy content (questions look like engagement bait and cause shadowban risk)",
    "Repetitive question templates ('what do you think?', 'anyone else?', 'am I the only one?')",
]

# Reply-specific demotion patterns (from conversation handling)
REPLY_DEMOTION_PATTERNS = [
    "Generic praise without substance ('great point!', 'so true!')",
    "Emoji-only replies",
    "Single word responses ('this', 'same', 'facts')",
    "Self-promotional replies",
    "Off-topic hijacking",
    "Engagement farming ('follow me back')",
    "Repetitive reply templates",
]

# Thread-specific quality signals (from dedup_conversation_filter.rs)
THREAD_QUALITY_SIGNALS = [
    "First tweet must stand alone as a hook",
    "Each subsequent tweet must add unique value",
    "No filler or padding content",
    "Clear progression/narrative arc",
    "Conversation deduplication favors highest-scored branch",
]

# Algorithm constraint block for prompts
ALGORITHM_CONSTRAINTS = """
X ALGORITHM ALIGNMENT (critical for visibility):
The X algorithm uses ML to predict engagement. Optimize for:

BOOST SIGNALS (algorithm rewards these):
- Reply-worthy content: tweets that spark genuine conversation
- Dwell time: content worth reading fully, not skimming
- Quote-worthy: content others want to add their take to
- Share-worthy: content people send to friends via DM
- Follow-worthy: content that makes readers want more from you

AVOID THESE (algorithm penalizes/suppresses):
- Engagement bait: "like if...", "RT for...", "follow for follow"
- Excessive hashtags (max 1-2, ideally 0)
- Excessive @mentions (feels spammy)
- Repetitive content patterns
- Empty/low-effort posts
- Inflammatory rage-bait designed only to provoke
- Generic filler phrases
- QUESTIONS: Avoid ending tweets with questions - they trigger shadowban risk and look like engagement bait

CONVERSATION VALUE (replies are weighted heavily):
- Content that invites thoughtful replies outperforms like-only content
- Specific, debatable takes perform better than vague statements
- Make STATEMENTS, not questions - strong opinions get more genuine replies than asking questions

CRITICAL - NO QUESTIONS:
- Do NOT end tweets with questions
- Do NOT use rhetorical questions
- Do NOT use "what do you think?", "anyone else?", "am I the only one?"
- Questions make all tweets look the same and risk shadowban
- Instead: make bold statements that INVITE disagreement or agreement
"""

# Author diversity note (from author_diversity_scorer.rs)
DIVERSITY_NOTE = """
DIVERSITY AWARENESS:
- The algorithm attenuates repeated content from the same author
- Vary your approaches, hooks, and angles across tweets
- Don't use the same opener/structure repeatedly
- NEVER use the same question template across tweets (causes shadowban)
- Each tweet should have a DIFFERENT structure - no patterns
"""

# Strict formatting and anti-pattern rules
STRICT_RULES = """
STRICT RULES (MUST FOLLOW - NO EXCEPTIONS):

1. LOWERCASE ONLY:
   - All tweets must be lowercase
   - No capitalization except for proper nouns/acronyms when necessary
   - Even at the start of sentences: use lowercase

2. NO OPINION-LABELING OPENERS (BANNED - never use these):
   - "unpopular opinion"
   - "hot take"
   - "just saying"
   - "controversial take"
   - "hear me out"
   - "most people miss this"
   - "most people don't realize"
   - "most people won't tell you"
   - "i'll probably get hate for this but"
   - "not sure if this is controversial but"
   - "this might be a hot take but"
   - Any phrase that labels your opinion before stating it
   - Any "most people..." opener that implies insider knowledge

3. NO ENGAGEMENT BAIT (BANNED):
   - "like if you agree"
   - "retweet if"
   - "follow for more"
   - "thoughts?"
   - "agree or disagree?"
   - "am i the only one"
   - "who else"
   - Any phrasing designed to beg for interaction

4. NO REPEATED STRUCTURES:
   - Avoid repeating sentence structures used in previous outputs
   - Each tweet must have a UNIQUE sentence pattern
   - Don't start multiple tweets the same way
   - Vary your rhythm: short, long, medium, fragment
   - If you used "okay but" in one tweet, don't use it in the next

5. NO FORMULAIC PATTERNS:
   - Don't use the same hook twice
   - Don't follow a template
   - Each output should feel like a different person wrote it
   - Surprise yourself with the structure
"""

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

HUMAN SPEECH PATTERNS (use these to sound real):
- Fillers: "oh", "wait", "hm", "hmm", "uh", "ah", "like", "okay so", "ngl"
- Reactions: "lol", "lmao", "bruh", "damn", "yikes", "oof", "wow okay"
- Trailing off: "idk...", "but yeah...", "anyway...", "so...", "i mean..."
- Mid-thought shifts: "wait no", "actually", "hold on", "okay but", "nvm"
- Casual emphasis: "literally", "lowkey", "highkey", "fr", "tbh", "imo"

ABBREVIATIONS & INTERNET SPEAK (mix in naturally):
- "rn" (right now), "ngl" (not gonna lie), "tbh" (to be honest)
- "imo" (in my opinion), "idk" (I don't know), "fr" (for real)
- "w/" (with), "b/c" or "bc" (because), "rly" (really)
- "prob" (probably), "def" (definitely), "obv" (obviously)
- "ppl" (people), "smth" (something), "sth" (something)

EMOTIONAL AUTHENTICITY (show feeling, not just state it):
- Frustration: "why is this so hard", "i stg", "this is killing me"
- Excitement: "oh my god", "wait this is actually good", "holy shit"
- Realization: "oh. OH.", "wait...", "hm. interesting."
- Uncertainty: "idk man", "maybe?", "not sure but..."
- Humor: self-deprecating jokes, absurdist takes, deadpan delivery

WHAT MAKES IT FEEL HUMAN (not AI):
- Imperfect grammar on purpose
- Thoughts that trail off or restart
- Personal reactions and emotions woven in
- Specific weird details instead of generic statements
- Typos left in occasionally (not forced, just natural)
- Run-on sentences when excited
- One-word reactions: "brutal." "fascinating." "pain."

EXAMPLES - AI vs HUMAN:

❌ AI-SOUNDING (avoid this - too polished, capitalized, generic):
"Productivity is about prioritizing what matters most. Focus on high-impact tasks."
"I've learned that consistency is key to success in any endeavor."
"Unpopular opinion: mornings are actually the best time to work."
"Here's an interesting observation about the tech industry."

✅ HUMAN-SOUNDING (do this - lowercase, messy, emotional, specific):
"okay but why did it take me 30 years to realize you can just... not reply to emails immediately"
"ngl i mass mass mass resistance everything about morning routines but this one thing actually worked"
"oh. OH. wait. i think i finally get why everyone's been saying this"
"been staring at this code for 3 hours and i just realized i forgot a semicolon. pain."
"not me thinking i was productive today when literally all i did was reorganize my notion lmao"
"the thing about burnout is nobody warns you it feels like boredom at first"
"hm. starting to think maybe the problem isn't the tools it's me"
"""

# Engagement rules - ALWAYS APPLY
ENGAGEMENT_RULES = """
ENGAGEMENT (every tweet MUST do this):
- Hook in first 5-7 words: make them stop scrolling
- Create curiosity gap: hint at something without revealing all
- Trigger emotion: surprise, relatability, controversy, humor, or "wait what?"
- Make it quotable: something people want to screenshot or reply to
- End with energy: punchline, bold statement, or mic-drop moment (NOT a question)
- Pattern interrupt: say something unexpected or flip a common take

GOOD HOOKS (use these - lowercase, no opinion labels):
- Personal stories: "learned this the hard way..." "nobody told me..."
- Bold claims: "this changed everything for me..." "the trick is..."
- Direct observations: "the thing about X is..." "most people miss this..."
- Curiosity gaps: "here's what happens when..." "the real reason..."
- Relatable moments: "that moment when..." "the worst part about..."
- Realizations: "oh. just realized..." "wait..." "hm."

BANNED HOOKS (never use these):
- "unpopular opinion" or any variation
- "hot take"
- "controversial take"
- "just saying"
- "hear me out"
- "most people miss this" or any "most people..." opener
- "most people don't realize"
- "most people won't tell you"
- "everyone's wrong about" (too formulaic)

NEVER USE THESE (engagement bait / question patterns):
- "what do you think?"
- "anyone else?"
- "am I the only one who...?"
- "thoughts?"
- "agree or disagree?"
- "who else"
- "like if"
- "retweet if"
- Any question at the end of a tweet
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
    target_engagement: str = "reply",  # reply|like|repost|mixed
) -> str:
    """
    Build the tweet generation prompt.
    
    IMPORTANT: This prompt only receives the persona JSON (few KB),
    NOT the full tweet history. Examples are optional and limited to 3-5.
    
    Algorithm-aware: Optimizes for X ranking signals.
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

    # Target engagement guidance
    engagement_guidance = {
        "reply": "Optimize for REPLIES: pose debatable takes, invite disagreement through bold statements",
        "like": "Optimize for LIKES: be relatable, quotable, express shared experiences",
        "repost": "Optimize for REPOSTS: be informative, provide value worth sharing",
        "mixed": "Balanced engagement: aim for a mix of replies, likes, and reposts",
    }
    engagement_instruction = engagement_guidance.get(target_engagement, engagement_guidance["mixed"])

    prompt = f"""Generate {n} tweet drafts that grab attention and keep people reading.

PERSONA:
{persona_json}

TOPIC: {topic}
SPICE LEVEL: {spice}
{char_constraint}
TARGET ENGAGEMENT: {engagement_instruction}
{examples_block}

{STRICT_RULES}

{TWITTER_STYLE}

{ENGAGEMENT_RULES}

{ALGORITHM_CONSTRAINTS}

{DIVERSITY_NOTE}

{GUARDRAILS}

Output a JSON object with this structure:
{{
  "drafts": [
    {{
      "text": "tweet text here (MUST be lowercase)",
      "tags": ["tag1", "tag2"],
      "hook_type": "what attention hook was used",
      "rationale": "one line explaining the approach",
      "confidence": 0.0-1.0,
      "expected_engagement": "reply|like|repost|mixed",
      "suppression_risk": "low|medium|high",
      "algorithm_alignment_notes": "brief note on how this aligns with ranking signals"
    }}
  ]
}}

Generate exactly {n} drafts. Each MUST:
1. Be entirely lowercase
2. Hook attention in the first few words
3. Avoid all suppression triggers and banned phrases
4. Have a UNIQUE structure (no repeated patterns across drafts)
5. NOT start with opinion labels like "unpopular opinion", "hot take", or "most people miss this"
JSON only:"""

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
    Algorithm-aware: Includes density validation and hook optimization.
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

    # Thread-specific algorithm constraints
    thread_algorithm_rules = """
THREAD ALGORITHM RULES (critical):
The X algorithm treats threads as linked posts where each must earn its place.

HOOK OPTIMIZATION (first tweet):
- Must stand COMPLETELY ALONE - people see it without knowing it's a thread
- Should create curiosity gap that demands the rest be read
- Avoid "thread:" or "🧵" - let content speak for itself
- First 7 words determine if people click through

DENSITY VALIDATION (every tweet):
- Each tweet must contain a UNIQUE point, example, or insight
- No filler phrases ("let me explain", "here's the thing", "stay with me")
- No repetition of points across tweets
- If a tweet could be deleted without losing info, it shouldn't exist

THREAD PENALTIES TO AVOID:
- Padding to reach arbitrary tweet count
- Repeating the same point in different words
- Empty engagement bait ("like and RT for more threads")
- Weak closers ("follow for more" / "that's it")

DENSITY CHECK: If you cannot fill {tweet_count} tweets with UNIQUE, VALUABLE points,
output fewer tweets rather than pad with filler. Quality > Quantity.
"""

    prompt = f"""Generate a Twitter thread that grabs attention and keeps readers til the end.

PERSONA:
{persona_json}

TOPIC: {topic}
SPICE LEVEL: {spice}
TWEETS IN THREAD: {tweet_count}

{output_instruction}

{STRICT_RULES}

{thread_algorithm_rules}

{TWITTER_STYLE}

{ENGAGEMENT_RULES}

{ALGORITHM_CONSTRAINTS}

{GUARDRAILS}

Output a JSON object:
{{
  "thread": [
    {{
      "position": 1,
      "text": "tweet text or outline point (MUST be lowercase)",
      "purpose": "hook|body|closer",
      "hook_type": "what keeps readers engaged here",
      "unique_value": "what new info/insight this tweet adds",
      "density_score": "low|medium|high"
    }}
  ],
  "rationale": "brief thread strategy",
  "density_validated": true,
  "hook_strength": "weak|moderate|strong",
  "recommended_tweet_count": {tweet_count},
  "suppression_risks": ["list any potential issues"]
}}

Every tweet must earn the next click. If content is insufficient, recommend fewer tweets.

CRITICAL REQUIREMENTS:
1. All tweets MUST be lowercase
2. NO opinion labels ("unpopular opinion", "hot take", "most people miss this", etc.)
3. Each tweet must have a UNIQUE structure
4. NO engagement bait
JSON only:"""

    return prompt


def build_review_prompt(
    persona: Persona,
    draft_text: str,
    auto_refine: bool = False,
    draft_kind: str = "tweet",  # tweet|reply|thread
) -> str:
    """
    Build the review/refinement prompt.
    
    Scores persona alignment AND algorithm alignment.
    Includes suppression risk checks.
    """
    persona_json = persona.to_prompt_context()

    refine_instruction = ""
    if auto_refine:
        refine_instruction = """
If alignment score is below 80 OR suppression_risk_score is above 50, provide a revised version.
Revision must fix issues while maintaining persona voice.
"""

    # Kind-specific review criteria
    kind_criteria = {
        "tweet": """
TWEET-SPECIFIC CHECKS:
- Single atomic idea (not trying to cover too much)
- Hook in first 7 words
- No engagement bait patterns
- Appropriate hashtag count (0-2 max)
""",
        "reply": """
REPLY-SPECIFIC CHECKS:
- Adds distinct value (not just agreeing)
- Not generic praise ("great point!", "so true!")
- Not emoji-only or single word
- Responds to original content specifically
- Doesn't end with a question (replies ≠ conversation starters)
""",
        "thread": """
THREAD-SPECIFIC CHECKS:
- Hook stands alone without context
- Each tweet adds unique value
- No filler or padding
- Clear progression
- Strong closer (not "follow for more")
""",
    }
    
    kind_rules = kind_criteria.get(draft_kind, kind_criteria["tweet"])

    # Algorithm suppression patterns to check
    suppression_check = """
SUPPRESSION RISK ANALYSIS:
Check for these algorithm-penalized patterns:
- Engagement bait: "like if", "RT for", "follow for follow"
- Excessive hashtags (>2)
- Excessive mentions (@)
- Spam-like repetition
- Low-effort/empty content
- Inflammatory rage-bait
- Generic filler phrases

Score suppression_risk from 0-100 (higher = riskier, likely to be demoted).
"""

    # Persona conflict resolution
    conflict_resolution = """
PERSONA vs ALGORITHM CONFLICT RESOLUTION:
If the persona style would trigger algorithm suppression:
- Algorithm safety OVERRIDES persona style
- Note which persona rule conflicted
- Note which algorithm constraint overrode it
- Revised text must be algorithm-safe while preserving persona voice where possible
"""

    prompt = f"""Review this draft for persona alignment AND algorithm alignment.

PERSONA:
{persona_json}

DRAFT TO REVIEW:
{draft_text}

DRAFT TYPE: {draft_kind}

{kind_rules}

{suppression_check}

{conflict_resolution}

TASK:
1. Score persona alignment (0-100): voice, tone, formatting match
2. Score algorithm alignment (0-100): ranking signal optimization
3. Score suppression risk (0-100): likelihood of demotion (lower is better)
4. Assess repetition risk and conversation value
5. List violations and conflicts
6. Suggest improvements
{refine_instruction}

{GUARDRAILS}

Output a JSON object:
{{
  "alignment_score": 0-100,
  "algorithm_alignment_score": 0-100,
  "suppression_risk_score": 0-100,
  "repetition_risk": "low|medium|high",
  "conversation_value": "low|medium|high",
  "violations": ["list of persona violations"],
  "algorithm_issues": ["list of algorithm/suppression issues"],
  "persona_algorithm_conflicts": [
    {{
      "persona_rule": "which persona rule conflicted",
      "algorithm_constraint": "which algorithm rule overrode it",
      "resolution": "how it was resolved"
    }}
  ],
  "suggestions": ["list of improvements"],
  "revised_text": "revised version or null if not needed",
  "revision_reason": "why revision was needed or null"
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

HUMAN REPLY PATTERNS (use these):
- Quick reactions: "oh damn", "wait really", "lmaooo", "this hit different"
- Relating: "dude same", "literally me", "felt this", "been there"
- Adding on: "also", "and honestly", "plus", "oh and"
- Disagreeing humanly: "idk about that", "eh", "hmm not sure", "nah"
- Casual agreement: "fr fr", "exactly", "this tbh", "yep"
- Emotional: "oof", "pain", "mood", "crying", "screaming"
- Starting casual: "lol", "omg", "bruh", "okay but", "wait"
"""

# Algorithm-aware reply rules (from conversation handling in x-official-repo)
REPLY_ALGORITHM_RULES = """
REPLY ALGORITHM ALIGNMENT (replies are weighted heavily in ranking):
The X algorithm treats replies as first-class content. Well-crafted replies
can outrank original tweets in the algorithm.

WHAT MAKES REPLIES RANK WELL:
- Adds a DISTINCT angle the original didn't cover
- Introduces NEW information or sharper framing
- Sparks further conversation (but don't force questions)
- Gets engagement on the reply itself (likes, re-replies)
- Demonstrates genuine engagement with the content

REPLY PATTERNS THAT GET DEMOTED:
- Generic praise: "great point!", "love this!", "so true!"
- Emoji-only: "🔥", "💯", "👏👏👏"
- Empty agreement: "this", "same", "facts", "real"
- Self-promotion: "check out my...", "I wrote about this..."
- Engagement farming: "follow me back", "check my pinned"
- Off-topic hijacking: replies that ignore the original content
- Template replies: clearly copy-pasted responses

REPLY INTENT (pick one):
- agree_extend: agree AND add something new
- disagree_reason: disagree with specific reasoning
- add_context: provide relevant info they missed
- share_experience: relate a personal story/example
- challenge: push back on a specific point
- joke: humor that relates to their content
- react: genuine emotional response

A reply should pass this test: "Does this add value that wasn't in the original?"
If no, don't post it.
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
    intent: Optional[str] = None,  # agree_extend|disagree_reason|add_context|share_experience|challenge|joke|react
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
        intent: Optional reply intent to guide generation
    
    Algorithm-aware: Optimizes for conversation depth, avoids low-effort patterns.
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
    
    # Intent guidance
    intent_block = ""
    if intent:
        intent_block = f"\nREPLY INTENT: {intent} - craft replies with this specific approach\n"

    prompt = f"""Generate {n} reply drafts to this tweet, matching your persona's voice.

PERSONA:
{persona_json}

ORIGINAL TWEET (replying to this):
"{original_tweet}"
{context_block}{intent_block}
REPLY TONE: {tone} - {tone_desc}

{STRICT_RULES}
{char_constraint}

{TWITTER_STYLE}

{REPLY_STYLE}

{REPLY_ALGORITHM_RULES}

{GUARDRAILS}

Output a JSON object:
{{
  "replies": [
    {{
      "text": "your reply text here (MUST be lowercase)",
      "tone_executed": "how the tone was expressed",
      "intent": "agree_extend|disagree_reason|add_context|share_experience|challenge|joke|react",
      "approach": "agree|disagree|extend|react|challenge|joke",
      "value_added": "what new angle/info this reply contributes",
      "rationale": "why this reply works",
      "confidence": 0.0-1.0,
      "suppression_risk": "low|medium|high",
      "conversation_value": "low|medium|high"
    }}
  ],
  "original_tweet_analysis": {{
    "main_point": "what the original tweet is about",
    "engagement_opportunity": "where a reply can add value"
  }}
}}

CRITICAL CHECKS before outputting each reply:
1. Is it lowercase? (MUST be lowercase)
2. Does it add value not in the original? (if no, discard)
3. Is it generic praise or empty agreement? (if yes, discard)
4. Does it respond specifically to their content? (if no, revise)
5. Does it use a UNIQUE structure from other replies? (no repeated patterns)
6. Does it avoid engagement bait? (no "thoughts?", questions, etc.)

Generate exactly {n} replies. Each must feel like a natural response, NOT a standalone tweet.
Each must add DISTINCT VALUE. All lowercase. No engagement bait. JSON only:"""

    return prompt
