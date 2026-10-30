"""Find a ready-made course bundle on disk: .cache/<hash>.json first, then any fixtures/*.json."""

import json
import logging
from pathlib import Path

from generation import CourseBundle, prompt_hash
from schemas.content import Level

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
FIXTURES_DIR = ROOT / "fixtures"


def _load(path: Path) -> CourseBundle | None:
    try:
        return CourseBundle.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        logger.warning("skipping unreadable bundle %s: %s", path, exc)
        return None


def find_bundle(prompt: str, level: Level) -> CourseBundle | None:
    h = prompt_hash(prompt, level)
    cached = CACHE_DIR / f"{h}.json"
    if cached.exists() and (bundle := _load(cached)):
        return bundle
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        bundle = _load(path)
        if bundle and prompt_hash(bundle.prompt, bundle.level) == h:
            return bundle
    return None


def cache_bundle(bundle: CourseBundle) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{prompt_hash(bundle.prompt, bundle.level)}.json"
    path.write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")
