# Google Flow Agent — Gemini CLI Instructions

## Setup

Read `CLAUDE.md` in this repo root — it contains the full API reference, rules, workflow recipes, and pipeline order. Everything there applies to you.

## Skills

This project has reusable skills in `skills/`. When the user says `/gla:<name>`, read `skills/gla:<name>.md` and follow the instructions inside.

Available skills:

| Skill | Purpose |
|-------|---------|
| `/gla:create-project` | Create a new video project |
| `/gla:gen-refs` | Generate reference images for all entities |
| `/gla:gen-images` | Generate scene images |
| `/gla:gen-videos` | Generate scene videos |
| `/gla:gen-chain-videos` | Generate videos with scene chaining |
| `/gla:gen-tts-template` | Generate a voice template for narration |
| `/gla:gen-tts` | Generate TTS narration |
| `/gla:gen-narrator` | Generate narrator text + TTS for all scenes |
| `/gla:concat` | Download and concatenate scene videos |
| `/gla:concat-fit-narrator` | Trim scenes to fit narrator duration, then concat |
| `/gla:status` | Show project status dashboard |
| `/gla:fix-uuids` | Fix non-UUID media_ids |
| `/gla:add-material` | Image material system |
| `/gla:insert-scene` | Insert new scenes into existing chain |
| `/gla:creative-mix` | Creative video mixing techniques |
| `/gla:thumbnail` | Generate YouTube thumbnails |
| `/gla:youtube-seo` | Generate YouTube metadata (SEO) |
| `/gla:youtube-upload` | Upload video to YouTube |
| `/gla:brand-logo` | Apply channel brand logo |
| `/gla:camera-guide` | Cinematic camera prompt reference |

## Pre-flight

Before any workflow, verify the server is running:

```bash
curl -s http://127.0.0.1:8100/health
# Must return: {"extension_connected": true}
```
