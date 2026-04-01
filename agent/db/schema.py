"""SQLite schema and database initialization."""
import sqlite3
from agent.config import DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS character (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    reference_image_url TEXT,
    media_gen_id        TEXT,
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    thumbnail_url   TEXT,
    language        TEXT DEFAULT 'en',
    status          TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ARCHIVED')),
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_character (
    project_id   TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    character_id TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, character_id)
);

CREATE TABLE IF NOT EXISTS video (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    display_order   INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','PROCESSING','COMPLETED','FAILED')),
    vertical_url    TEXT,
    horizontal_url  TEXT,
    thumbnail_url   TEXT,
    duration        REAL,
    resolution      TEXT,
    youtube_id      TEXT,
    privacy         TEXT DEFAULT 'unlisted',
    tags            TEXT,
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_video_project ON video(project_id);

CREATE TABLE IF NOT EXISTS scene (
    id                  TEXT PRIMARY KEY,
    video_id            TEXT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    display_order       INTEGER DEFAULT 0,
    prompt              TEXT,
    character_names     TEXT,

    parent_scene_id     TEXT REFERENCES scene(id),
    chain_type          TEXT DEFAULT 'ROOT' CHECK(chain_type IN ('ROOT','CONTINUATION','INSERT')),

    vertical_image_url              TEXT,
    vertical_video_url              TEXT,
    vertical_upscale_url            TEXT,
    vertical_image_media_gen_id     TEXT,
    vertical_video_media_gen_id     TEXT,
    vertical_upscale_media_gen_id   TEXT,
    vertical_image_status           TEXT DEFAULT 'PENDING',
    vertical_video_status           TEXT DEFAULT 'PENDING',

    horizontal_image_url            TEXT,
    horizontal_video_url            TEXT,
    horizontal_upscale_url          TEXT,
    horizontal_image_media_gen_id   TEXT,
    horizontal_video_media_gen_id   TEXT,
    horizontal_upscale_media_gen_id TEXT,
    horizontal_image_status         TEXT DEFAULT 'PENDING',
    horizontal_video_status         TEXT DEFAULT 'PENDING',

    vertical_end_scene_media_gen_id   TEXT,
    horizontal_end_scene_media_gen_id TEXT,

    trim_start  REAL,
    trim_end    REAL,
    duration    REAL,

    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_scene_video ON scene(video_id);
CREATE INDEX IF NOT EXISTS idx_scene_parent ON scene(parent_scene_id);

CREATE TABLE IF NOT EXISTS request (
    id              TEXT PRIMARY KEY,
    project_id      TEXT REFERENCES project(id),
    video_id        TEXT REFERENCES video(id),
    scene_id        TEXT REFERENCES scene(id),
    character_id    TEXT REFERENCES character(id),
    type            TEXT NOT NULL CHECK(type IN ('GENERATE_IMAGES','GENERATE_VIDEO','UPSCALE_VIDEO','GENERATE_CHARACTER_IMAGE')),
    orientation     TEXT CHECK(orientation IN ('VERTICAL','HORIZONTAL')),
    status          TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING','PROCESSING','COMPLETED','FAILED')),
    request_id      TEXT,
    media_gen_id    TEXT,
    output_url      TEXT,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_request_scene ON request(scene_id);
CREATE INDEX IF NOT EXISTS idx_request_status ON request(status);
"""


def get_db() -> sqlite3.Connection:
    """Get a database connection."""
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    """Initialize the database with schema."""
    db = get_db()
    db.executescript(SCHEMA)
    db.close()
    print(f"Database initialized at {DB_PATH}")
