# TweetDNA

Local-first Twitter persona profiling and tweet generation.

**No X API required.** Tweet data is imported from browser extension exports.

---

## Features

- 🧬 **Persona Profiling** — Extracts your unique writing style from your tweets
- ✍️ **Tweet Generation** — Creates tweets that sound like you
- 🧵 **Thread Generation** — Builds engaging multi-tweet threads
- 💬 **Reply Generation** — Crafts replies with customizable tone/emotion
- ✅ **Draft Review** — Scores and refines content for persona alignment
- 🔒 **Privacy-First** — Your tweet history stays local; only persona is sent to LLM
- 🌐 **Extension-First** — No API keys for Twitter; import from browser extension
- 📈 **Algorithm-Aware** — Optimizes content for X's ranking signals (replies, dwell time, shares)

---

## Quick Start

### 1. Install

```bash
cd twitter-algo
pip install -e .
```

### 2. Configure

Copy `env.example` to `.env` and add your OpenAI API key:

```bash
cp env.example .env
```

```env
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Export tweets from browser extension

1. Install the TweetDNA browser extension (in `extension/` folder)
2. Navigate to your Twitter/X profile
3. Click "Capture" then "Start Export"
4. Download the `.jsonl` file

### 4. Import tweets

```bash
tweetdna import extension --path ./your_tweets.jsonl
```

### 5. Build persona (one-time)

```bash
tweetdna profile --sample 300
```

This sends your tweets to the LLM **once** to extract your writing style.

### 6. Generate content

```bash
# Generate tweets
tweetdna generate tweet --topic "productivity tips" --n 5

# Generate threads
tweetdna generate thread --topic "career lessons" --tweets 5 --draft

# Generate replies
tweetdna generate reply --to "Just shipped my first app!" --tone supportive
```

---

## CLI Commands

### Import

```bash
tweetdna import extension --path ./export.jsonl           # Import tweets
tweetdna import extension --path ./export.jsonl --validate # Validate only
```

### Profile

```bash
tweetdna profile                    # Build persona from stored tweets
tweetdna profile --sample 500       # Use more tweets for profiling
tweetdna profile --force            # Rebuild even if persona exists
```

### Generate Tweet

```bash
tweetdna generate tweet --topic "AI tools" --n 5
```

| Option | Default | Description |
|--------|---------|-------------|
| `--topic` | Required | Topic or prompt for generation |
| `--n` | 5 | Number of drafts to generate |
| `--spice` | medium | Spice level: `low`, `medium`, `high` |
| `--min-chars` | 0 | Minimum characters (0 = no minimum) |
| `--max-chars` | 280 | Maximum characters |
| `--use-examples` | false | Include similar historical tweets |

**Algorithm optimization:** Tweets are automatically optimized for X's ranking signals. The output includes `suppression_risk` and `expected_engagement` metadata.

### Generate Thread

```bash
tweetdna generate thread --topic "Building in public" --tweets 5 --draft
```

| Option | Default | Description |
|--------|---------|-------------|
| `--topic` | Required | Thread topic |
| `--tweets` | 5 | Number of tweets in thread |
| `--spice` | medium | Spice level |
| `--draft` | false | Generate full drafts (vs outline) |
| `--min-chars` | 0 | Minimum characters per tweet |
| `--max-chars` | 280 | Maximum characters per tweet |

**Algorithm optimization:**
- First tweet (hook) is optimized to stand alone in the feed
- Each tweet validated for unique value (no filler/padding)
- May return fewer tweets if content density is insufficient
- Output includes `hook_strength` and `density_validated` metadata

### Generate Reply

```bash
tweetdna generate reply --to "Original tweet text here" --tone playful
```

| Option | Default | Description |
|--------|---------|-------------|
| `--to`, `-t` | Required | The tweet you're replying to |
| `--tone` | neutral | Reply tone (see below) |
| `--n` | 3 | Number of reply drafts |
| `--min-chars` | 0 | Minimum characters |
| `--max-chars` | 280 | Maximum characters |
| `--context`, `-c` | None | Additional context |

**Available tones:**

| Tone | Description |
|------|-------------|
| `neutral` | Balanced, conversational |
| `supportive` | Encouraging, agreeing, positive |
| `curious` | Interested, wanting to learn more |
| `playful` | Teasing, witty, light humor |
| `sarcastic` | Dry humor, ironic, deadpan |
| `critical` | Respectfully disagreeing |
| `angry` | Frustrated, calling out (within persona) |
| `excited` | Enthusiastic, hyped |
| `thoughtful` | Adding nuance, reflective |

**Context examples:**

```bash
# Who posted it
--context "Posted by Elon Musk"

