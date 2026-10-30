"""Generate one course bundle, cache it in .cache/<hash>.json, and print a summary.

Usage: uv run python scripts/gen_course.py "<prompt>" [--level novice|beginner|intermediate|advanced]
"""

import argparse
import asyncio
import hashlib
import json
import logging
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generation.bundle import CourseBundle  # noqa: E402
from generation.course_gen import generate_course  # noqa: E402
from generation.llm import spend_summary  # noqa: E402
from generation.prompts import DEFAULT_LEVEL, LEVEL_GUIDE  # noqa: E402

CACHE_DIR = ROOT / ".cache"


def cache_path(prompt: str, level: str) -> Path:
    key = f"{' '.join(prompt.lower().split())}|{level}"
    return CACHE_DIR / f"{hashlib.sha1(key.encode()).hexdigest()[:12]}.json"


def print_summary(bundle: CourseBundle) -> None:
    graph = bundle.graph
    roots = [c.id for c in graph.concepts if not c.prerequisites]
    print(f"\ncourse {bundle.course_id}: {graph.topic} (level {bundle.level})")
    print(f"{len(graph.concepts)} concepts ({len(roots)} roots), {len(graph.misconceptions)} catalog misconceptions")
    for c in graph.concepts:
        count = sum(q.concept_id == c.id for q in bundle.questions)
        print(f"  {c.id:<32} prereqs={c.prerequisites} questions={count}")
    kinds = {k: sum(q.kind == k for q in bundle.questions) for k in ("diagnostic", "practice", "transfer")}
    print(f"{len(bundle.questions)} questions: {kinds}")


def print_questions(bundle: CourseBundle, n: int) -> None:
    for q in random.sample(bundle.questions, min(n, len(bundle.questions))):
        print(f"\n[{q.id}] ({q.kind}, difficulty {q.difficulty})\n{q.prompt}")
        for i, o in enumerate(q.options):
            print(f" {'*' if i == q.correct_index else ' '} {i}. {o.text}   <{o.misconception_tag}>")
        print(f"  why: {q.explanation}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--level", choices=list(LEVEL_GUIDE), default=DEFAULT_LEVEL)
    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("generation").setLevel(logging.INFO)  # per-call token log

    try:
        bundle = await generate_course(args.prompt, level=args.level)
    finally:
        print(spend_summary())
    path = cache_path(args.prompt, args.level)
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")
    print_summary(bundle)
    print_questions(bundle, 5)
    print(f"\nsaved {path}")


if __name__ == "__main__":
    asyncio.run(main())
