import asyncio
from types import SimpleNamespace

import anthropic
import pytest
from langchain_core.messages import AIMessage

from config import Settings
from generation import llm
from generation.drafts import LessonDraft


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for field in ("calls", "input_tokens", "output_tokens"):
        monkeypatch.setattr(llm._Spend, field, 0)
    settings = Settings(_env_file=None, ANTHROPIC_API_KEY="test-key")
    monkeypatch.setattr(llm, "get_settings", lambda: settings)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)


class FakeModel:
    """Stands in for ChatAnthropic.with_structured_output(..., include_raw=True)."""

    def __init__(self, replies: list):
        self.replies = replies
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def ok(inp: int = 100, out: int = 20) -> dict:
    raw = AIMessage(content="", usage_metadata={"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out})
    return {"raw": raw, "parsed": LessonDraft(explanation="x"), "parsing_error": None}


def cut_off() -> dict:
    raw = AIMessage(
        content="", usage_metadata={"input_tokens": 1, "output_tokens": 9, "total_tokens": 10},
        response_metadata={"stop_reason": "max_tokens"},
    )
    return {"raw": raw, "parsed": None, "parsing_error": ValueError("truncated")}


def status_error(cls: type, code: int) -> Exception:
    return cls("boom", response=SimpleNamespace(status_code=code, headers={}, request=None), body=None)


def install(monkeypatch, model: FakeModel) -> list[int]:
    seen: list[int] = []

    def fake(role, schema, max_tokens):
        seen.append(max_tokens)
        return model

    monkeypatch.setattr(llm, "_structured", fake)
    return seen


def complete(**kw):
    return asyncio.run(llm.structured_completion("strong", "s", "u", LessonDraft, max_tokens=kw.get("max_tokens", 2500)))


def test_returns_parsed_and_records_spend(monkeypatch):
    seen = install(monkeypatch, FakeModel([ok(1_000_000, 1_000_000)]))
    assert complete().explanation == "x"
    assert seen == [2500]
    assert (llm._Spend.calls, llm._Spend.input_tokens, llm._Spend.output_tokens) == (1, 1_000_000, 1_000_000)
    assert llm._Spend.cost() == pytest.approx(0.60)
    assert "estimated $0.6000" in llm.spend_summary()


def test_spend_limit_stops_before_calling(monkeypatch):
    model = FakeModel([ok()])
    install(monkeypatch, model)
    monkeypatch.setattr(llm._Spend, "output_tokens", 5_000_000)  # $2.50 > $2.00
    with pytest.raises(llm.SpendLimitError, match="MAX_SPEND_USD"):
        complete()
    assert model.calls == 0


def test_spend_under_limit_runs(monkeypatch):
    install(monkeypatch, FakeModel([ok()]))
    monkeypatch.setattr(llm._Spend, "output_tokens", 3_000_000)  # $1.50 < $2.00
    complete()


@pytest.mark.parametrize(
    "error",
    [
        status_error(anthropic.RateLimitError, 429),
        status_error(anthropic.OverloadedError, 529),
        status_error(anthropic.InternalServerError, 500),
        anthropic.APIConnectionError(request=None),
    ],
)
def test_transient_errors_are_retried(monkeypatch, error):
    model = FakeModel([error, ok()])
    install(monkeypatch, model)
    complete()
    assert model.calls == 2


def test_client_errors_are_not_retried(monkeypatch):
    model = FakeModel([status_error(anthropic.BadRequestError, 400), ok()])
    install(monkeypatch, model)
    with pytest.raises(anthropic.BadRequestError):
        complete()
    assert model.calls == 1


def test_unparseable_reply_is_retried_and_counted(monkeypatch):
    model = FakeModel([cut_off(), ok()])
    install(monkeypatch, model)
    assert complete().explanation == "x"
    assert model.calls == 2 and llm._Spend.calls == 2  # the cut-off reply still cost tokens


def test_unparseable_reply_gives_up_with_reason(monkeypatch):
    install(monkeypatch, FakeModel([cut_off(), cut_off(), cut_off()]))
    with pytest.raises(ValueError, match="stop_reason=max_tokens"):
        complete()


def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(llm, "get_settings", lambda: Settings(_env_file=None))
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm._structured("strong", LessonDraft, 100)


def test_every_role_defaults_to_haiku():
    s = Settings(_env_file=None)
    assert s.MODEL_STRONG == s.MODEL_CHEAP == s.MODEL_LOCAL == "claude-haiku-5-5"
    assert s.MAX_SPEND_USD == 2.00
