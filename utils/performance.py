import math
import random
import statistics
from typing import List, Sequence

from config import ANALYTICS_WINDOW_DAYS

# How many average videos each option is assumed to have before its own
# results come in. Higher values take longer to trust a few lucky videos.
PRIOR_WEIGHT = 1


def score(metadata: dict) -> float:
    """How far YouTube spread the video in its first days, on a log scale so one viral hit doesn't drown out the rest."""
    stats = metadata["stats"]
    return math.log1p(stats.get("engagedViews", stats.get("views", 0)))


def finished(records: List[dict]) -> List[dict]:
    """Videos whose stats window has closed and whose stats are complete."""
    return [record for record in records if record.get("stats_final")]


def choose(options: Sequence[str], records: List[dict], field: str, rng=random) -> str:
    """Pick one of `options` by Thompson sampling over past videos' scores.

    Options that did well get picked more often, while options with few or no
    videos keep getting tried because their estimate is still uncertain.
    """
    scores = {option: [] for option in options}
    for record in finished(records):
        if record.get(field) in scores:
            scores[record[field]].append(score(record))

    all_scores = [s for option_scores in scores.values() for s in option_scores]
    if not all_scores:
        return rng.choice(list(options))

    prior_mean = statistics.fmean(all_scores)
    spread = statistics.pstdev(all_scores) or 1.0

    def draw(option_scores: List[float]) -> float:
        weight = PRIOR_WEIGHT + len(option_scores)
        mean = (PRIOR_WEIGHT * prior_mean + sum(option_scores)) / weight
        return rng.gauss(mean, spread / math.sqrt(weight))

    return max(options, key=lambda option: draw(scores[option]))


def format_examples(
    records: List[dict], include_scripts: bool = False, count: int = 3
) -> str:
    """The best and worst past videos as prompt context, or "" until there are enough of them."""
    ranked = sorted(finished(records), key=score, reverse=True)
    if len(ranked) < 2 * count:
        return ""

    def describe(record: dict) -> str:
        stats = record["stats"]
        views = stats.get("views", 0)
        engaged_views = stats.get("engagedViews", 0)
        line = (
            f'- "{record["title"]}": {engaged_views:,} engaged views, '
            f'{stats.get("averageViewPercentage", 0):.0f}% of the video watched on average'
        )
        if views:
            line += f", {engaged_views / views:.0%} of viewers kept watching"
        if include_scripts:
            line += f'\n  Script: {record["script"]}'
        return line

    return "\n".join(
        [
            f"Here is how viewers responded to this channel's past videos in their first {ANALYTICS_WINDOW_DAYS} days.",
            "BEST PERFORMING:",
            *[describe(record) for record in ranked[:count]],
            "WORST PERFORMING:",
            *[describe(record) for record in ranked[-count:]],
            "Work out what the best ones do differently from the worst ones and apply it. Do not copy them.",
        ]
    )
