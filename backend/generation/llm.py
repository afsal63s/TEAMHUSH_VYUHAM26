import asyncio
import logging
from typing import Any, Literal, TypeVar

import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from config import get_settings

logger = logging.getLogger(__name__)

Role = Literal["strong", "cheap", "local"]
T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (4, 10, 25)
INPUT_USD_PER_M = 0.10  # claude-haiku-5-5 list price
OUTPUT_USD_PER_M = 0.50

BREVITY = (
    "Use as few tokens as possible: no preamble or commentary, and keep each text field short. "
    "But obey every count and rule in the task exactly; never produce fewer items to save tokens."
)


class SpendLimitError(RuntimeError):
    """The estimated spend of this process passed MAX_SPEND_USD."""


class _Spend:
    """Running token totals for this process."""

    calls = 0
    input_tokens = 0
    output_tokens = 0

    @classmethod
    def cost(cls) -> float:
        return (cls.input_tokens * INPUT_USD_PER_M + cls.output_tokens * OUTPUT_USD_PER_M) / 1e6


def spend_summary() -> str:
    return (
        f"LLM usage: {_Spend.calls} calls, {_Spend.input_tokens} input + "
        f"{_Spend.output_tokens} output tokens, estimated ${_Spend.cost():.4f}"
    )


def _check_spend() -> None:
    limit = get_settings().MAX_SPEND_USD
    if _Spend.cost() > limit:
        raise SpendLimitError(f"estimated spend ${_Spend.cost():.4f} passed MAX_SPEND_USD=${limit:.2f}")


def _record_usage(role: Role, usage: dict[str, Any] | None) -> None:
    if not usage:
        logger.warning("%s reply carried no usage metadata; spend not counted", role)
        return
    _Spend.calls += 1
    _Spend.input_tokens += usage.get("input_tokens", 0)
    _Spend.output_tokens += usage.get("output_tokens", 0)
    logger.info(
        "%s call: %d in / %d out tokens; %s",
        role, usage.get("input_tokens", 0), usage.get("output_tokens", 0), spend_summary(),
    )


def _structured(role: Role, schema: type[BaseModel], max_tokens: int) -> Runnable:
    """Chat model for `role` constrained to `schema` by the API's native structured output."""
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY.get_secret_value():
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    chat = ChatAnthropic(
        model=getattr(settings, f"MODEL_{role.upper()}"),
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=max_tokens,
        default_request_timeout=120,
        max_retries=0,  # retries are handled below, with logging
    )
    return chat.with_structured_output(schema, method="json_schema", include_raw=True)


def _is_transient(exc: Exception) -> bool:
    """429, 529 (overloaded), other 5xx, and connection errors or timeouts."""
    if isinstance(exc, anthropic.APIConnectionError):
        return True
    return isinstance(exc, anthropic.APIStatusError) and (
        exc.status_code == 429 or exc.status_code >= 500
    )


async def structured_completion(
    role: Role, system: str, user: str, schema: type[T], *, max_tokens: int
) -> T:
    """Call the model for `role` and return its reply as a validated `schema` instance.

    Retries HTTP 429, 529, 5xx and connection errors with backoff, and re-asks when the reply
    cannot be parsed (for example, cut off at `max_tokens`). Raises SpendLimitError before any
    call once this process's estimated spend passes MAX_SPEND_USD.
    """
    model = _structured(role, schema, max_tokens)
    messages = [("system", f"{system}\n\n{BREVITY}"), ("user", user)]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _check_spend()
        try:
            result = await model.ainvoke(messages)
        except Exception as exc:
            if attempt == MAX_ATTEMPTS or not _is_transient(exc):
                raise
            delay = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
            logger.warning("transient %s from %s model, retrying in %ss", type(exc).__name__, role, delay)
            await asyncio.sleep(delay)
            continue
        raw = result["raw"]
        _record_usage(role, raw.usage_metadata)
        if result["parsed"] is not None:
            return result["parsed"]
        stop = raw.response_metadata.get("stop_reason")
        problem = f"unparseable reply (stop_reason={stop}): {result['parsing_error']}"
        if attempt == MAX_ATTEMPTS:
            raise ValueError(f"{role} model gave an {problem}")
        logger.warning("%s model gave an %s; retrying", role, problem)
    raise AssertionError("unreachable")
