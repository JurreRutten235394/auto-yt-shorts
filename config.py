import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

# What every video on the channel is about. YouTube finds the right viewers for
# a channel faster when all of its Shorts are for the same audience.
CHANNEL_NICHE = "science and space"

# Subtopics of the niche, picked by past performance (see utils/performance.py)
POSSIBLE_TOPICS = [
    "Planets and moons of our solar system",
    "Stars, black holes and galaxies",
    "Space missions and astronauts",
    "The human body",
    "The human brain and senses",
    "Animal superpowers",
    "Deep sea creatures",
    "Volcanoes, earthquakes and extreme weather",
    "Physics of everyday things",
    "Chemistry and the elements",
    "Accidental scientific discoveries",
    "Dinosaurs and prehistoric life",
]

# Opening formulas for titles and scripts. Each run uses one, chosen from past
# performance in the same way as the topic (see utils/performance.py).
HOOK_STYLES = {
    "Shock/Mystery": [
        "You won't believe...",
        "This will shock you...",
        "Scientists discovered...",
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
        "NASA confirmed...",
        "Biologists were stunned when...",
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

# Overlay a clip from secondary_video/ on the bottom of each video. Only use
# footage you made yourself: Shorts made of reused clips get less reach.
USE_SECONDARY_VIDEO = os.environ.get("USE_SECONDARY_VIDEO", "false").lower() == "true"

# Hold generated videos for approval with `python review.py` instead of
# uploading them straight away
REVIEW_BEFORE_UPLOAD = os.environ.get("REVIEW_BEFORE_UPLOAD", "false").lower() == "true"
