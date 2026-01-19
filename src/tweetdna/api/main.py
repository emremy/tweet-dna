"""FastAPI application for TweetDNA local API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tweetdna.config import get_config
from tweetdna.importer import ExtensionImporter
from tweetdna.providers.factory import get_provider
from tweetdna.services import GeneratorService, ProfilerService, ReviewerService
from tweetdna.storage import Database, Repository


# Request/Response models
class ImportExtensionRequest(BaseModel):
    path: str


class ImportExtensionResponse(BaseModel):
    imported: int
    skipped_invalid: int
    skipped_duplicate: int
    total: int


class ProfileRequest(BaseModel):
    sample: int = 300
    force: bool = False


class ProfileResponse(BaseModel):
    persona_version: int


class GenerateTweetRequest(BaseModel):
    topic: str
    n: int = 10
    spice: str = "medium"
    use_examples: bool = True
    max_chars: int = 280


class GenerateThreadRequest(BaseModel):
    topic: str
    tweets: int = 8
    spice: str = "low"
    draft: bool = True


class GenerateResponse(BaseModel):
    generation_ids: List[str]


class ReviewRequest(BaseModel):
    last: int = 10
    auto_refine: bool = True


class ReviewResponse(BaseModel):
    reviewed: int


class PersonaResponse(BaseModel):
    version: int
    persona: Dict[str, Any]


# Application state
class AppState:
    def __init__(self):
        self.config = get_config()
        self.db = Database(self.config.db_path)
        self.db.connect()
        self.db.initialize()
        self.repo = Repository(self.db)

    def close(self):
        self.db.close()


state: Optional[AppState] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global state
    state = AppState()
    yield
    if state:
        state.close()


app = FastAPI(
    title="TweetDNA API",
    description="Local API for Twitter persona profiling and tweet generation. No X API required.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_state() -> AppState:
    """Get application state."""
    if state is None:
        raise HTTPException(status_code=500, detail="Application not initialized")
    return state


@app.post("/import/extension", response_model=ImportExtensionResponse)
async def import_extension(request: ImportExtensionRequest) -> ImportExtensionResponse:
    """Import tweets from browser extension export file."""
    s = get_state()
    
    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {request.path}")
    
    importer = ExtensionImporter(repository=s.repo)
    
    try:
        imported, skipped_invalid, skipped_duplicate = importer.import_file(path)
        total = s.repo.get_tweet_count()
        
        return ImportExtensionResponse(
            imported=imported,
            skipped_invalid=skipped_invalid,
            skipped_duplicate=skipped_duplicate,
            total=total,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/profile", response_model=ProfileResponse)
async def build_profile(request: ProfileRequest) -> ProfileResponse:
    """Build or refresh persona from stored tweets."""
    s = get_state()
    provider = get_provider(s.config, role="profile")
    profiler = ProfilerService(repository=s.repo, provider=provider)
    
    try:
        persona = profiler.build_persona(
            sample_size=request.sample,
            force=request.force,
        )
        return ProfileResponse(persona_version=persona.version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate/tweet", response_model=GenerateResponse)
async def generate_tweets(request: GenerateTweetRequest) -> GenerateResponse:
    """Generate tweet drafts."""
    s = get_state()
    provider = get_provider(s.config, role="generate")
    generator = GeneratorService(repository=s.repo, provider=provider)
    
    try:
        drafts = generator.generate_tweets(
            topic=request.topic,
            n=request.n,
            spice=request.spice,  # type: ignore
            max_chars=request.max_chars,
            use_examples=request.use_examples,
        )
        return GenerateResponse(generation_ids=[str(d.id) for d in drafts])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/generate/thread", response_model=GenerateResponse)
async def generate_thread(request: GenerateThreadRequest) -> GenerateResponse:
    """Generate a thread."""
    s = get_state()
    provider = get_provider(s.config, role="generate")
    generator = GeneratorService(repository=s.repo, provider=provider)
    
    try:
        drafts = generator.generate_thread(
            topic=request.topic,
            tweet_count=request.tweets,
            spice=request.spice,  # type: ignore
            full_draft=request.draft,
        )
        return GenerateResponse(generation_ids=[str(d.id) for d in drafts])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/review", response_model=ReviewResponse)
async def review_drafts(request: ReviewRequest) -> ReviewResponse:
    """Review recent drafts for persona alignment."""
    s = get_state()
    provider = get_provider(s.config, role="review")
    reviewer = ReviewerService(repository=s.repo, provider=provider)
    
    try:
        results = reviewer.review_drafts(
            last_n=request.last,
            auto_refine=request.auto_refine,
        )
        return ReviewResponse(reviewed=len(results))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/persona/latest", response_model=PersonaResponse)
async def get_latest_persona() -> PersonaResponse:
    """Get the most recent persona."""
    s = get_state()
    persona = s.repo.get_latest_persona()
    
    if persona is None:
        raise HTTPException(status_code=404, detail="No persona found")
    
    return PersonaResponse(
        version=persona.version,
        persona=persona.model_dump(),
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
