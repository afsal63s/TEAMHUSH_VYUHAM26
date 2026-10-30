"""Research agent: finds real articles and videos for ONE concept.

A small tool-calling loop (no LangGraph): the model may call search_articles and search_videos for a
few turns. Every result is registered as a candidate with an id (a1, a2, v1, ...). A final structured
call picks resources BY ID, so the model can never invent a URL: code maps ids back to real results.
Research must never break learning, so any failure returns [] (or a rank-based fallback).
"""

import asyncio
import logging
from collections.abc import Callable, Sequence

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from research import tools
from schemas.content import Concept, Level, Resource

logger = logging.getLogger(__name__)

MAX_TURNS = 5
MAX_ARTICLES, MAX_VIDEOS = 2, 1
TIMEOUT_SECONDS = 90
TRANSCRIPT_CHARS = 600

AGENT_SYSTEM = (
    "You find learning resources for ONE concept. Call search_articles up to twice and search_videos "
    "up to twice, with specific queries that include the topic, the concept and the learner's level. "
    "Prefer tutorials and clear explanations over news, product pages or lists. When you have "
    "enough results, reply with the single word: done."
)
PICK_SYSTEM = (
    "You choose the best learning resources for one concept from a numbered list. Use ONLY ids from "
    "the list. Prefer clear explanations that match the learner's level and, if misconceptions are "
    "given, resources likely to address them. Reject off-topic, promotional or news results. "
    f"Choose at most {MAX_ARTICLES} articles and {MAX_VIDEOS} video."
)


class PickDraft(BaseModel):
    article_ids: list[str] = Field(description="ids of the best articles, best first")
    video_ids: list[str] = Field(description="ids of the best video")


@tool
def search_articles(query: str) -> str:
    """Search the web for articles that teach the concept."""
    return ""  # schema only; calls are dispatched by _run_tool


@tool
def search_videos(query: str) -> str:
    """Search YouTube for videos that teach the concept."""
    return ""  # schema only; calls are dispatched by _run_tool


class Candidates:
    """Every real search result seen in one research run, keyed by a short id."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self._count = {"article": 0, "video": 0}

    def add(self, kind: str, rows: Sequence[dict]) -> list[tuple[str, dict]]:
        added = []
        for row in rows:
            url = row.get("url")
            if not url or any(c["url"] == url for c in self.items.values()):
                continue
            self._count[kind] += 1
            cid = f"{'a' if kind == 'article' else 'v'}{self._count[kind]}"
            self.items[cid] = {**row, "kind": kind}
            added.append((cid, self.items[cid]))
        return added


def to_resource(row: dict) -> Resource:
    return Resource(kind=row["kind"], title=row["title"], url=row["url"], snippet=row.get("snippet", ""))


def resolve_picks(pick: PickDraft, cands: Candidates) -> list[Resource]:
    """Map picked ids to real results. Unknown ids are dropped, never turned into URLs."""
    out: list[Resource] = []
    for ids, limit in ((pick.article_ids, MAX_ARTICLES), (pick.video_ids, MAX_VIDEOS)):
        for cid in ids[:limit]:
            row = cands.items.get(cid)
            if row:
                out.append(to_resource(row))
    return out


def fallback_picks(cands: Candidates) -> list[Resource]:
    """Top-ranked article and video, used when the picker fails or picks nothing usable."""
    first = lambda prefix: next((r for cid, r in cands.items.items() if cid.startswith(prefix)), None)
    return [to_resource(r) for r in (first("a"), first("v")) if r]


async def _run_tool(
    name: str,
    args: dict,
    cands: Candidates,
    articles_fn: Callable[[str], list[dict]],
    videos_fn: Callable[[str], list[dict]],
) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "error: empty query"
    if name == "search_articles":
        kind, fn = "article", articles_fn
    elif name == "search_videos":
        kind, fn = "video", videos_fn
    else:
        return f"error: unknown tool {name}"
    try:
        rows = await asyncio.to_thread(fn, query)
    except Exception as exc:
        logger.warning("%s failed: %s", name, exc)
        return f"error: {type(exc).__name__}"
    added = cands.add(kind, rows)
    return "\n".join(f"[{cid}] {r['title']} - {r['snippet'][:160]}" for cid, r in added) or "no new results"


def _spend_hooks() -> tuple[Callable[[], None], Callable[[str, dict | None], None]]:
    """The generation layer's spend guard and usage log, so research counts toward MAX_SPEND_USD."""
    from generation import llm

    return llm._check_spend, llm._record_usage


