import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from config import OUTPUT_PATH

logger = logging.getLogger(__name__)


def save_metadata(
    title: str,
    description: str,
    topic: str,
    script: str,
    search_terms: List[str],
    video_path: Path,
    hook_style: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Path:
    metadata = {
        "title": title,
        "description": description,
        "topic": topic,
        "hook_style": hook_style,
        "script": script,
        "search_terms": search_terms,
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    today = (datetime.now()).strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_PATH / today, exist_ok=True)

    title = title.replace("/", " ")

    new_video_file = OUTPUT_PATH / f"{today}" / f"{title}.mp4"

    shutil.move(str(video_path), new_video_file)

    with open(OUTPUT_PATH / f"{today}" / f"{title}.json", "w") as f:
        json.dump(metadata, f)

    return new_video_file


def record_upload(video_file: Path, video: dict) -> None:
    """Store the YouTube video ID next to the metadata so analytics can be matched to it."""
    update_metadata(
        video_file.with_suffix(".json"),
        {
            "video_id": video["id"],
            "published_at": video.get("snippet", {}).get("publishedAt"),
        },
    )


def update_metadata(metadata_file: Path, fields: dict) -> None:
    with open(metadata_file) as f:
        metadata = json.load(f)

    metadata.update(fields)

    with open(metadata_file, "w") as f:
        json.dump(metadata, f)


def load_all_metadata() -> List[Tuple[Path, dict]]:
    """Every saved video's metadata file and contents, oldest first."""
    records = []
    for metadata_file in sorted(OUTPUT_PATH.glob("*/*.json")):
        try:
            with open(metadata_file) as f:
                records.append((metadata_file, json.load(f)))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Skipping unreadable metadata file {metadata_file}: {e}")

    return records
