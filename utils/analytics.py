import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from config import ANALYTICS_WINDOW_DAYS
from utils.metadata import load_all_metadata, update_metadata
from utils.performance import finished
from utils.youtube_auth import (
    ANALYTICS_SCOPE,
    READONLY_SCOPE,
    build_service,
    has_saved_credentials,
    load_credentials,
)

logger = logging.getLogger(__name__)

METRICS = [
    "views",
    "engagedViews",
    "averageViewPercentage",
    "averageViewDuration",
    "likes",
    "comments",
    "shares",
    "subscribersGained",
]

# YouTube Analytics reports days in Pacific time. A fixed offset is close
# enough for windows measured in whole days.
REPORTING_TIMEZONE = timezone(timedelta(hours=-8))

# Analytics data can take a couple of days to fill in.
DATA_LAG_DAYS = 2

# How long to keep looking for a hand-uploaded video's ID after it was generated.
LINK_LOOKBACK_DAYS = 30


def sync_analytics() -> None:
    """Find the YouTube IDs of new uploads and fetch stats for videos that still need them."""
    if not has_saved_credentials():
        logger.info("No YouTube credentials saved, skipping analytics sync")
        return

    credentials = load_credentials([READONLY_SCOPE, ANALYTICS_SCOPE])
    records = load_all_metadata()

    link_uploads(build_service("youtube", "v3", credentials), records)
    refresh_stats(build_service("youtubeAnalytics", "v2", credentials), records)


def link_uploads(youtube, records: List[Tuple[Path, dict]]) -> None:
    """Match videos that were uploaded by hand to their metadata by title."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LINK_LOOKBACK_DAYS)
    unlinked = {
        _normalize(metadata["title"]): (path, metadata)
        for path, metadata in records
        if not metadata.get("video_id")
        and metadata.get("title")
        and _created_at(path, metadata) >= cutoff
    }
    if not unlinked:
        return

    known_ids = {
        metadata["video_id"] for _, metadata in records if metadata.get("video_id")
    }
    # Uploads are listed newest first, so stop once they're older than any unlinked video.
    oldest = min(_created_at(path, metadata) for path, metadata in unlinked.values())
    stop_before = oldest - timedelta(days=1)

    channels = youtube.channels().list(part="contentDetails", mine=True).execute()
    if not channels.get("items"):
        logger.warning("The YouTube account has no channel, can't look up its uploads")
        return
    uploads = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    request = youtube.playlistItems().list(
        part="snippet,contentDetails", playlistId=uploads, maxResults=50
    )
    while request is not None and unlinked:
        response = request.execute()

        for item in response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            published_at = item["contentDetails"].get(
                "videoPublishedAt", item["snippet"]["publishedAt"]
            )
            key = _normalize(item["snippet"]["title"])

            if key in unlinked and video_id not in known_ids:
                path, metadata = unlinked.pop(key)
                fields = {"video_id": video_id, "published_at": published_at}
                update_metadata(path, fields)
                metadata.update(fields)
                known_ids.add(video_id)
                logger.info(f"Linked YouTube video {video_id} to {path}")

            if datetime.fromisoformat(published_at) < stop_before:
                return

        request = youtube.playlistItems().list_next(request, response)


def refresh_stats(analytics, records: List[Tuple[Path, dict]]) -> None:
    """Fetch each video's stats for its first days, until that data has settled."""
    today = datetime.now(REPORTING_TIMEZONE).date()

    by_start_date = defaultdict(list)
    for path, metadata in records:
        if metadata.get("video_id") and not metadata.get("stats_final"):
            published_at = (
                datetime.fromisoformat(metadata["published_at"])
                if metadata.get("published_at")
                else _created_at(path, metadata)
            )
            start = published_at.astimezone(REPORTING_TIMEZONE).date()
            by_start_date[start].append((path, metadata))

    for start, group in by_start_date.items():
        end = start + timedelta(days=ANALYTICS_WINDOW_DAYS - 1)
        stats = _query_stats(
            analytics,
            [metadata["video_id"] for _, metadata in group],
            start,
            min(end, today),
        )

        for path, metadata in group:
            fields = {
                # Videos without any views in the window have no row in the report
                "stats": stats.get(metadata["video_id"], dict.fromkeys(METRICS, 0)),
                "stats_window": [start.isoformat(), end.isoformat()],
                "stats_final": today >= end + timedelta(days=DATA_LAG_DAYS),
                "stats_updated_at": datetime.now(timezone.utc).isoformat(),
            }
            update_metadata(path, fields)
            metadata.update(fields)

        logger.info(f"Updated stats for {len(group)} video(s) published on {start}")


def _query_stats(
    analytics, video_ids: List[str], start: date, end: date
) -> Dict[str, dict]:
    response = (
        analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics=",".join(METRICS),
            dimensions="video",
            filters="video==" + ",".join(video_ids),
        )
        .execute()
    )

    columns = [header["name"] for header in response["columnHeaders"]]
    return {
        row[0]: dict(zip(columns[1:], row[1:])) for row in response.get("rows") or []
    }


def _created_at(path: Path, metadata: dict) -> datetime:
    if metadata.get("created_at"):
        return datetime.fromisoformat(metadata["created_at"])

    # Older metadata files only have their date in the folder name
    try:
        return datetime.strptime(path.parent.name, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def _normalize(title: str) -> str:
    return " ".join(title.split()).casefold()


def print_report(records: List[dict]) -> None:
    done = finished(records)
    collecting = [r for r in records if r.get("video_id") and not r.get("stats_final")]
    print(
        f"{len(done)} video(s) with complete stats, {len(collecting)} still collecting"
    )
    if not done:
        return

    def engaged_views(record: dict) -> int:
        return record["stats"].get("engagedViews", 0)

    for field in ("topic", "hook_style"):
        groups = defaultdict(list)
        for record in done:
            groups[record.get(field) or "(not recorded)"].append(engaged_views(record))

        print(f"\nMedian engaged views by {field}:")
        for option, views in sorted(
            groups.items(), key=lambda group: statistics.median(group[1]), reverse=True
        ):
            print(
                f"  {statistics.median(views):>9,.0f}  {option} ({len(views)} videos)"
            )

    print("\nTop videos:")
    for record in sorted(done, key=engaged_views, reverse=True)[:5]:
        print(f"  {engaged_views(record):>9,}  {record['title']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_analytics()
    print_report([metadata for _, metadata in load_all_metadata()])
