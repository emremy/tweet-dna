"""SQLite database management."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
-- Tweets table stores imported tweet data from extension exports
CREATE TABLE IF NOT EXISTS tweets (
    tweet_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT,
    source TEXT DEFAULT 'extension_network',
    lang TEXT,
    metrics_json TEXT,
    raw_json TEXT
);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at);

-- Index for source-based queries
CREATE INDEX IF NOT EXISTS idx_tweets_source ON tweets(source);

-- Persona versions table
CREATE TABLE IF NOT EXISTS persona_versions (
    version INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    persona_json TEXT NOT NULL
);

-- Generations table stores all generated drafts
CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    kind TEXT NOT NULL,
    topic TEXT NOT NULL,
    spice TEXT NOT NULL,
    persona_version INTEGER NOT NULL,
    text_json TEXT NOT NULL,
    tags_json TEXT,
    rationale TEXT,
    confidence REAL,
    provider TEXT,
    model TEXT,
    prompt_hash TEXT,
    FOREIGN KEY (persona_version) REFERENCES persona_versions(version)
);

-- Index for querying recent generations
CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at);

-- Reviews table stores review results
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    generation_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    alignment_score REAL NOT NULL,
    violations_json TEXT,
    suggestions_json TEXT,
    revised_text_json TEXT,
    FOREIGN KEY (generation_id) REFERENCES generations(id)
);

-- Index for querying reviews by generation
CREATE INDEX IF NOT EXISTS idx_reviews_generation_id ON reviews(generation_id);
"""

# Migration SQL for existing databases
MIGRATION_SQL = """
-- Add url column if it doesn't exist
ALTER TABLE tweets ADD COLUMN url TEXT;

-- Add source column if it doesn't exist  
ALTER TABLE tweets ADD COLUMN source TEXT DEFAULT 'extension_network';
"""


class Database:
    """SQLite database wrapper with connection management."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._connection is None:
            self._ensure_directory()
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def _run_migrations(self) -> None:
        """Run schema migrations for existing databases."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Check if tweets table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tweets'"
        )
        if cursor.fetchone() is None:
            return  # No migration needed, schema will be created fresh
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(tweets)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add missing columns
        if "url" not in columns:
            try:
                conn.execute("ALTER TABLE tweets ADD COLUMN url TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        if "source" not in columns:
            try:
                conn.execute("ALTER TABLE tweets ADD COLUMN source TEXT DEFAULT 'extension_network'")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        conn.commit()

    def initialize(self) -> None:
        """Create tables if they don't exist and run migrations."""
        conn = self.connect()
        self._run_migrations()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "Database":
        self.connect()
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