def _chat():
    from langchain_anthropic import ChatAnthropic

    from config import get_settings

    s = get_settings()
    return ChatAnthropic(
        model=s.MODEL_CHEAP, api_key=s.ANTHROPIC_API_KEY, max_tokens=1000,
        default_request_timeout=60, max_retries=0,
    )


async def _default_pick(topic: str, concept: Concept, level: Level, targets: Sequence[str],
                        cands: Candidates) -> PickDraft:
    from generation.llm import structured_completion

    listing = "\n".join(
        f"[{cid}] ({r['kind']}) {r['title']} - {r['snippet'][:200]}" for cid, r in cands.items.items()
    )
    wanted = "\n".join(f"- {t}" for t in targets) or "none"
    user = (
        f"Topic: {topic}\nConcept: {concept.name}: {concept.description}\nLearner level: {level}\n"
        f"Misconceptions to address:\n{wanted}\n\nCandidates:\n{listing}"
    )
    return await structured_completion("cheap", PICK_SYSTEM, user, PickDraft, max_tokens=1500)


async def _research(topic, concept, level, targets, llm, articles_fn, videos_fn, pick_fn,
                    use_transcripts) -> list[Resource]:
    check_spend, record_usage = _spend_hooks()
    cands = Candidates()
    model = (llm or _chat()).bind_tools([search_articles, search_videos])
    wanted = "; ".join(targets) or "none"
    messages = [
        SystemMessage(content=AGENT_SYSTEM),
        HumanMessage(content=(
            f"Topic: {topic}\nConcept: {concept.name}: {concept.description}\n"
            f"Learner level: {level}\nMisconceptions to address: {wanted}"
        )),
    ]
    for _ in range(MAX_TURNS):
        check_spend()
        reply = await model.ainvoke(messages)
        record_usage("cheap", getattr(reply, "usage_metadata", None))
        messages.append(reply)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            out = await _run_tool(call["name"], call.get("args") or {}, cands, articles_fn, videos_fn)
            messages.append(ToolMessage(content=out, tool_call_id=call["id"]))

    if not cands.items:
        return []
    try:
        pick = await (pick_fn or _default_pick)(topic, concept, level, targets, cands)
        resources = resolve_picks(pick, cands)
    except Exception as exc:
        logger.warning("picker failed for %s: %s", concept.id, exc)
        resources = []
    if not resources:  # nothing usable picked: show the top-ranked results rather than none
        resources = fallback_picks(cands)

    if use_transcripts:
        for r in resources:
            if r.kind == "video":
                text = await asyncio.to_thread(tools.get_video_transcript, r.url)
                if text:
                    r.snippet = text[:TRANSCRIPT_CHARS]
    return resources


async def research_concept(
    topic: str,
    concept: Concept,
    level: Level = "beginner",
    target_misconceptions: Sequence[str] = (),
    *,
    llm=None,
    articles_fn: Callable[[str], list[dict]] | None = None,
    videos_fn: Callable[[str], list[dict]] | None = None,
    pick_fn=None,
    use_transcripts: bool = True,
) -> list[Resource]:
    """Real articles and videos for one concept. Never raises (except for the spend limit)."""
    try:
        return await asyncio.wait_for(
            _research(
                topic, concept, level, list(target_misconceptions), llm,
                articles_fn or tools.search_articles, videos_fn or tools.search_videos,
                pick_fn, use_transcripts,
            ),
            TIMEOUT_SECONDS,
        )
    except Exception as exc:
        from generation.llm import SpendLimitError

        if isinstance(exc, SpendLimitError):
            raise
        logger.warning("research failed for %s: %s: %s", concept.id, type(exc).__name__, exc)
        return []