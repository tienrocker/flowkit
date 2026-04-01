# Google Flow Agent

Standalone system to generate AI videos via Google Flow API. Uses a Chrome extension as browser bridge for authentication, reCAPTCHA solving, and API proxying.

```
┌──────────────────┐     WebSocket      ┌──────────────────────┐
│  Python Agent    │◄──────────────────►│  Chrome Extension     │
│  (FastAPI+SQLite)│     localhost:9222  │  (MV3 Service Worker) │
│                  │                    │                       │
│  - REST API :8100│  ── commands ──►   │  - Token capture      │
│  - Queue worker  │  ◄── results ──    │  - reCAPTCHA solve    │
│  - Post-process  │                    │  - API proxy          │
│  - SQLite DB     │                    │  (on labs.google)     │
└──────────────────┘                    └──────────────────────┘
```

## Why?

Google Flow (labs.google) has no official API. This project reverse-engineers the internal endpoints and uses a Chrome extension running on a real browser session to:

1. **Capture** the bearer token (`ya29.*`) from network requests
2. **Solve** reCAPTCHA Enterprise tokens via `grecaptcha.enterprise.execute()`
3. **Proxy** API calls through the browser (residential IP, cookies, session)

The Python agent manages projects, scenes, and a request queue — the extension just executes what the agent tells it to.

## Quick Start

### 1. Install the Chrome Extension

```bash
# In Chrome:
# 1. Go to chrome://extensions
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ folder from this repo
```

### 2. Open Google Flow

Go to [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow) and sign in. The extension captures your bearer token automatically.

Check the extension popup — you should see:
- ✅ Agent connected (once the agent is running)
- 🔑 Token captured

### 3. Start the Agent

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python -m agent.main

# Or with custom ports
API_HOST=127.0.0.1 API_PORT=8100 WS_PORT=9222 python -m agent.main
```

The agent starts:
- **REST API** on `http://127.0.0.1:8100`
- **WebSocket server** on `ws://127.0.0.1:9222` (extension auto-connects)
- **Background worker** that processes the request queue

### 4. Verify Connection

```bash
curl http://127.0.0.1:8100/health
# {"status":"ok","version":"0.2.0","extension_connected":true}

curl http://127.0.0.1:8100/api/flow/status
# {"connected":true,"flow_key_present":true}

curl http://127.0.0.1:8100/api/flow/credits
# {"credits":...,"userPaygateTier":"PAYGATE_TIER_TWO"}
```

## Usage

### Option A: Direct API (for testing / one-off)

```bash
# Generate an image
curl -X POST http://127.0.0.1:8100/api/flow/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A white Bichon Frise dog wearing a tiny business suit",
    "project_id": "12345",
    "aspect_ratio": "IMAGE_ASPECT_RATIO_PORTRAIT"
  }'

# Generate a video from an image
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<media_gen_id from image>",
    "prompt": "The dog walks confidently through a shopping mall",
    "project_id": "12345",
    "scene_id": "scene-1"
  }'

# Check video generation status
curl -X POST http://127.0.0.1:8100/api/flow/check-status \
  -H "Content-Type: application/json" \
  -d '{"operations": [{"name": "operations/xxx"}]}'

# Upscale a video to 4K
curl -X POST http://127.0.0.1:8100/api/flow/upscale-video \
  -H "Content-Type: application/json" \
  -d '{
    "media_gen_id": "<video_media_gen_id>",
    "scene_id": "scene-1"
  }'
```

### Option B: Queue-based (for production pipelines)

Create a project with characters, scenes, and let the worker process everything automatically.

