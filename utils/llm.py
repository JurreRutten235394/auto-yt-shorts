import json
import logging
from typing import List, Tuple

import requests
from openai import OpenAI

from config import (
    CHANNEL_NICHE,
    HOOK_STYLES,
    NEWS_API_KEY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    POSSIBLE_TOPICS,
)
from utils.performance import choose, format_examples

logger = logging.getLogger(__name__)

# Initialize OpenAI client with optional base URL
client_kwargs = {"api_key": OPENAI_API_KEY}
if OPENAI_BASE_URL:
    logger.info(f"Using OpenAI base URL: {OPENAI_BASE_URL}")
    client_kwargs["base_url"] = OPENAI_BASE_URL

client = OpenAI(**client_kwargs)

_base_prompt = f"""
You are a passionate Tiktok creator and you want to create more short form content. Your videos contain a voiceover, stock footage and subtitles. 
Your channel is about {CHANNEL_NICHE}, and every video is made for people who are interested in that.
The content of the video is one informative, interesting or mind-blowing fact about the topic which people will find interesting.
Every fact must be true and well documented. Never invent, exaggerate or speculate.
Your videos are not too complex, they should bring the message across in a simple and engaging way.
"""

# A script gets this many checks to pass, with corrections in between
FACT_CHECK_ROUNDS = 3


class FactCheckFailed(Exception):
    pass


def get_topic(records: List[dict] = ()) -> str:
    return choose(POSSIBLE_TOPICS, records, "topic")


def get_hook_style(records: List[dict] = ()) -> str:
    return choose(list(HOOK_STYLES), records, "hook_style")


def _hook_formula(hook_style: str) -> str:
    examples = ", ".join(f'"{example}"' for example in HOOK_STYLES[hook_style])
    return f"- {hook_style}: {examples}"


