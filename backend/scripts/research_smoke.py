"""Live smoke test of the research agent against the real LLM, Tavily and YouTube.

Usage: uv run python scripts/research_smoke.py

Runs research_concept for 2 concepts of fixtures/python_novice.json, each with one target
misconception, and checks that every returned URL appeared in a real search result. Prints
resources, elapsed time and LLM spend. Never prints API keys: all output is scrubbed.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from config import get_settings  # noqa: E402
from generation import CourseBundle  # noqa: E402
from generation.llm import spend_summary  # noqa: E402
from research import tools  # noqa: E402
from research.agent import research_concept  # noqa: E402

FIXTURE = ROOT / "fixtures" / "python_novice.json"
S = get_settings()
SECRETS = [k for k in (S.ANTHROPIC_API_KEY.get_secret_value(), S.TAVILY_API_KEY.get_secret_value(),
                       S.YOUTUBE_API_KEY.get_secret_value(), S.MASTER_PASSWORD.get_secret_value()) if k]


def scrub(text: str) -> str:
    for k in SECRETS:
        text = text.replace(k, "<redacted>")
    return text


class ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = scrub(record.getMessage()), ()
        return True


def say(text: str = "") -> None:
    print(scrub(text))


class Recorder:
    """Real search functions, wrapped to record every URL returned and every failure."""

    def __init__(self) -> None:
        self.urls: set[str] = set()
        self.calls: list[str] = []
        self.errors: list[str] = []

    def wrap(self, name, fn):
        def run(query: str) -> list[dict]:
            t = time.monotonic()
            try:
                rows = fn(query)
            except Exception as exc:
                status = getattr(getattr(exc, "resp", None), "status", None) or getattr(exc, "status_code", None)
                self.errors.append(f"{name}: {type(exc).__name__}" + (f" (HTTP {status})" if status else "")
                                   + f": {scrub(str(exc))[:300]}")
                raise
            self.urls |= {r["url"] for r in rows}
            self.calls.append(f"{name}({query!r}) -> {len(rows)} results in {time.monotonic() - t:.1f} s")
            return rows
        return run


async def main() -> int:
    handler = logging.StreamHandler()
    handler.addFilter(ScrubFilter())
    logging.basicConfig(level=logging.WARNING, handlers=[handler], format="  log %(levelname)s %(name)s: %(message)s")
    missing = [n for n, k in (("ANTHROPIC_API_KEY", S.ANTHROPIC_API_KEY), ("TAVILY_API_KEY", S.TAVILY_API_KEY),
                              ("YOUTUBE_API_KEY", S.YOUTUBE_API_KEY)) if not k.get_secret_value()]
    if missing:
        say(f"missing keys: {missing}")
        return 1

    bundle = CourseBundle.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    picks = []
    for c in bundle.graph.concepts:
        mis = [m for m in bundle.graph.misconceptions if m.concept_id == c.id]
        if mis:
            picks.append((c, mis[0]))
        if len(picks) == 2:
            break

    ok = True
    for concept, mis in picks:
        rec = Recorder()
        say(f"\n=== {concept.id} ({bundle.level}); target misconception: {mis.tag}: {mis.description}")
        t = time.monotonic()
        resources = await research_concept(
            bundle.graph.topic, concept, bundle.level, [mis.description],
            articles_fn=rec.wrap("search_articles", tools.search_articles),
            videos_fn=rec.wrap("search_videos", tools.search_videos),
        )
        elapsed = time.monotonic() - t
        for line in rec.calls:
            say(f"  {line}")
        for line in rec.errors:
            say(f"  ERROR {line}")
        for r in resources:
            say(f"  [{r.kind}] {r.title}\n      {r.url}\n      {r.snippet[:120]!r}")
        unknown = [r.url for r in resources if r.url not in rec.urls]
        kinds = {r.kind for r in resources}
        say(f"  {len(resources)} resources ({', '.join(sorted(kinds)) or 'none'}) in {elapsed:.1f} s; "
            f"every URL came from a search result: {not unknown}{f' (unknown: {unknown})' if unknown else ''}")
        if not resources or unknown or rec.errors:
            ok = False
    say(f"\n{spend_summary()}")
    say("RESEARCH SMOKE " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