```bash
# 1. Create a project
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Boss Babe Ep 5", "language": "en"}'
# → {"id": "proj-uuid", ...}

# 2. Create a character
curl -X POST http://127.0.0.1:8100/api/characters \
  -H "Content-Type: application/json" \
  -d '{"name": "Bijou", "description": "White Bichon Frise, tiny CEO in designer suit"}'
# → {"id": "char-uuid", ...}

# 3. Link character to project
curl -X POST http://127.0.0.1:8100/api/projects/proj-uuid/characters/char-uuid

# 4. Create a video
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-uuid", "title": "Episode 5"}'
# → {"id": "vid-uuid", ...}

# 5. Create scenes
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "vid-uuid",
    "display_order": 0,
    "prompt": "Bijou enters a luxury mall flanked by two Doberman bodyguards",
    "image_prompt": "A tiny white Bichon Frise CEO in a designer suit entering a luxury mall...",
    "video_prompt": "The tiny CEO walks confidently through the mall entrance...",
    "character_names": ["Bijou"]
  }'
# → {"id": "scene-uuid", ...}

# 6. Queue image generation
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_IMAGES",
    "orientation": "VERTICAL",
    "scene_id": "scene-uuid",
    "project_id": "proj-uuid",
    "video_id": "vid-uuid"
  }'

# 7. Check request status
curl http://127.0.0.1:8100/api/requests/pending
curl http://127.0.0.1:8100/api/requests?scene_id=scene-uuid

# 8. Once image is done, queue video generation
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "GENERATE_VIDEO",
    "orientation": "VERTICAL",
    "scene_id": "scene-uuid",
    "project_id": "proj-uuid"
  }'

# 9. Once video is done, queue upscale
curl -X POST http://127.0.0.1:8100/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "type": "UPSCALE_VIDEO",
    "orientation": "VERTICAL",
    "scene_id": "scene-uuid"
  }'
```

The worker automatically:
- Picks up PENDING requests
- Solves reCAPTCHA via extension
- Calls the correct Google Flow endpoint
- Polls for async operations (video gen, upscale)
- Updates scene status and media URLs
- Retries on failure (up to 5 times)

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + extension status |
| **Characters** | | |
| `POST` | `/api/characters` | Create character |
| `GET` | `/api/characters` | List all characters |
| `GET` | `/api/characters/:id` | Get character |
| `PATCH` | `/api/characters/:id` | Update character |
| `DELETE` | `/api/characters/:id` | Delete character |
| **Projects** | | |
| `POST` | `/api/projects` | Create project |
| `GET` | `/api/projects` | List projects |
| `GET` | `/api/projects/:id` | Get project |
| `PATCH` | `/api/projects/:id` | Update project |
| `DELETE` | `/api/projects/:id` | Delete project |
| `POST` | `/api/projects/:id/characters/:cid` | Link character |
| `DELETE` | `/api/projects/:id/characters/:cid` | Unlink character |
| `GET` | `/api/projects/:id/characters` | List project characters |
| **Videos** | | |
| `POST` | `/api/videos` | Create video |
| `GET` | `/api/videos?project_id=` | List videos |
| `GET` | `/api/videos/:id` | Get video |
| `PATCH` | `/api/videos/:id` | Update video |
| `DELETE` | `/api/videos/:id` | Delete video |
| **Scenes** | | |
| `POST` | `/api/scenes` | Create scene |
| `GET` | `/api/scenes?video_id=` | List scenes |
| `GET` | `/api/scenes/:id` | Get scene |
| `PATCH` | `/api/scenes/:id` | Update scene |
| `DELETE` | `/api/scenes/:id` | Delete scene |
| **Requests** | | |
| `POST` | `/api/requests` | Create request |
| `GET` | `/api/requests` | List requests |
| `GET` | `/api/requests/pending` | List pending |
| `GET` | `/api/requests/:id` | Get request |
| `PATCH` | `/api/requests/:id` | Update request |
| **Flow (Direct)** | | |
| `GET` | `/api/flow/status` | Extension connection status |
| `GET` | `/api/flow/credits` | Google Flow credits |
| `POST` | `/api/flow/generate-image` | Generate image (sync) |
| `POST` | `/api/flow/generate-video` | Submit video gen |
| `POST` | `/api/flow/upscale-video` | Submit upscale |
| `POST` | `/api/flow/check-status` | Poll operation status |

### Request Types

| Type | Description | Async? |
|------|-------------|--------|
| `GENERATE_IMAGES` | Generate scene image | No — returns immediately |
| `GENERATE_VIDEO` | Generate video from image | Yes — worker polls until done |
| `UPSCALE_VIDEO` | Upscale video to 4K | Yes — worker polls until done |
| `GENERATE_CHARACTER_IMAGE` | Generate character reference | No |

### Scene Fields

Each scene stores media for **two orientations** (vertical 9:16 + horizontal 16:9):

```
vertical_image_url / vertical_image_media_gen_id / vertical_image_status
vertical_video_url / vertical_video_media_gen_id / vertical_video_status
vertical_upscale_url / vertical_upscale_media_gen_id / vertical_upscale_status
(same for horizontal_*)
```

Status flow: `PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`

### Scene Chaining

For smooth transitions between scenes, use continuation chains:

```
Scene 0 (ROOT) ──video──► Scene 1 (CONTINUATION)
                          └─ endImage = Scene 0's video mediaGenId
```

Set `parent_scene_id` and `chain_type: "CONTINUATION"` when creating the scene. The worker automatically uses the parent's video as `endImage` for the Google Flow API.

## Architecture

```
agent/
├── main.py              # FastAPI app + WebSocket server
├── config.py            # All configuration
├── db/
│   ├── schema.py        # SQLite schema (aiosqlite)
│   └── crud.py          # Async CRUD with column whitelisting
├── models/
│   ├── enums.py         # Literal types for validation
│   ├── character.py
│   ├── project.py
│   ├── video.py
│   ├── scene.py
│   └── request.py
├── api/
│   ├── characters.py    # REST routes
│   ├── projects.py
│   ├── videos.py
│   ├── scenes.py
│   ├── requests.py
│   └── flow.py          # Direct Flow API access
├── services/
│   ├── flow_client.py   # WS bridge to extension
│   ├── headers.py       # Randomized browser headers
│   ├── scene_chain.py   # Continuation scene logic
│   └── post_process.py  # ffmpeg trim/merge/music
└── worker/
    └── processor.py     # Background queue processor + status poller

extension/
├── manifest.json        # Chrome MV3
├── background.js        # WS client, token capture, API proxy
├── content.js           # Bridge to injected.js
├── injected.js          # reCAPTCHA solver (MAIN world)
├── popup.html
└── popup.js
```

### How It Works

1. **Extension** captures bearer token from `aisandbox-pa.googleapis.com` requests
2. **Extension** connects to agent's WebSocket server (`ws://127.0.0.1:9222`)
3. **Agent** receives API requests via REST or queue
4. **Agent** sends commands to extension via WS: `{method: "api_request", params: {url, body, captchaAction}}`
5. **Extension** solves reCAPTCHA, injects token into request body, makes API call from browser context
6. **Extension** returns result to agent via WS
7. **Worker** polls async operations (video gen, upscale) until completion
8. **Agent** updates scene/request status in SQLite

### Google Flow API Endpoints

| Operation | Endpoint |
|-----------|----------|
| Generate Image | `POST /v1/projects/{id}/flowMedia:batchGenerateImages` |
| Generate Video | `POST /v1/video:batchAsyncGenerateVideoStartImage` |
| Generate Video (chain) | `POST /v1/video:batchAsyncGenerateVideoStartAndEndImage` |
| Upscale Video | `POST /v1/video:batchAsyncGenerateVideoUpsampleVideo` |
| Check Status | `POST /v1/video:batchCheckAsyncVideoGenerationStatus` |
| Get Credits | `GET /v1/credits` |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `127.0.0.1` | REST API bind address |
| `API_PORT` | `8100` | REST API port |
| `WS_HOST` | `127.0.0.1` | WebSocket server bind |
| `WS_PORT` | `9222` | WebSocket server port |
| `POLL_INTERVAL` | `5` | Worker poll interval (seconds) |
| `MAX_RETRIES` | `5` | Max retries per request |
| `VIDEO_POLL_TIMEOUT` | `420` | Video gen poll timeout (seconds) |

## Post-Processing

After all scenes are generated and upscaled, use the post-process utilities:

```python
from agent.services.post_process import trim_video, merge_videos, add_music

# Trim each scene
trim_video("scene0_4k.mp4", "scene0_trimmed.mp4", start=0, end=6)
trim_video("scene1_4k.mp4", "scene1_trimmed.mp4", start=0, end=4)

# Merge all trimmed scenes
merge_videos(["scene0_trimmed.mp4", "scene1_trimmed.mp4"], "merged.mp4")

# Add background music
add_music("merged.mp4", "music.mp3", "final.mp4", music_volume=0.3)
```

All ffmpeg outputs use `-movflags +faststart` for streaming compatibility.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Extension shows "Agent disconnected" | Make sure `python -m agent.main` is running |
| Extension shows "No token" | Open [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow) and do any action |
| `CAPTCHA_FAILED: NO_FLOW_TAB` | Need a Google Flow tab open in Chrome |
| `CAPTCHA_FAILED: grecaptcha not available` | Wait for the Flow page to fully load |
| API returns 403 | reCAPTCHA token expired or invalid — will auto-retry |
| API returns 429 | Rate limited — wait and retry |
| Video gen stuck in PROCESSING | Check `/api/requests?status=PROCESSING` — worker polls automatically |

## License

MIT
