import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

POSSIBLE_TOPICS = [
    # "NASA Facts",
    "Controversial Events",
    # "Bold Predictions",
    "Controversial Actions by Celebrities",
    "Controversial Actions by Well Known Companies",
    "Controversial Science Facts",
    "Controversial Historical Mysteries",
    "Controversial Tech Milestones",
    "Controversial Cultural Oddities",
    "Controversial Psychological Phenomena",
    "Controversial Space Exploration Events",
    "Controvercies around Cryptocurrency and Blockchain",
    "Controversial Laws",
    "Controversial Secrets of Successful People",
    "Controversial Eco-Friendly movements",
    "Controversial World Records",
]

# Opening formulas for titles and scripts. Each run uses one, chosen from past
# performance in the same way as the topic (see utils/performance.py).
HOOK_STYLES = {
    "Shock/Mystery": [
        "You won't believe...",
        "This will shock you...",
        "Scientists discovered...",
        "You've been lied to...",
    ],
    "Numbers/Stats": [
        "97% of people don't know...",
        "In just 3 seconds...",
        "Only 1 in 1000...",
    ],
    "Direct Question": [
        "Did you know that...",
        "What if I told you...",
        "Have you ever wondered...",
    ],
    "Urgency": [
        "Before you scroll...",
        "Stop what you're doing...",
        "This changes everything...",
    ],
    "Authority": [
        "Experts revealed...",
        "[Celebrity name] uses this...",
        "Billionaires know this secret...",
    ],
    "Contradiction": [
        "Everyone thinks [X] but actually...",
        "This looks normal, but...",
    ],
}


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY_AUTO_YT_SHORTS")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY_AUTO_YT_SHORTS not set")


OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")

GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

ASSEMBLY_AI_API_KEY = os.environ.get("ASSEMBLY_AI_API_KEY")

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

TEMP_PATH = Path("temp")

os.makedirs(TEMP_PATH, exist_ok=True)

OUTPUT_PATH = Path("output")

os.makedirs(OUTPUT_PATH, exist_ok=True)

BACKGROUND_SONGS_PATH = Path("music")

SECONDARY_CONTENT_PATH = Path("secondary_video")

CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "31 4 * * *")

RUN_ONCE = os.environ.get("RUN_ONCE", "false").lower() == "true"

VIDEO_COUNT = int(os.environ.get("VIDEO_COUNT", "1"))

APPRISE_URL = os.environ.get("APPRISE_URL")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set")

NO_UPLOAD = os.environ.get("NO_UPLOAD", "false").lower() == "true"

NOTIFY_ON_SUCCESS = os.environ.get("NOTIFY_ON_SUCCESS", "false").lower() == "true"

VIDEO_LANGUAGE = os.environ.get("VIDEO_LANGUAGE", "en")

# Set to "true" when videos contain realistic AI-generated or altered footage
# (https://support.google.com/youtube/answer/14328491)
CONTAINS_SYNTHETIC_MEDIA = (
    os.environ.get("CONTAINS_SYNTHETIC_MEDIA", "false").lower() == "true"
)

# Number of days after upload whose stats are used to compare videos
ANALYTICS_WINDOW_DAYS = int(os.environ.get("ANALYTICS_WINDOW_DAYS", "3"))
