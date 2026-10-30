"""Thin, synchronous wrappers over Tavily and the YouTube Data API.

Clients are created lazily, so a missing key only matters when research actually runs
(the app still boots without Tavily/YouTube keys). Every function returns plain dicts
{"kind", "title", "url", "snippet"} that the agent turns into schemas.content.Resource.
"""

import logging
import re
from functools import lru_cache

from config import get_settings

logger = logging.getLogger(__name__)

SNIPPET_CHARS = 400
_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})")


@lru_cache(maxsize=1)
def _tavily():
    from langchain_tavily import TavilySearch

    key = get_settings().TAVILY_API_KEY.get_secret_value()
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set")
    return TavilySearch(
        max_results=5, topic="general", search_depth="basic", include_raw_content=False, tavily_api_key=key
    )


@lru_cache(maxsize=1)
def _youtube():
    from googleapiclient.discovery import build

    key = get_settings().YOUTUBE_API_KEY.get_secret_value()
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY is not set")
    return build("youtube", "v3", developerKey=key, cache_discovery=False)


def search_articles(query: str, max_results: int = 5) -> list[dict]:
    """Web articles for a query. Raises if Tavily is not configured."""
    raw = _tavily().invoke({"query": query})
    rows = raw.get("results", []) if isinstance(raw, dict) else []
    return [
        {
            "kind": "article",
            "title": (r.get("title") or "").strip(),
            "url": r.get("url") or "",
            "snippet": (r.get("content") or "").strip()[:SNIPPET_CHARS],
        }
        for r in rows[:max_results]
        if r.get("url")
    ]


def search_videos(query: str, max_results: int = 5) -> list[dict]:
    """YouTube videos for a query. Raises if the YouTube key is not configured."""
    response = (
        _youtube()
        .search()
        .list(
            q=query, part="snippet", type="video", maxResults=max_results,
            videoEmbeddable="true", safeSearch="strict",
        )
        .execute()
    )
    out = []
    for item in response.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet", {})
        out.append(
            {
                "kind": "video",
                "title": (snippet.get("title") or "").strip(),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "snippet": (snippet.get("description") or "").strip()[:SNIPPET_CHARS],
            }
        )
    return out


def video_id_from_url(url: str) -> str | None:
    match = _VIDEO_ID.search(url)
    return match.group(1) if match else None


def get_video_transcript(video_url: str) -> str | None:
    """Transcript text for a YouTube video, or None if unavailable (disabled, blocked, no key needed)."""
    video_id = video_id_from_url(video_url)
    if not video_id:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id)
        return " ".join(piece.text for piece in fetched)
    except Exception as exc:  # transcripts are flaky from cloud IPs; never let that break research
        logger.info("no transcript for %s: %s", video_id, type(exc).__name__)
        return None