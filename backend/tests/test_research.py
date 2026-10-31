"""No network, no keys: the model, the searches and the picker are all faked."""

import asyncio

from langchain_core.messages import AIMessage

from research import agent, tools
from research.agent import Candidates, PickDraft
from schemas.content import Concept

CONCEPT = Concept(id="loops", name="Loops", description="repeat code", prerequisites=[])
ARTICLES = [
    {"kind": "article", "title": "Loops 101", "url": "https://a.example/1", "snippet": "for and while"},
    {"kind": "article", "title": "Loops deep", "url": "https://a.example/2", "snippet": "iteration"},
]
VIDEOS = [{"kind": "video", "title": "Loops video", "url": "https://www.youtube.com/watch?v=abcdefghijk", "snippet": "d"}]


class FakeLLM:
    """First turn asks for both searches; second turn says done."""

    def __init__(self, turns=None):
        self.turns = list(turns or [
            AIMessage(content="", tool_calls=[
                {"name": "search_articles", "args": {"query": "python loops"}, "id": "t1"},
                {"name": "search_videos", "args": {"query": "python loops"}, "id": "t2"},
            ]),
            AIMessage(content="done"),
        ])

    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, _messages):
        return self.turns.pop(0)


def _patch(monkeypatch):
    monkeypatch.setattr(agent, "_spend_hooks", lambda: (lambda: None, lambda role, usage: None))


def run(pick, monkeypatch, **kw):
    _patch(monkeypatch)

    async def pick_fn(*_a):
        return pick

    return asyncio.run(agent.research_concept(
        "Python", CONCEPT, "novice", ["believes range(n) runs n+1 times"],
        llm=kw.pop("llm", FakeLLM()), articles_fn=lambda q: ARTICLES, videos_fn=lambda q: VIDEOS,
        pick_fn=pick_fn, use_transcripts=False, **kw,
    ))


def test_candidates_get_ids_and_dedupe():
    c = Candidates()
    first = c.add("article", ARTICLES + [ARTICLES[0]])
    assert [cid for cid, _ in first] == ["a1", "a2"]
    assert [cid for cid, _ in c.add("video", VIDEOS)] == ["v1"]
    assert c.add("article", ARTICLES) == []


def test_picks_map_to_real_urls_only(monkeypatch):
    out = run(PickDraft(article_ids=["a2", "a99"], video_ids=["v1"]), monkeypatch)
    assert [r.url for r in out] == ["https://a.example/2", "https://www.youtube.com/watch?v=abcdefghijk"]


def test_invented_ids_never_become_urls(monkeypatch):
    out = run(PickDraft(article_ids=["https://evil.example"], video_ids=[]), monkeypatch)
    assert all(r.url.startswith(("https://a.example", "https://www.youtube.com")) for r in out)


def test_fallback_when_nothing_usable_is_picked(monkeypatch):
    out = run(PickDraft(article_ids=["zzz"], video_ids=[]), monkeypatch)
    assert [r.kind for r in out] == ["article", "video"]
    assert out[0].url == "https://a.example/1"


def test_picker_failure_falls_back(monkeypatch):
    _patch(monkeypatch)

    async def boom(*_a):
        raise RuntimeError("picker down")

    out = asyncio.run(agent.research_concept(
        "Python", CONCEPT, llm=FakeLLM(), articles_fn=lambda q: ARTICLES, videos_fn=lambda q: VIDEOS,
        pick_fn=boom, use_transcripts=False,
    ))
    assert len(out) == 2


def test_search_errors_do_not_break_research(monkeypatch):
    _patch(monkeypatch)

    def broken(_q):
        raise RuntimeError("quota")

    out = asyncio.run(agent.research_concept(
        "Python", CONCEPT, llm=FakeLLM(), articles_fn=broken, videos_fn=broken,
        pick_fn=None, use_transcripts=False,
    ))
    assert out == []


def test_model_failure_returns_empty(monkeypatch):
    _patch(monkeypatch)

    class Dead(FakeLLM):
        async def ainvoke(self, _m):
            raise RuntimeError("model down")

    out = asyncio.run(agent.research_concept("Python", CONCEPT, llm=Dead(), use_transcripts=False))
    assert out == []


def test_video_id_parsing():
    assert tools.video_id_from_url("https://www.youtube.com/watch?v=abcdefghijk&t=3") == "abcdefghijk"
    assert tools.video_id_from_url("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert tools.video_id_from_url("https://example.com/x") is None

def test_article_search_drops_video_hosts(monkeypatch):
    rows = [
        {"title": "Guide", "url": "https://realpython.com/python-lists", "content": "lists"},
        {"title": "Video", "url": "https://www.youtube.com/watch?v=abcdefghijk", "content": "v"},
        {"title": "Short", "url": "https://youtu.be/abcdefghijk", "content": "v"},
        {"title": "Mobile", "url": "https://m.youtube.com/watch?v=abcdefghijk", "content": "v"},
        {"title": "Lookalike", "url": "https://notyoutube.com/page", "content": "ok"},
    ]

    class FakeTavily:
        def invoke(self, args):
            return {"results": rows}

    monkeypatch.setattr(tools, "_tavily", lambda: FakeTavily())
    urls = [r["url"] for r in tools.search_articles("python lists")]
    assert urls == ["https://realpython.com/python-lists", "https://notyoutube.com/page"]
    assert "youtube.com" in tools.EXCLUDED_ARTICLE_DOMAINS and "facebook.com" in tools.EXCLUDED_ARTICLE_DOMAINS