def get_titles(topic: str, hook_style: str, records: List[dict] = ()) -> List[str]:
    _prompt = (
        _base_prompt
        + f"""
The next message will contain the name of the topic, that you want to make a Tiktok about.
The length of the video should be between 15 and 30 seconds.

Generate highly engaging titles that will stop users from scrolling. The FIRST 3 WORDS are CRITICAL - they must immediately grab attention.

Use this proven viral title formula:
{_hook_formula(hook_style)}

REQUIREMENTS:
- Include a famous person, brand, or well-known entity when possible
- Focus on ONE specific shocking/interesting fact
- Create curiosity gaps that demand answers
- Use power words: secret, revealed, discovered, shocking, hidden, truth, exposed
- Make the first 3 words irresistible
- Only promise what a 30 second video about a true fact can deliver

{format_examples(records)}
"""
        + """
Respond with JSON in the following format:
{
    "titles": [
        "Title 1",
        ...
        "Title n"
    ]
}
    """
    )

    response = (
        client.chat.completions.create(
            messages=[
                {"role": "system", "content": _prompt},
                {"role": "user", "content": topic},
            ],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    return json.loads(response)["titles"]

    ...


def get_news_topics() -> List[str]:
    news = requests.get(
        f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    ).json()

    return [
        article["description"] for article in news["articles"] if article["description"]
    ]


def filter_by_spicyness(titles: List[str]) -> List[str]:
    _prompt = (
        _base_prompt
        + """
You will be presented with a list of possible headline for your video and a corresponding number. 
Your goal is to make the most engaging video by using spicy news headlines that will attract the most attention.
You are now a classification model to tell me whether the title is spicy or not.

respond with JSON in the following format:
{
    "spicy_titles": [n, m, ...]
}
"""
    )

    response = (
        client.chat.completions.create(
            messages=[
                {"role": "system", "content": _prompt},
                {
                    "role": "user",
                    "content": "\n".join(
                        [f"{i+1}. {title}" for i, title in enumerate(titles)]
                    ),
                },
            ],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )
    return [
        titles[i - 1]
        for i in dict.fromkeys(json.loads(response)["spicy_titles"])
        if 1 <= i <= len(titles) and titles[i - 1]
    ]


def get_most_engaging_titles(titles: List[str], n: int = 1) -> List[str]:
    _prompt = (
        _base_prompt
        + """
You will be presented with a list of possible title for your video and a corresponding number.
Sort the titles by the most engaging one first and respond with a list of indices.
They should have a name of a famous person, event, product or company, choose the one that is most engaging.

Respond with JSON in the following format:
{
    "most_engaging_titles": [n, m, ...]
}
"""
    )

    response = (
        client.chat.completions.create(
            messages=[
                {"role": "system", "content": _prompt},
                {
                    "role": "user",
                    "content": "\n".join(
                        [f"{i+1}. {title}" for i, title in enumerate(titles)]
                    ),
                },
            ],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    most_engaging_titles = json.loads(response)["most_engaging_titles"]

    # The titles were numbered from 1 in the prompt
    sorted_titles = [
        titles[i - 1]
        for i in dict.fromkeys(most_engaging_titles)
        if 1 <= i <= len(titles) and titles[i - 1]
    ]

    return sorted_titles[: n if n < len(sorted_titles) else len(sorted_titles)]


def get_best_title(titles: List[str]) -> str:
    _prompt = (
        _base_prompt
        + """
You will be presented with a list of possible title for your video and a corresponding number. 
Respond with the best, most engaging title for your video. 
It should have a name of a famous person, event, product or company, choose the one that is most engaging.

Respond with JSON in the following format:
{
    "best_title_index": n
}

"""
    )

    response = (
        client.chat.completions.create(
            messages=[
                {"role": "system", "content": _prompt},
                {
                    "role": "user",
                    "content": "\n".join(
                        [f"{i+1}. {title}" for i, title in enumerate(titles)]
                    ),
                },
            ],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    best_title_index = json.loads(response)["best_title_index"]
    return titles[best_title_index - 1]


def get_description(title: str, script: str) -> str:
    _prompt = (
        _base_prompt
        + f"""
You have decided that your video is about {title}.
The Script for your video is:
{script}

Create a compelling caption that amplifies engagement and encourages interaction. The description should complement the video content and drive more views.

DESCRIPTION STRATEGY:
- Start with a hook that reinforces the video's intrigue
- Include a call-to-action that encourages comments
- Use relevant hashtags strategically
- Create FOMO (fear of missing out)
- Ask questions that spark debate or discussion

STRUCTURE:
1. Hook line (builds on video's shock value)
2. Engagement question or controversial statement
3. Call-to-action for comments/shares
4. Strategic hashtags

EXAMPLES OF ENGAGEMENT TACTICS:
- "Wait until you see what happens next..."
- "This blew my mind - did you know this?"
- "Comment 'MIND BLOWN' if this shocked you"
- "Tag someone who needs to see this"
- "Most people have no idea about this..."

Keep it concise but impactful. Focus on maximizing comments and shares.

Do not under any circumstance reference this prompt in your response.

ONLY RETURN THE RAW DESCRIPTION. DO NOT RETURN ANYTHING ELSE.
"""
    )

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "text"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content.strip()
    )

    return response


def get_script(title: str, hook_style: str, records: List[dict] = ()) -> str:
    _prompt = (
        _base_prompt
        + f"""
You have decided on the title for your video: "{title}".

Create a script that hooks viewers IMMEDIATELY. The first 3-5 words are CRITICAL - they determine if someone keeps watching or scrolls away.

SCRIPT STRUCTURE:
1. HOOK (0-3 seconds): Start with an attention-grabbing opener that creates instant intrigue
2. REVELATION (3-15 seconds): Deliver the shocking/interesting fact with specific details
3. IMPACT (15-27 seconds): Explain why this matters
4. LOOP (last sentence): End on a phrase that leads straight back into the opening line, so the Short sounds like one continuous thought when it replays.
   For example, a script that opens with "Nobody can explain the Voynich manuscript." could end with "...and that's exactly why"

OPENING HOOK FORMULA:
{_hook_formula(hook_style)}

REQUIREMENTS:
- NO introductions, greetings, or "welcome" phrases
- Jump straight into the hook within the first 3 words
- Use conversational, natural speech patterns
- Include specific names, numbers, or details when possible
- Create curiosity that demands immediate answers
- No sign-off, summary or call to action at the end: the last sentence must loop back into the first
- 15-30 seconds of speaking time

TONE: Conversational but urgent, like you're sharing an incredible secret with a friend.

{format_examples(records, include_scripts=True)}

ONLY RETURN THE RAW SCRIPT. DO NOT RETURN ANYTHING ELSE.
"""
    )

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "text"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content.strip()
    )

    return response


def get_search_terms(title: str, script: str) -> list:
    _prompt = (
        _base_prompt
        + f"""
You have decided on the title for your video: "{title}".
The Script for your video is:
{script}

You will now generate an appropriate amount search terms for the stock footage for your video.
"""
        + """

The stock footage should be related to the content of the video and the the video.

Make sure that the search terms are in the order that they appear in the script and that they are relevant to the content of the video.
Also make sure the amount of search terms is appropriate for the length of the video.

Respond with JSON in the following format:
{
    "search_terms": [
        "Search Term 1",
        ...
        "Search Term n"
    ]
}
"""
    )

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    return json.loads(response)["search_terms"]


def get_tags(title: str, script: str) -> List[str]:
    _prompt = (
        _base_prompt
        + f"""
You have decided on the title for your video: "{title}".
The Script for your video is:
{script}

Generate 5 to 10 YouTube tags for the video: the people, brands, places and subjects it is about, and the phrases someone would search to find it.
"""
        + """
Respond with JSON in the following format:
{
    "tags": [
        "Tag 1",
        ...
        "Tag n"
    ]
}
"""
    )

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    return _fit_tag_limit(json.loads(response)["tags"])


def _fit_tag_limit(tags: List[str], limit: int = 500) -> List[str]:
    """Keep as many tags as fit YouTube's 500 character limit.

    The separating commas count towards the limit, and so do the quotes YouTube
    adds around tags that contain spaces.
    """
    kept, used = [], 0
    for tag in tags:
        tag = tag.replace("<", "").replace(">", "").strip().lstrip("#")
        if not tag:
            continue

        cost = len(tag) + (2 if " " in tag else 0) + (1 if kept else 0)
        if used + cost > limit:
            break

        kept.append(tag)
        used += cost

    return kept


def check_facts(title: str, script: str) -> Tuple[str, List[str]]:
    """Fact check the script, correcting it if needed.

    Returns the script that passed and the problems that were corrected on the
    way. Raises FactCheckFailed when the video can't be made accurate.
    """
    corrections = []
    for _ in range(FACT_CHECK_ROUNDS):
        result = _fact_check(title, script)

        if result.get("verdict") == "pass":
            return script, corrections

        if result.get("verdict") == "fix" and result.get("script"):
            logger.info(f"[Fact Check Corrections] {result.get('issues')}")
            corrections += result.get("issues") or []
            script = result["script"]
            continue

        raise FactCheckFailed("; ".join(result.get("issues") or ["no reason given"]))

    raise FactCheckFailed(f"didn't pass after {FACT_CHECK_ROUNDS} checks")


def _fact_check(title: str, script: str) -> dict:
    _prompt = f"""
You are a strict fact checker for a YouTube channel about {CHANNEL_NICHE}. Check this Short before it is published.

Title: "{title}"
Script:
{script}

Check every factual claim: names, numbers, dates, records, quotes and causes. A claim only passes if it is well documented and you are confident it is true. These are problems:
- claims that are false, disputed, outdated or that you can't confirm
- numbers or details that are more precise than the evidence supports
- accusations against real people or companies that aren't established fact
- a title that promises something the script doesn't deliver

Then decide on a verdict:
- "pass" if there are no problems
- "fix" if correcting or removing the problems still leaves a good video. Rewrite the script with the smallest changes that make it accurate, keeping its opening hook, its last sentence that loops back into the opening, and its length.
- "reject" if the title or the main fact is wrong, so no correction can save the video
"""
    _prompt += """
Respond with JSON in the following format:
{
    "verdict": "pass | fix | reject",
    "issues": ["What is wrong and why", ...],
    "script": "The corrected script if the verdict is fix, otherwise the original script"
}
"""

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "json_object"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content
    )

    return json.loads(response)


def get_hook_caption(title: str, script: str) -> str:
    _prompt = (
        _base_prompt
        + f"""
You have decided on the title for your video: "{title}".
The Script for your video is:
{script}

Write the text that is shown big on screen during the first 3 seconds, while the voiceover starts. It's the first thing a viewer sees and decides whether to keep watching.

REQUIREMENTS:
- 3 to 7 words
- Makes the viewer curious about the fact without giving it away
- Matches what the title promises and what the voiceover says first
- No hashtags, emojis or quotation marks

ONLY RETURN THE RAW TEXT. DO NOT RETURN ANYTHING ELSE.
"""
    )

    response = (
        client.chat.completions.create(
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "text"},
            model=OPENAI_MODEL,
        )
        .choices[0]
        .message.content.strip()
    )

    return response.strip('"')
