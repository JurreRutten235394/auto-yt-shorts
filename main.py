import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from tqdm import tqdm

from config import CRON_SCHEDULE, REVIEW_BEFORE_UPLOAD, RUN_ONCE, VIDEO_COUNT
from utils.analytics import sync_analytics
from utils.audio import generate_voiceover
from utils.llm import (
    FactCheckFailed,
    check_facts,
    get_description,
    get_hook_caption,
    get_hook_style,
    get_most_engaging_titles,
    get_script,
    get_search_terms,
    get_tags,
    get_titles,
    get_topic,
)
from utils.metadata import load_all_metadata, record_upload, save_metadata
from utils.notifications import (
    send_action_notification,
    send_error_notification,
    send_success_notification,
)
from utils.stock_videos import get_stock_videos
from utils.video import generate_video
from utils.yt import auto_upload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_performance() -> list:
    """Sync the latest YouTube stats, then load every saved video to learn from."""
    try:
        sync_analytics()
    except Exception as e:
        error_msg = "Failed to sync YouTube analytics, using the stats saved so far"
        logger.error(f"{error_msg}: {e}")
        send_error_notification(error_msg, e, "Analytics Sync")

    return [metadata for _, metadata in load_all_metadata()]


def generate_video_data(title, hook_style, records):
    logger.info("[Generated Title]")
    logger.info(title)

    script = get_script(title, hook_style, records)
    logger.info("[Generated Script]")
    logger.info(script)

    script, fact_check_corrections = check_facts(title, script)
    logger.info("[Fact Checked Script]")
    logger.info(script)

    description = get_description(title, script)
    logger.info("[Generated Description]")
    logger.info(description)

    search_terms = get_search_terms(title, script)
    logger.info("[Generated Search Terms]")
    logger.info(search_terms)

    tags = get_tags(title, script)
    logger.info("[Generated Tags]")
    logger.info(tags)

    hook_caption = get_hook_caption(title, script)
    logger.info("[Generated Hook Caption]")
    logger.info(hook_caption)

    stock_videos = get_stock_videos(search_terms)
    logger.info("[Generated Stock Videos]")

    voiceover = generate_voiceover(script)
    logger.info("[Generated Voiceover]")

    return (
        title,
        description,
        script,
        fact_check_corrections,
        search_terms,
        tags,
        hook_caption,
        stock_videos,
        voiceover,
    )


def generate_videos(n: int = 4) -> None:
    try:
        records = load_performance()

        topic = get_topic(records)

        logger.info("[Generated Topic]")
        logger.info(topic)

        hook_style = get_hook_style(records)
        logger.info("[Chosen Hook Style]")
        logger.info(hook_style)

        possible_titles = get_titles(topic, hook_style, records)
        logger.info("[Generated Possible Titles]")
        logger.info(possible_titles)

        # Rank every title, so the next one can be tried when one fails its fact check
        titles = get_most_engaging_titles(possible_titles, len(possible_titles))

        videos_generated = 0
        attempts = 0
        progress = tqdm(total=n, desc="Generating videos")
        for title in titles:
            if attempts == n:
                break

            try:
                (
                    title,
                    description,
                    script,
                    fact_check_corrections,
                    search_terms,
                    tags,
                    hook_caption,
                    stock_videos,
                    voiceover,
                ) = generate_video_data(title, hook_style, records)

                logging.debug(f"Title: {title}")
                logging.debug(f"Description: {description}")
                logging.debug(f"Script: {script}")
                logging.debug(f"Search terms: {search_terms}")
                logging.debug(f"Tags: {tags}")
                logging.debug(f"Hook caption: {hook_caption}")
                logging.debug(f"Stock videos: {stock_videos}")
                logging.debug(f"Voiceover: {voiceover}")

                video = generate_video(
                    stock_videos, voiceover, hook_caption=hook_caption
                )
                logger.info("[Generated Video]")

                new_video_file = save_metadata(
                    title,
                    description,
                    topic,
                    script,
                    search_terms,
                    video,
                    hook_style=hook_style,
                    tags=tags,
                    hook_caption=hook_caption,
                    fact_check_corrections=fact_check_corrections,
                    review_status="pending" if REVIEW_BEFORE_UPLOAD else None,
                )
                logger.info("[Saved Video]")

                if not REVIEW_BEFORE_UPLOAD:
                    uploaded_video = auto_upload(
                        new_video_file, title, description, tags
                    )
                    if uploaded_video:
                        record_upload(new_video_file, uploaded_video)
                        logger.info("[Uploaded Video]")
                        logger.info(uploaded_video["id"])
                videos_generated += 1

            except FactCheckFailed as e:
                logger.warning(f"Skipping '{title}', it failed the fact check: {e}")
                continue

            except Exception as e:
                error_msg = f"Failed to generate/upload video '{title}'"
                logger.error(f"{error_msg}: {e}")
                send_error_notification(error_msg, e, "Video Generation")

            attempts += 1
            progress.update()

        progress.close()

        if videos_generated > 0 and REVIEW_BEFORE_UPLOAD:
            send_action_notification(
                f"{videos_generated} new video(s) are waiting for review, "
                "run `python review.py` to approve them for upload",
                "Review",
            )
        elif videos_generated > 0:
            success_msg = (
                f"Successfully generated and uploaded {videos_generated} video(s)"
            )
            logger.info(success_msg)
            send_success_notification(success_msg, "Video Generation")
        else:
            error_msg = "No videos were successfully generated"
            logger.error(error_msg)
            send_error_notification(error_msg, context="Video Generation")

    except Exception as e:
        error_msg = "Failed to start video generation process"
        logger.error(f"{error_msg}: {e}")
        send_error_notification(error_msg, e, "Video Generation")


def main():
    cron_schedule = CRON_SCHEDULE
    run_once = RUN_ONCE
    video_count = VIDEO_COUNT

    if run_once:
        logger.info("RUN_ONCE is enabled, generating videos immediately...")
        generate_videos(video_count)
        logger.info("Video generation completed. Exiting.")
        return

    logger.info(f"Starting scheduler with cron schedule: {cron_schedule}")
    scheduler = BlockingScheduler()

    trigger = CronTrigger.from_crontab(cron_schedule)
    scheduler.add_job(
        func=generate_videos, trigger=trigger, args=[video_count], id="video_generation"
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        scheduler.shutdown()
    except Exception as e:
        error_msg = "Scheduler failed unexpectedly"
        logger.error(f"{error_msg}: {e}")
        send_error_notification(error_msg, e, "Scheduler")


if __name__ == "__main__":
    main()
