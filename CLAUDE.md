# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp example.env .env
# Edit .env with your API keys and credentials

# Initial YouTube OAuth setup (run once)
python upload_video.py

# Update/refresh OAuth credentials (also grants analytics access to older tokens)
python update_tokens.py
```

### Running the Application
```bash
# One-time execution
RUN_ONCE=true python main.py

# Scheduled execution with cron
CRON_SCHEDULE="0 */6 * * *" python main.py

# Run with Docker
docker compose up

# Testing stock video functionality
python test.py

# Sync YouTube Analytics stats and print what's performing best
python -m utils.analytics

# Approve, edit or reject videos waiting for review (REVIEW_BEFORE_UPLOAD=true)
python review.py
```

### Project Structure & Configuration
- `config.py` - Central configuration with environment variables and API keys
- `main.py` - Entry point with scheduler and video generation orchestration
- `requirements.txt` - Python dependencies
- `utils/` - Core functionality modules
- `credentials/` - YouTube OAuth credentials (client_secrets.json, tokens.json)
- `music/` - Background music files (.mp3)
- `secondary_video/` - Optional footage you made yourself, overlaid when `USE_SECONDARY_VIDEO=true` (.mp4)
- `temp/` - Temporary files during processing
- `output/` - Final generated videos organized by date

## Architecture Overview

This is an automated YouTube Shorts/TikTok video generation system that creates engaging short-form content using AI. The application follows a pipeline architecture:

### Core Pipeline (main.py:96-209)
1. **Performance Sync** - Pulls stats for past uploads from the YouTube Analytics API into their metadata
2. **Topic & Hook Selection** - Picks a subtopic of `CHANNEL_NICHE` and a hook style, favouring what performed best
3. **Content Creation** - Generates titles and looping scripts using OpenAI, with the best and worst past videos as examples
4. **Fact Check** - Corrects inaccurate scripts, or drops the title and tries the next-ranked one
5. **Media Assembly** - Combines stock footage, voiceover, subtitles and a hook caption on the first frame
6. **Upload & Storage** - Saves metadata, then uploads and records the video ID, or queues it for `review.py`

### Key Modules

**utils/llm.py** - OpenAI integration for content generation
- `get_topic()`, `get_hook_style()` - Pick from `POSSIBLE_TOPICS` / `HOOK_STYLES` using past performance
- `get_titles()`, `get_script()` - AI-generated content in the chosen hook style; scripts end on a line that loops back into the opening
- `check_facts()` - Up to `FACT_CHECK_ROUNDS` checks with corrections in between, raises `FactCheckFailed` when the video can't be made accurate
- `get_hook_caption()` - 3 to 7 word on-screen hook for the first seconds
- `get_tags()` - YouTube tags, trimmed to the 500 character limit
- `get_most_engaging_titles()` - Content ranking and selection

**utils/video.py** - Video processing and assembly
- `generate_subtitles()` - AssemblyAI transcription with SRT equalization
- `combine_videos()` - Concatenates stock footage to match audio duration
- `generate_video()` - Final composition with subtitles, the hook caption, audio, and optional secondary content

**utils/audio.py** - Voice generation and audio processing
- `generate_voiceover()` - Google Gemini TTS with custom voice (Fenrir)
- `get_random_background_song()` - Random background music selection

**utils/stock_videos.py** - External media sourcing
- `get_stock_videos()` - Pexels API integration for relevant footage

**utils/yt.py** - Platform upload functionality
- `auto_upload()` - YouTube upload with OAuth 2.0 authentication, returns the created video
- Uses `insert_video()` from `upload_video.py` (resumable upload with retries)

**utils/youtube_auth.py** - OAuth scopes, token loading and API clients shared by upload, analytics and `update_tokens.py`

**utils/analytics.py** - YouTube Analytics feedback loop
- `sync_analytics()` - Links hand-uploaded videos to their metadata by title, then stores each video's stats for its first `ANALYTICS_WINDOW_DAYS` days in its metadata JSON
- Stats are marked `stats_final` once the window has closed and the data has settled

**utils/performance.py** - Learning from past videos
- `choose()` - Thompson sampling over finished videos' scores (log of engaged views)
- `format_examples()` - Best and worst past videos as prompt context

**utils/metadata.py** - Per-video JSON in `output/<date>/<title>.json` (title, script, topic, hook style, tags, hook caption, fact check corrections, review status, video ID, stats)

**review.py** - Interactive review queue: shows each pending video and its fact check corrections, then approves (uploads), rejects, or edits the title and description

### Environment Variables
Key configurations in `.env`:
- `OPENAI_API_KEY_AUTO_YT_SHORTS` - OpenAI API access
- `GEMINI_API_KEY` - Google Gemini TTS
- `PEXELS_API_KEY` - Stock video sourcing
- `ASSEMBLY_AI_API_KEY` - Subtitle generation
- `CRON_SCHEDULE` - Automated execution timing
- `RUN_ONCE` - Single execution mode
- `VIDEO_COUNT` - Number of videos per run
- `NO_UPLOAD` - Disable platform uploads
- `NOTIFY_ON_SUCCESS` - Success notifications via Apprise
- `VIDEO_LANGUAGE` - Language of titles and voiceover sent with uploads (default `en`)
- `CONTAINS_SYNTHETIC_MEDIA` - Sets YouTube's altered or synthetic content disclosure
- `ANALYTICS_WINDOW_DAYS` - Days after upload used to compare videos (default 3)
- `USE_SECONDARY_VIDEO` - Overlay a clip from `secondary_video/` (default off)
- `REVIEW_BEFORE_UPLOAD` - Queue videos for `python review.py` instead of uploading them (default off)

The niche (`CHANNEL_NICHE`), its subtopics (`POSSIBLE_TOPICS`) and `HOOK_STYLES` are set in `config.py`.

### Execution Modes
- **Scheduled Mode**: Uses APScheduler with cron expressions for automated generation
- **One-time Mode**: Single execution when `RUN_ONCE=true`
- **Docker Mode**: Containerized execution with volume mounts for credentials and content

The system is designed for unattended operation, generating fact-checked videos within one niche (science and space by default) and learning from each video's YouTube Analytics, with comprehensive error handling and notification systems.