# Thread context
--context "Last tweet in a thread about burnout"

# Relationship
--context "Close friend I've known for years"

# Situation
--context "Tweet is going viral with 50k quote tweets"
```

**Algorithm optimization:**
- Replies avoid low-effort patterns (generic praise, emoji-only, "this", "same")
- Each reply adds distinct value to the conversation
- Output includes `conversation_value` and `reply_intent` metadata
- Replies are weighted heavily in X's ranking system

### Review

```bash
tweetdna review                      # Review last 5 drafts
tweetdna review --last 10            # Review last 10 drafts
tweetdna review --all                # Review all drafts
tweetdna review --auto-refine        # Auto-generate improved versions
```

**Alignment scores:**

| Score | Meaning |
|-------|---------|
| 80-100 | ✅ Great match to persona |
| 60-79 | ⚠️ Okay, could be closer |
| 0-59 | ❌ Doesn't sound like you |

**Algorithm alignment (new):**

Reviews now include algorithm-specific scoring:

| Metric | Description |
|--------|-------------|
| `algorithm_alignment_score` | 0-100, how well optimized for ranking |
| `suppression_risk_score` | 0-100, likelihood of demotion (lower is better) |
| `repetition_risk` | low/medium/high |
| `conversation_value` | low/medium/high |
| `persona_algorithm_conflicts` | Any conflicts between style and algorithm |

Auto-refine triggers on: alignment < 80 OR suppression_risk > 50

### API Server

```bash
tweetdna api                         # Start on localhost:8765
tweetdna api --host 0.0.0.0 --port 8000
```

---

## Browser Extension

The extension captures tweet data from X/Twitter network responses.

### Installation

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension/` folder

### Usage

1. Go to any X/Twitter profile
2. Click extension icon
3. Enter username and click "Capture"
4. Click "Start Export" and wait
5. Click "Download JSONL"
6. Import with `tweetdna import extension --path file.jsonl`

---

## Extension Export Format

The browser extension exports tweets in JSONL format (one JSON per line):

```json
{
  "id": "1234567890",
  "text": "Your tweet text here",
  "created_at": "2025-01-15T10:30:00.000Z",
  "url": "https://x.com/username/status/1234567890",
  "source": "extension_network",
  "metrics": {
    "likes": 42,
    "retweets": 5,
    "replies": 3,
    "views": 1200
  },
  "is_reply": false,
  "is_quote": false,
  "lang": "en"
}
```

---

## Configuration

All settings via environment variables (`.env` file):

```env
# Database
TWEETDNA_DB_PATH=./data/tweetdna.sqlite
TWEETDNA_LOG_LEVEL=INFO

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Model Selection (optional - uses defaults if not set)
LLM_MODEL_PROFILE=gpt-4o           # Best for profiling
LLM_MODEL_GENERATE=gpt-4o-mini     # Fast for generation
LLM_MODEL_REVIEW=gpt-4o-mini       # Fast for review

# Local LLM (optional - for Ollama)
LOCAL_LLM_BASE_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=llama3
```

---

## How It Works

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Browser Ext    │────▶│    Import       │────▶│    SQLite DB    │
│  (JSONL export) │     │  (dedupe)       │     │  (local storage)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Profile      │────▶│    Persona      │────▶│    Generate     │
│  (one-time LLM) │     │  (JSON ~2KB)    │     │  (persona only) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┘
                        ▼
                ┌─────────────────┐
                │    Review       │
                │  (score/refine) │
                └─────────────────┘
