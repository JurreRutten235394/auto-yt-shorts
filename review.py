#!/usr/bin/python

from pathlib import Path

from config import NO_UPLOAD
from utils.metadata import load_all_metadata, record_upload, update_metadata
from utils.yt import auto_upload

# YouTube's limit for video titles
MAX_TITLE_LENGTH = 100

ACTIONS = (
    "[a]pprove and upload, [r]eject, edit [t]itle, edit [d]escription, [s]kip, [q]uit: "
)


def show(video_file: Path, metadata: dict) -> None:
    print(f"\nVideo:       {video_file}")
    print(f"Title:       {metadata['title']}")
    print(f"Hook:        {metadata.get('hook_caption')}")
    print(f"Topic:       {metadata.get('topic')} ({metadata.get('hook_style')})")
    print(f"Tags:        {', '.join(metadata.get('tags') or [])}")
    print(f"\nScript:\n{metadata['script']}")
    print(f"\nDescription:\n{metadata['description']}")

    corrections = metadata.get("fact_check_corrections")
    if corrections:
        print("\nThe fact check corrected these, double check them:")
        for issue in corrections:
            print(f"  - {issue}")


def review(metadata_file: Path, metadata: dict) -> bool:
    """Show one pending video and act on the reviewer's choice. Returns False to stop reviewing."""
    video_file = metadata_file.with_suffix(".mp4")
    show(video_file, metadata)

    while True:
        choice = input(f"\n{ACTIONS}").strip().lower()

        if choice == "t":
            title = input("New title: ").strip()
            if len(title) > MAX_TITLE_LENGTH:
                print(f"Titles can be at most {MAX_TITLE_LENGTH} characters")
            elif title:
                metadata["title"] = title
                update_metadata(metadata_file, {"title": title})

        elif choice == "d":
            print("New description, finish with an empty line:")
            description = "\n".join(iter(input, "")).strip()
            if description:
                metadata["description"] = description
                update_metadata(metadata_file, {"description": description})

        elif choice == "a":
            try:
                uploaded_video = auto_upload(
                    video_file,
                    metadata["title"],
                    metadata["description"],
                    metadata.get("tags"),
                )
            except Exception as e:
                print(f"Upload failed, the video stays in the review queue: {e}")
                return True

            if uploaded_video:
                record_upload(video_file, uploaded_video)
                print(f"Uploaded as https://youtube.com/shorts/{uploaded_video['id']}")
            elif NO_UPLOAD:
                print(
                    "NO_UPLOAD is on, so upload it yourself with exactly this title "
                    "and its stats will be matched to it automatically"
                )
            update_metadata(metadata_file, {"review_status": "approved"})
            return True

        elif choice == "r":
            update_metadata(metadata_file, {"review_status": "rejected"})
            return True

        elif choice == "s":
            return True

        elif choice == "q":
            return False

        if choice in ("t", "d"):
            show(video_file, metadata)


def main() -> None:
    pending = [
        (metadata_file, metadata)
        for metadata_file, metadata in load_all_metadata()
        if metadata.get("review_status") == "pending"
    ]

    if not pending:
        print("No videos are waiting for review")
        return

    print(f"{len(pending)} video(s) waiting for review")
    for metadata_file, metadata in pending:
        if not review(metadata_file, metadata):
            break


if __name__ == "__main__":
    main()
