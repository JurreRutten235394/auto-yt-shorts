import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import CONTAINS_SYNTHETIC_MEDIA, NO_UPLOAD, VIDEO_LANGUAGE
from upload_video import insert_video
from utils.youtube_auth import build_service, load_credentials


def auto_upload(
    video: Path,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy: str = "public",
    category: str = "24",
) -> Optional[dict]:
    """Upload to YouTube and return the created video resource, or None if uploads are off."""
    if NO_UPLOAD:
        return None

    youtube = build_service("youtube", "v3", load_credentials())

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category,
            "defaultLanguage": VIDEO_LANGUAGE,
            "defaultAudioLanguage": VIDEO_LANGUAGE,
        },
        "status": {
            "privacyStatus": privacy,
            "containsSyntheticMedia": CONTAINS_SYNTHETIC_MEDIA,
        },
    }

    return insert_video(youtube, str(video), body)


def prep_for_manual_upload(
    file: Path,
    title: str,
    description: str,
) -> None:

    os.system("mkdir -p youtube")

    # create a folder with today's date
    today = (datetime.now()).strftime("%Y-%m-%d")

    os.system(f"mkdir -p youtube/{today}")

    # copy video file into youtube and name it title
    new_video_file = Path("youtube") / f"{today}" / f"{title}.mp4"
    if not new_video_file.exists():
        # copy it
        os.system(f"cp {shlex.quote(str(file))} {shlex.quote(str(new_video_file))}")

        # create a txt file with the description
        with open(new_video_file.with_suffix(".txt"), "w") as f:
            f.write(description)

        print("[Prepped for Manual Upload]")
        print({new_video_file})
        print({new_video_file.with_suffix(".txt")})