```

### Key Principles

**Extension-first data pipeline:**
- No X API or SDK dependencies
- All tweet data comes from browser extension exports
- Works completely offline after import

**Privacy-preserving generation:**
- Profile extracts a compact persona once (~2KB JSON)
- Generation uses only persona + optional 3-5 examples
- Your full tweet history is never sent on every request

**Natural Twitter style:**
- Engagement hooks built into prompts
- Replies don't end with questions
- Avoids corporate/marketing language
- Matches real Twitter posting patterns

**X Algorithm Alignment:**
- Optimizes for ranking signals (replies, dwell time, shares, follows)
- Avoids suppression triggers (engagement bait, excessive hashtags, spam patterns)
- Thread density validation ensures quality over quantity
- Reply generation avoids low-effort patterns (generic praise, emoji-only)

---

## X Algorithm Alignment

TweetDNA includes algorithm-aware optimization based on the official X recommendation system. This helps generate content that performs well in the For You feed.

### How It Works

The generation and review systems understand X's ranking signals:

**Positive signals (algorithm rewards):**
- Reply-worthy content that sparks conversation
- Dwell time (content worth reading fully)
- Quote-worthy content others want to expand on
- Share-worthy content people send via DM
- Follow-worthy content that builds audience

**Suppression triggers (algorithm penalizes):**
- Engagement bait ("like if...", "RT for...", "follow for follow")
- Excessive hashtags (more than 2-3)
- Excessive @mentions
- Low-effort/empty content
- Spam-like repetition

### Algorithm Metadata in Outputs

Generated drafts now include algorithm alignment metadata:

```python
draft.expected_engagement    # "reply" | "like" | "repost" | "mixed"
draft.suppression_risk       # "low" | "medium" | "high"
draft.conversation_value     # "low" | "medium" | "high"
draft.algorithm_alignment_notes  # Brief explanation
```

Review results include additional scoring:

```python
result.algorithm_alignment_score  # 0-100
result.suppression_risk_score     # 0-100 (lower is better)
result.repetition_risk            # "low" | "medium" | "high"
result.persona_algorithm_conflicts  # List of resolved conflicts
```

### Quick Suppression Check

The reviewer includes a deterministic check (no LLM needed):

```python
from tweetdna.services import ReviewerService

reviewer = ReviewerService(repo, provider)
risk = reviewer.check_suppression_risk("Like if you agree! #blessed")
# {'risk_level': 'medium', 'patterns_found': ['engagement_bait:like if'], 'recommendation': 'review'}
```

---

## Project Structure

```
twitter-algo/
├── extension/              # Browser extension
│   ├── manifest.json
│   └── src/
│       ├── background.js   # Network capture
│       ├── content.js      # Page injection
│       ├── injected.js     # Export logic
│       ├── normalize.js    # Data normalization
│       ├── popup.html      # UI
│       └── popup.js        # UI logic
├── src/tweetdna/           # Python package
│   ├── cli.py              # Typer CLI
│   ├── config.py           # Environment config
│   ├── schemas/            # Pydantic models
│   │   ├── persona.py      # Persona schema
│   │   └── generation.py   # Draft/Review/Reply schemas
│   ├── storage/            # SQLite layer
│   │   ├── database.py     # Connection management
│   │   └── repository.py   # CRUD operations
│   ├── importer/           # Data import
│   │   └── extension.py    # Extension export importer
│   ├── providers/          # LLM providers
│   │   ├── base.py         # Abstract interface
│   │   ├── openai.py       # OpenAI implementation
│   │   ├── local.py        # Ollama-compatible
│   │   └── factory.py      # Provider factory
│   ├── prompts/            # Prompt templates
│   │   └── templates.py    # Profile/Generate/Reply/Review
│   ├── services/           # Business logic
│   │   ├── profiler.py     # Persona building
│   │   ├── generator.py    # Tweet/thread/reply generation
│   │   └── reviewer.py     # Alignment scoring
│   └── api/                # FastAPI app
│       └── main.py         # HTTP endpoints
├── data/                   # SQLite database (gitignored)
├── docs/                   # Documentation
├── env.example             # Environment template
├── pyproject.toml          # Package config
├── requirements.txt        # Dependencies
└── README.md
```

---

## HTTP API

Start the server:

```bash
tweetdna api --host 127.0.0.1 --port 8765
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/import/extension` | Import extension export |
| POST | `/profile` | Build persona |
| POST | `/generate/tweet` | Generate tweets |
| POST | `/generate/thread` | Generate threads |
| POST | `/generate/reply` | Generate replies |
| POST | `/review` | Review drafts |
| GET | `/persona/latest` | Get current persona |
| GET | `/health` | Health check |

### Example: Generate Tweet

```bash
curl -X POST http://localhost:8765/generate/tweet \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "productivity tips",
    "n": 5,
    "spice": "medium"
  }'
```

---

## Troubleshooting

### "No persona found"

Run profiling first:
```bash
tweetdna profile --sample 300
```

### "No tweets in database"

Import tweets first:
```bash
tweetdna import extension --path ./your_export.jsonl
```

### Extension not capturing

1. Make sure you're on `x.com` (not `twitter.com`)
2. Refresh the page after installing extension
3. Scroll down on the profile to trigger network requests

### API key issues

Check your `.env` file:
```bash
cat .env | grep OPENAI
```

---

## License

MIT License - See LICENSE file for details.
