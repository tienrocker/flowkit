# Google Flow Agent — Architecture

## Overview
Standalone system for AI video production: Chrome extension talks to Google Flow API,
Python agent manages data locally via SQLite and orchestrates everything.

## Two Components

### 1. Extension (Chrome)
- Captures Google Flow bearer token (ya29.*) from aisandbox-pa.googleapis.com
- Solves reCAPTCHA v2 (site key: 6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV)
- Wraps ALL Google Flow API endpoints
- Exposes to local agent via WebSocket
- API methods:
  - generate_image(prompt, characters[], orientation) → mediaGenerationId + imageUrl
  - generate_video(mediaGenId, prompt, orientation, endSceneMediaGenId?) → mediaGenerationId + videoUrl
  - upscale_video(mediaGenId, orientation, resolution) → mediaGenerationId + videoUrl
  - generate_character_image(name, description) → mediaGenerationId + imageUrl
  - get_request_status(requestId) → status + output
  - get_credits() → remaining credits + tier

### 2. Local Agent (Python + SQLite)
- CRUD for projects, videos, scenes, characters
- Track requests/jobs
- Calls extension to gen image/video/upscale
- Post-processing: trim, merge (ffmpeg), add music
- Upload YouTube

## Stack
- Extension: Chrome Manifest V3, vanilla JS
- Agent: Python 3.12+, FastAPI, SQLite
- Communication: WebSocket (extension ↔ agent)

---

## Database Schema

### character (STANDALONE — not owned by project)
```sql
CREATE TABLE character (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    reference_image_url TEXT,
    media_gen_id        TEXT,
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);
```

### project
```sql
CREATE TABLE project (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    thumbnail_url       TEXT,
    language            TEXT DEFAULT 'en',
    status              TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ARCHIVED')),
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);
```

### project_character (link table, M:N)
```sql
CREATE TABLE project_character (
    project_id   TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    character_id TEXT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, character_id)
);
```

### video (belongs to project)
```sql
CREATE TABLE video (
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
CREATE INDEX idx_video_project ON video(project_id);
```

### scene (belongs to video, chainable, dual orientation)
```sql
CREATE TABLE scene (
    id                  TEXT PRIMARY KEY,
    video_id            TEXT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    display_order       INTEGER DEFAULT 0,
    prompt              TEXT,
    character_names     TEXT,

    -- Chain
    parent_scene_id     TEXT REFERENCES scene(id),
    chain_type          TEXT DEFAULT 'ROOT' CHECK(chain_type IN ('ROOT','CONTINUATION','INSERT')),

    -- Vertical
    vertical_image_url              TEXT,
    vertical_video_url              TEXT,
    vertical_upscale_url            TEXT,
    vertical_image_media_gen_id     TEXT,
    vertical_video_media_gen_id     TEXT,
    vertical_upscale_media_gen_id   TEXT,
    vertical_image_status           TEXT DEFAULT 'PENDING',
    vertical_video_status           TEXT DEFAULT 'PENDING',

    -- Horizontal
    horizontal_image_url            TEXT,
    horizontal_video_url            TEXT,
    horizontal_upscale_url          TEXT,
    horizontal_image_media_gen_id   TEXT,
    horizontal_video_media_gen_id   TEXT,
    horizontal_upscale_media_gen_id TEXT,
    horizontal_image_status         TEXT DEFAULT 'PENDING',
    horizontal_video_status         TEXT DEFAULT 'PENDING',

    -- Chain source
    vertical_end_scene_media_gen_id   TEXT,
    horizontal_end_scene_media_gen_id TEXT,

    -- Trim
    trim_start  REAL,
    trim_end    REAL,
    duration    REAL,

    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX idx_scene_video ON scene(video_id);
CREATE INDEX idx_scene_parent ON scene(parent_scene_id);
```

### request (job tracking)
```sql
CREATE TABLE request (
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
CREATE INDEX idx_request_scene ON request(scene_id);
CREATE INDEX idx_request_status ON request(status);
```

---

## File Structure
```
google-flow-agent/
├── extension/
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
├── agent/
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   └── crud.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── video.py
│   │   ├── scene.py
│   │   ├── character.py
│   │   └── request.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── videos.py
│   │   ├── scenes.py
│   │   ├── characters.py
│   │   └── requests.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── flow_client.py
│   │   ├── scene_chain.py
│   │   └── post_process.py
│   └── worker/
│       ├── __init__.py
│       └── processor.py
└── requirements.txt
```

---

## Reference Repos (READ ONLY)
- /tmp/veogent-flow-connect/ — existing Chrome extension (study background.js for token capture + WS patterns)
- /tmp/vgen-agent-backend/src/modules/scene/scene.d.ts — Scene TypeScript types
- /tmp/vgen-agent-backend/src/modules/request/request.d.ts — Request DTOs with all input data types
- /tmp/vgen-agent-video-processor/app/video/api_client.py — Google Flow API client (KEY FILE for API endpoints, auth, request/response)
- /tmp/vgen-agent-video-processor/app/worker/ — Worker patterns
- /tmp/vgen-agent-video-processor/app/image/ — Image generation patterns
- /tmp/vgen-agent-video-processor/app/config.py — Config

## Key Google Flow API Details
- Endpoint: aisandbox-pa.googleapis.com
- Auth: Bearer ya29.* token (captured by extension from Google Labs session)
- reCAPTCHA v2 enterprise required for most calls
- Each generated asset gets a unique mediaGenerationId (base64-encoded protobuf)
- Video generation is async: submit → poll → get result
- Upscale also async with same pattern
- endScene parameter chains video from previous scene's mediaGenerationId
