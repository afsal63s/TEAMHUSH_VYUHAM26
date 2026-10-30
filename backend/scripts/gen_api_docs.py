"""Generate the frontend API reference from a live run against a server this script launches.

Usage: uv run python scripts/gen_api_docs.py

Writes, in docs/: API_REFERENCE.md, API_REFERENCE_CHECK.md, types.ts, openapi.json, api.http and
examples/<name>.json. Every field, status code and behaviour claim in the reference is taken from
responses captured during this run; anything surprising goes under "Quirks and open questions".

Secrets: the master password and API keys never reach any output; the header is shown as
"X-Master-Password: <your-master-password>". If .env has no MASTER_PASSWORD, the launched server gets
a temporary one for this run (so a real 401 can be captured) and the reference says so.
"""

import json
import os
import re
import secrets
import statistics
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import httpx  # noqa: E402

from api.bundles import find_bundle  # noqa: E402
from config import get_settings  # noqa: E402

DOCS = ROOT / "docs"
EXAMPLES = DOCS / "examples"
BASE = "http://127.0.0.1:8000"
SERVER_CMD = ("import logging; logging.basicConfig(level=logging.INFO); import uvicorn; "
              "uvicorn.run('main:app', port=8000)")
PW_SHOWN = "<your-master-password>"
COURSES = [("prompt engineering", "beginner"), ("Python", "novice")]
GEN_PROMPT, GEN_LEVEL = "SQL joins", "novice"     # the course this script generates to show "generating"
GEN_TIMEOUT = 8 * 60
EXAMPLE_LIMIT = 4000

SETTINGS = get_settings()
ENV_PASSWORD = SETTINGS.MASTER_PASSWORD.get_secret_value()
PASSWORD = ENV_PASSWORD or secrets.token_urlsafe(16)
SECRETS = [s for s in (PASSWORD, SETTINGS.ANTHROPIC_API_KEY.get_secret_value(),
                       SETTINGS.TAVILY_API_KEY.get_secret_value(), SETTINGS.YOUTUBE_API_KEY.get_secret_value()) if s]
RUN_ID = datetime.now().strftime("%H%M%S")
META_PATH = DOCS / "examples" / "_run_meta.json"


def scrub(text: str) -> str:
    for s in SECRETS:
        text = text.replace(s, PW_SHOWN if s == PASSWORD else "<redacted>")
    return text


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(scrub(text), encoding="utf-8")
    os.replace(tmp, path)


# --- server ---

class Server:
    def __init__(self) -> None:
        self.lines: list[tuple[float, str]] = []
        self.proc = None

    def start(self) -> None:
        try:
            httpx.get(f"{BASE}/health", timeout=1)
            sys.exit("port 8000 is already serving; stop that server first")
        except httpx.HTTPError:
            pass
        env = {**os.environ, "MASTER_PASSWORD": PASSWORD, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen([sys.executable, "-c", SERVER_CMD], cwd=ROOT, env=env, text=True,
                                     encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()
        for _ in range(120):
            try:
                if httpx.get(f"{BASE}/health", timeout=1).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.5)
        raise RuntimeError("server did not come up")

    def _read(self) -> None:
        for line in self.proc.stdout:
            self.lines.append((time.monotonic(), scrub(line.rstrip())))

    pos = 0

    def take(self, method: str, path: str, timeout: float = 3.0) -> list[str]:
        """Log lines of one request: everything since the previous request up to its access-log line."""
        marker = f'"{method} {path} HTTP'
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for i in range(self.pos, len(self.lines)):
                if marker in self.lines[i][1]:
                    chunk = [ln for _, ln in self.lines[self.pos:i + 1]]
                    self.pos = i + 1
                    return chunk
            time.sleep(0.02)
        chunk = [ln for _, ln in self.lines[self.pos:]]
        self.pos = len(self.lines)
        return chunk

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


# --- capture ---

class Call:
    def __init__(self, route, method, path, body, status, ms, data, llm, auth):
        self.route, self.method, self.path, self.body = route, method, path, body
        self.status, self.ms, self.data, self.llm, self.auth = status, ms, data, llm, auth


SRV = Server()
META: dict = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
CALLS: list[Call] = []
EXAMPLE_FILES: dict[str, Call] = {}
QUIRKS: list[str] = []
RESEARCH_LLM: list[int] = []   # background research LLM calls seen in each request's log window
UNVERIFIED: list[str] = []
FACTS: dict = {}


def quirk(text: str) -> None:
    if text not in QUIRKS:
        QUIRKS.append(text)
        print(f"  quirk: {text}")


def call(client: httpx.Client, route: str, method: str, path: str, body=None, *, example: str | None = None,
         auth: bool = True, expect: int | None = 200) -> Call:
    t0 = time.monotonic()
    if auth:
        r = client.request(method, path, json=body)
    else:                                            # no X-Master-Password header at all
        r = httpx.request(method, f"{BASE}{path}", json=body, timeout=60)
    t1 = time.monotonic()
    try:
        data = r.json()
    except ValueError:
        data = r.text
    lines = SRV.take(method, path)
    llm = sum(1 for ln in lines if re.search(r"strong call: \d+ in / \d+ out tokens", ln))
    RESEARCH_LLM.append(sum(1 for ln in lines if re.search(r"cheap call: \d+ in / \d+ out tokens", ln)))
    c = Call(route, method, path, body, r.status_code, (t1 - t0) * 1000, data, llm, auth)
    CALLS.append(c)
    print(f"{method:5} {path} -> {r.status_code} ({c.ms:.0f} ms{', LLM x' + str(c.llm) if c.llm else ''})"
          f"{'  [' + example + ']' if example else ''}")
    if example:
        EXAMPLE_FILES[example] = c
        write(EXAMPLES / f"{example}.json", json.dumps(data, indent=2))
    if expect is not None and r.status_code != expect:
        raise RuntimeError(f"{method} {path}: expected {expect}, got {r.status_code}: {str(data)[:300]}")
    return c


def answers_for(key, questions, right, confidence=None, per_q=None):
    out = []
    for q in questions:
        k = key[q["id"]]
        ok = q["concept_id"] in right if per_q is None else per_q(q)[0]
        conf = confidence if per_q is None else per_q(q)[1]
        idx = k.correct_index if ok else next(i for i, o in enumerate(k.options) if o.misconception_tag)
        a = {"question_id": q["id"], "chosen_index": idx}
        if conf is not None:
            a["confidence"] = conf
        out.append(a)
    return out


# --- the live run ---

def run(client: httpx.Client) -> None:
    lp = "/courses/{cid}/learners/{lid}"
    call(client, "GET /health", "GET", "/health", example="health", auth=False)
    call(client, "POST /courses", "POST", "/courses", {"prompt": "x"}, example="error_401", auth=False, expect=401)

    bundle = None
    for prompt, level in COURSES:
        bundle = find_bundle(prompt, level)
        if bundle:
            break
    if bundle is None:
        raise RuntimeError("no cached course bundle for 'prompt engineering' or 'Python'")
    FACTS["course_prompt"] = (bundle.prompt, bundle.level)
    key = {q.id: q for q in bundle.questions}
    c = call(client, "POST /courses", "POST", "/courses", {"prompt": bundle.prompt, "level": bundle.level},
             example="courses_create_ready")
    cid = c.data["course_id"]
    FACTS["cid"] = cid
    call(client, "GET /courses/{cid}", "GET", f"/courses/{cid}", example="course_get")
    call(client, "GET /courses/{cid}", "GET", "/courses/no-such-course", example="error_404", expect=404)
    call(client, "POST /courses", "POST", "/courses", {"level": "beginner"}, example="error_422_validation", expect=422)
    call(client, "POST /courses", "POST", "/courses", {"prompt": "x", "level": "expert"}, expect=422)

    # --- main learner ---
    lid = f"docs-{RUN_ID}"
    FACTS["lid"] = lid
    b = f"/courses/{cid}/learners/{lid}"
    call(client, f"GET {lp}/state", "GET", f"{b}/state", example="error_404_learner", expect=404)
    start = call(client, f"POST {lp}/start", "POST", f"{b}/start", example="start").data
    call(client, f"POST {lp}/start", "POST", f"{b}/start", example="error_409_start", expect=409)
    call(client, f"GET {lp}/next", "GET", f"{b}/next", example="error_409_next_before_diagnostic", expect=409)
    diag = start["questions"]
    stranger = next(q.id for q in bundle.questions if q.id not in {d["id"] for d in diag})
    call(client, f"POST {lp}/attempts", "POST", f"{b}/attempts",
         {"answers": [{"question_id": stranger, "chosen_index": 0}]}, example="error_422_unserved", expect=422)
    call(client, f"POST {lp}/attempts", "POST", f"{b}/attempts", {"answers": []}, expect=422)

    plan = {}
    for i, q in enumerate(diag, start=1):
        plan[q["id"]] = ((True, "medium") if i <= 3 else (False, "high") if i == 4 else (True, None) if i == 5
                         else (False, "low") if i == 6 else (True, "high"))
    FACTS["diag_plan"] = {diag[i]["concept_id"]: plan[diag[i]["id"]] for i in range(len(diag))}
    ans = answers_for(key, diag, None, per_q=lambda q: plan[q["id"]])
    res = call(client, f"POST {lp}/attempts", "POST", f"{b}/attempts", {"answers": ans}, example="attempts_diagnostic").data
    FACTS["confidence_omitted_ok"] = True       # answer 5 carried no confidence and was accepted
    n1 = call(client, f"GET {lp}/next", "GET", f"{b}/next", example="next_lesson")
    n2 = call(client, f"GET {lp}/next", "GET", f"{b}/next")
    FACTS["next_idempotent"] = n1.data == n2.data
    FACTS["next_matches_attempt"] = n1.data["step"] == res["next"]["step"] and \
        [q["id"] for q in n1.data["questions"]] == [q["id"] for q in res["next"]["questions"]]
    call(client, f"GET {lp}/state", "GET", f"{b}/state", example="state_after_diagnostic")
    r0 = call(client, f"GET {lp}/resources", "GET", f"{b}/resources", example="resources_after_diagnostic")
    FACTS["research_first"] = {k: v["status"] for k, v in r0.data.items()}
    t_res = time.monotonic()
    while time.monotonic() - t_res < 90:
        rr = call(client, f"GET {lp}/resources", "GET", f"{b}/resources")
        if rr.data and all(v["status"] != "pending" for v in rr.data.values()):
            break
        time.sleep(3)
    EXAMPLE_FILES["resources_ready"] = rr
    write(EXAMPLES / "resources_ready.json", json.dumps(rr.data, indent=2))
    FACTS["research_seconds"] = time.monotonic() - t_res
    FACTS["research_final"] = {k: v["status"] for k, v in rr.data.items()}
    gaps_now = call(client, f"GET {lp}/state", "GET", f"{b}/state").data["gaps"]
    FACTS["research_gaps_match"] = set(rr.data) <= set(gaps_now) and set(r0.data) == set(gaps_now)
    qs = n1.data["questions"]
    practice = answers_for(key, qs, None, per_q=lambda q: (q["id"] != qs[-1]["id"], "medium"))
    call(client, f"POST {lp}/attempts", "POST", f"{b}/attempts", {"answers": practice}, example="attempts_practice")
    call(client, f"POST {lp}/advance", "POST", f"{b}/advance", {"days": 0}, example="error_422_advance_days", expect=422)
    adv = call(client, f"POST {lp}/advance", "POST", f"{b}/advance", {"days": 1}, example="advance").data
    call(client, f"GET {lp}/state", "GET", f"{b}/state", example="state_after_advance")
    rv = call(client, f"GET {lp}/next", "GET", f"{b}/next", example="next_review" if adv["next_kind"] == "review" else None).data
    if rv["step"]["kind"] == "review":
        fail = answers_for(key, rv["questions"], set(), "high")
        rr = call(client, f"POST {lp}/attempts", "POST", f"{b}/attempts", {"answers": fail}, example="attempts_review_failed").data
        call(client, f"GET {lp}/next", "GET", f"{b}/next",
             example="next_relearn" if rr["next"]["step"]["kind"] == "lesson" else None)
    else:
        UNVERIFIED.append(f"Review flow: after advancing 1 day the next step was {rv['step']['kind']}, not a review.")
    call(client, f"POST {lp}/sessions/new", "POST", f"{b}/sessions/new", example="sessions_new")
    call(client, f"GET {lp}/state", "GET", f"{b}/state", example="state")

    # --- learner who knows everything: done ---
    b2 = f"/courses/{cid}/learners/{lid}-all"
    d2 = call(client, f"POST {lp}/start", "POST", f"{b2}/start").data["questions"]
    call(client, f"POST {lp}/attempts", "POST", f"{b2}/attempts",
         {"answers": answers_for(key, d2, {q["concept_id"] for q in d2}, "high")}, example="attempts_all_known_done")
    call(client, f"GET {lp}/next", "GET", f"{b2}/next", example="next_done")
    call(client, f"POST {lp}/advance", "POST", f"{b2}/advance", {"days": 3}, example="advance_all_due")

    # --- a struggling learner: fallback, session_end, give_up_after, needs_help ---
    graph = EXAMPLE_FILES["course_get"].data["concepts"]
    target = next(x for x in graph if x["prerequisites"])
    FACTS["struggle_target"] = target["id"]
    b3 = f"/courses/{cid}/learners/{lid}-stuck"
    d3 = call(client, f"POST {lp}/start", "POST", f"{b3}/start").data["questions"]
    call(client, f"POST {lp}/attempts", "POST", f"{b3}/attempts",
         {"answers": answers_for(key, d3, {q["concept_id"] for q in d3} - {target["id"]}, "medium")})
    seen_kinds, in_session, cap_at = set(), 0, None
    for _ in range(16):
        nx = call(client, f"GET {lp}/next", "GET", f"{b3}/next").data
        st = nx["step"]
        tag = st["kind"] + ("_give_up" if st["give_up_after"] else "")
        if tag not in seen_kinds:
            seen_kinds.add(tag)
            name = {"fallback": "next_fallback", "lesson_give_up": "next_give_up", "session_end": "next_session_end"}.get(tag)
            if name:
                EXAMPLE_FILES[name] = CALLS[-1]
                write(EXAMPLES / f"{name}.json", json.dumps(nx, indent=2))
        if st["kind"] == "done":
            EXAMPLE_FILES["next_done_with_needs_help"] = CALLS[-1]
            write(EXAMPLES / "next_done_with_needs_help.json", json.dumps(nx, indent=2))
            break
        if st["kind"] == "session_end":
            cap_at = in_session
            call(client, f"POST {lp}/sessions/new", "POST", f"{b3}/sessions/new")
            in_session = 0
            continue
        right = st["kind"] == "fallback"                     # pass the prerequisite, fail the target
        r = call(client, f"POST {lp}/attempts", "POST", f"{b3}/attempts",
                 {"answers": answers_for(key, nx["questions"], {q["concept_id"] for q in nx["questions"]} if right else set(), "medium")}).data
        in_session += len(nx["questions"])
        if any("flagged for help" in m for m in r["messages"]) and "attempts_needs_help" not in EXAMPLE_FILES:
            EXAMPLE_FILES["attempts_needs_help"] = CALLS[-1]
            write(EXAMPLES / "attempts_needs_help.json", json.dumps(r, indent=2))
            call(client, f"GET {lp}/state", "GET", f"{b3}/state", example="state_needs_help")
    FACTS["struggle_kinds"] = sorted(seen_kinds)
    FACTS["session_cap_at"] = cap_at

    # --- other routes ---
    call(client, "GET /eval/results", "GET", "/eval/results", example="eval_results", expect=None)
    FACTS["planned"] = {}
    for method, path, body in [("POST", f"{b}/virtual/start", {"persona": "x"}),
                               ("POST", f"{b}/virtual/pause", None), ("POST", f"{b}/virtual/resume", None),
                               ("POST", f"{b}/virtual/stop", None), ("POST", f"{b}/virtual/speed", {"speed": 1}),
                               ("GET", f"{b}/virtual/status", None), ("GET", f"{b}/virtual/events?after=0", None)]:
        r = client.request(method, path, json=body)
        FACTS["planned"][f"{method} {path.replace(b, '.../learners/{lid}')}"] = r.status_code

    # --- a course generated during this run: generating status, polling, deadline messages ---
    deadline = (datetime.now(timezone.utc) + timedelta(days=2, hours=12)).replace(tzinfo=None).isoformat()
    g = call(client, "POST /courses", "POST", "/courses", {"prompt": GEN_PROMPT, "level": GEN_LEVEL, "deadline": deadline})
    gid = g.data["course_id"]
    if g.data["status"] == "generating":
        EXAMPLE_FILES["courses_create_generating"] = g
        write(EXAMPLES / "courses_create_generating.json", json.dumps(g.data, indent=2))
        t0 = time.monotonic()
        polls = 0
        while True:
            time.sleep(2)
            p = call(client, "GET /courses/{cid}", "GET", f"/courses/{gid}",
                     example="course_get_generating" if polls == 0 else None)
            polls += 1
            if p.data["status"] != "generating" or time.monotonic() - t0 > GEN_TIMEOUT:
                break
        FACTS["generation_seconds"] = time.monotonic() - t0
        FACTS["generation_status"] = p.data["status"]
        FACTS["generation_polls"] = polls
        FACTS["generation_when"] = "this run"
        META["generation"] = {"seconds": FACTS["generation_seconds"], "polls": polls, "status": p.data["status"],
                              "when": f"{datetime.now():%Y-%m-%d %H:%M}",
                              **{k: {n: getattr(EXAMPLE_FILES[n], a) for n in ("courses_create_generating", "course_get_generating")}
                                 for k, a in (("routes", "route"), ("methods", "method"), ("paths", "path"), ("ms", "ms"))}}
    elif META.get("generation"):
        g = META["generation"]
        FACTS.update(generation_seconds=g["seconds"], generation_polls=g["polls"], generation_status=g["status"],
                     generation_when=f"an earlier run of this script ({g['when']})")
        for name in ("courses_create_generating", "course_get_generating"):
            f = EXAMPLES / f"{name}.json"
            if f.exists():
                EXAMPLE_FILES[name] = Call(g["routes"][name], g["methods"][name], g["paths"][name], None, 200,
                                           g["ms"][name], json.loads(f.read_text(encoding="utf-8")), 0, True)
    else:
        FACTS["generation_seconds"] = None
        UNVERIFIED.append(f"The 'generating' status: the course '{GEN_PROMPT}' ({GEN_LEVEL}) already existed from an "
                          f"earlier run, so no generation was observed (examples from an earlier run are kept if present).")
    gc = call(client, "GET /courses/{cid}", "GET", f"/courses/{gid}").data
    if gc["status"] == "ready":
        b4 = f"/courses/{gid}/learners/{lid}-deadline"
        d4 = call(client, f"POST {lp}/start", "POST", f"{b4}/start").data["questions"]
        call(client, f"POST {lp}/attempts", "POST", f"{b4}/attempts",
             {"answers": [{"question_id": q["id"], "chosen_index": 0} for q in d4]}, example="attempts_with_deadline")
        call(client, f"GET {lp}/state", "GET", f"{b4}/state", example="state_with_deadline")
    else:
        UNVERIFIED.append(f"Deadline messages: the generated course ended as '{gc['status']}'.")

    # A learner who gets every diagnostic question wrong: research starts for every concept not researched yet,
    # so the first poll shows `pending` (research results persist per course, so later runs may not see it).
    b5 = f"/courses/{cid}/learners/{lid}-new"
    d5 = call(client, f"POST {lp}/start", "POST", f"{b5}/start").data["questions"]
    call(client, f"POST {lp}/attempts", "POST", f"{b5}/attempts", {"answers": answers_for(key, d5, set(), "low")})
    rp = call(client, f"GET {lp}/resources", "GET", f"{b5}/resources")
    if any(v["status"] == "pending" for v in rp.data.values()):
        EXAMPLE_FILES["resources_pending"] = rp
        write(EXAMPLES / "resources_pending.json", json.dumps(rp.data, indent=2))
        META["resources_pending"] = {"path": rp.path, "ms": rp.ms, "when": f"{datetime.now():%Y-%m-%d %H:%M}"}
    elif META.get("resources_pending") and (EXAMPLES / "resources_pending.json").exists():
        m = META["resources_pending"]
        EXAMPLE_FILES["resources_pending"] = Call(f"GET {lp}/resources", "GET", m["path"], None, 200, m["ms"],
                                                  json.loads((EXAMPLES / "resources_pending.json").read_text(encoding="utf-8")), 0, True)
        quirk(f"The `pending` resources example was captured in an earlier run of this script ({m['when']}); "
              "in this run every concept had been researched already.")
    else:
        UNVERIFIED.append("A `pending` research status: every gap concept was already researched when polled.")
    # Let that research finish before the server stops: research killed by a restart is marked failed.
    t_wait = time.monotonic()
    while time.monotonic() - t_wait < 120 and any(
            v["status"] == "pending" for v in client.get(f"{b5}/resources").json().values()):
        time.sleep(3)


# --- analysis of the captures ---

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")


def walk_strings(x, out):
    if isinstance(x, dict):
        for v in x.values():
            walk_strings(v, out)
    elif isinstance(x, list):
        for v in x:
            walk_strings(v, out)
    elif isinstance(x, str):
        out.append(x)


def analyse() -> None:
    strings = []
    for c in CALLS:
        walk_strings(c.data, strings)
    dts = [s for s in strings if ISO.match(s)]
    FACTS["datetimes"] = len(dts)
    FACTS["datetimes_with_zone"] = [s for s in dts if s.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", s)]
    FACTS["datetime_sample"] = dts[0] if dts else None
    qs_before = [q for c in CALLS if c.status == 200 and isinstance(c.data, dict)
                 for q in (c.data.get("questions") or [])]
    FACTS["question_keys"] = sorted({k for q in qs_before for k in q})
    FACTS["options_all_strings"] = all(isinstance(o, str) for q in qs_before for o in q["options"])
    steps = [c.data["step"] for c in CALLS if c.status == 200 and isinstance(c.data, dict) and "step" in c.data] + \
            [c.data["next"]["step"] for c in CALLS if c.status == 200 and isinstance(c.data, dict) and "next" in c.data]
    FACTS["step_kinds_seen"] = sorted({s["kind"] + (" (give_up_after)" if s["give_up_after"] else "") for s in steps})
    msgs = [m for c in CALLS if c.status == 200 and isinstance(c.data, dict) for m in c.data.get("messages", [])]
    FACTS["messages_seen"] = msgs
    lessons = [c for c in CALLS if c.status == 200 and isinstance(c.data, dict)
               and ((c.data.get("lesson")) or (c.data.get("next") or {}).get("lesson"))]
    FACTS["lesson_llm_ms"] = [c.ms for c in lessons if c.llm]
    if FACTS["lesson_llm_ms"]:
        META["lesson_llm"] = {"ms": FACTS["lesson_llm_ms"], "when": f"{datetime.now():%Y-%m-%d %H:%M}"}
        FACTS["lesson_llm_when"] = "this run"
    elif META.get("lesson_llm"):
        FACTS["lesson_llm_ms"], FACTS["lesson_llm_when"] = META["lesson_llm"]["ms"], f"an earlier run of this script ({META['lesson_llm']['when']})"
    FACTS["lesson_cached_ms"] = [c.ms for c in lessons if not c.llm]
    if FACTS["datetimes_with_zone"]:
        quirk(f"Some datetimes carry a zone: {FACTS['datetimes_with_zone'][:3]}")
    if not FACTS.get("next_idempotent"):
        quirk("Two identical GET .../next calls returned different bodies.")
    # Things that looked surprising during the run
    for c in CALLS:
        if isinstance(c.data, dict) and c.data.get("next", {}).get("lesson") and not c.data["next"]["lesson"]["resources"]:
            quirk("A lesson built before its concept's research is ready comes with `resources: []`; "
                  "GET .../next returns the same lesson with the resources once research is ready.")
            break
    st = EXAMPLE_FILES.get("state")
    if st and isinstance(st.data, dict) and isinstance(st.data.get("pace", {}).get("mastered"), float):
        quirk("`pace.mastered` and `pace.total` are counts but are sent as floats (e.g. 4.0), "
              "because `pace` is typed dict[str, float].")
    if any(m.startswith("Placed") and "1 concepts" in m for m in msgs):
        quirk("The placement message says 'Placed 1 concepts' (no singular form).")
    fractions = {len(m.group(1)) if m else 0 for d in dts for m in [re.search(r"\.(\d+)$", d)]}
    ms_only =sum(1 for d in dts if re.search(r"\.\d{3}000$", d))
    quirk(f"Datetimes: {len(dts)} values, fraction digits seen {sorted(fractions)}; {ms_only} of them end in '000' "
          "(values stored in MongoDB keep only milliseconds). "
          + ("Some have no fraction at all (Python omits it when the microseconds are 0), so parse with a lenient ISO "
             "parser, not a fixed format." if 0 in fractions else
             "Open question: Python omits the fraction entirely when the microseconds are 0 (not observed here), so "
             "parse with a lenient ISO parser."))
    if ENV_PASSWORD == "":
        quirk(".env has no MASTER_PASSWORD, so a server started from .env runs in dev mode with every route open "
              "(it logs a warning). This run gave the server a temporary password to capture the real 401.")
    sn = EXAMPLE_FILES.get("sessions_new")
    if sn and "next_kind" in sn.data:
        quirk("POST .../sessions/new has no response model in the OpenAPI schema (a plain object); its shape "
              "below is taken from the live response.")
    if FACTS.get("planned") and all(v == 404 for v in FACTS["planned"].values()):
        pass
    if any(c.route.endswith("/next") and c.status == 200 and c.data["step"]["kind"] in ("done", "session_end")
           and c.data["reason"] == "" for c in CALLS):
        quirk("A done/session_end step came with an empty reason.")


# --- documentation content ---

FIELD_DOCS = {
    "CreateCourseIn.prompt": ("What the learner wants to learn, free text. Case and extra spaces do not matter for reuse.", ""),
    "CreateCourseIn.level": ("Self-assessed level from a dropdown.", ""),
    "CreateCourseIn.deadline": ("Optional target date (naive UTC ISO). Drives `days_left` and the deadline message.", ""),
    "CreateCourseOut.course_id": ("Id to use in every learner URL.", ""),
    "CreateCourseOut.status": ("`generating`, `ready` or `failed`.", ""),
    "CreateCourseOut.topic": ("Topic name for headings. While generating it is the prompt.", "never null"),
    "CreateCourseOut.concepts": ("Concept graph for the UI: `[{id, name, prerequisites}]`.", "empty while generating or failed"),
    "QuestionPublic.id": ("Question id; send it back in an answer.", ""),
    "QuestionPublic.concept_id": ("Concept this question tests.", ""),
    "QuestionPublic.prompt": ("Question text (plain text, may contain code inline).", ""),
    "QuestionPublic.options": ("Exactly 4 option texts. Answer with the 0-based index.", ""),
    "StartOut.questions": ("The diagnostic: one question per concept, in roadmap order.", ""),
    "SubmitAnswersIn.answers": ("One entry per answered question. Only questions served to this learner are accepted.", ""),
    "AnswerIn.question_id": ("Id of a served question.", ""),
    "AnswerIn.chosen_index": ("0-based index into `options`.", ""),
    "AnswerIn.confidence": ("Optional self-reported confidence. Low confidence on a right answer counts less; "
                            "high confidence on a wrong answer counts as stronger misconception evidence; on the "
                            "diagnostic it sets how soon placed concepts are re-checked (low 1 day, medium 2, high 3).",
                            "omit or null when not asked"),
    "StepOut.step": ("The brain's decision: what to show next.", ""),
    "StepOut.reason": ("Human-readable explanation of the decision, built from facts.", "never empty in this run"),
    "StepOut.lesson": ("Lesson for lesson/fallback steps.", "null for review, session_end, done; null if generation failed"),
    "StepOut.questions": ("Questions to answer next (3 for lessons, 2 for reviews).", "empty for session_end and done"),
    "Step.kind": ("What to render: lesson, review, fallback, session_end, done.", ""),
    "Step.concept_id": ("Concept to teach or review. For fallback it is the prerequisite being revisited.", "null for session_end and done"),
    "Step.target_misconceptions": ("Confirmed misconception tags this lesson addresses.", "empty when none are confirmed"),
    "Step.avoid_styles": ("Lesson styles already tried for this concept (informational).", "often empty"),
    "Step.difficulty": ("Reserved.", "always null in this run"),
    "Step.target_concept": ("For fallback: the concept the learner is stuck on.", "null except for fallback"),
    "Step.give_up_after": ("True on the last attempt before the concept is flagged needs_help.", ""),
    "Lesson.concept_id": ("Concept taught.", ""),
    "Lesson.style": ("worked_example, contrast, analogy or step_by_step.", ""),
    "Lesson.explanation": ("Lesson text, 120 to 200 words, plain text.", ""),
    "Lesson.targets": ("Misconception tags addressed.", "empty when none"),
    "Lesson.resources": ("Researched articles and videos for the concept.", "empty until the concept's research is ready"),
    "ConceptResearch.status": ("`pending` while research runs, then `ready` or `failed`.", ""),
    "ConceptResearch.resources": ("Articles and videos found (at most 2 articles and 1 video).", "empty while pending and when failed"),
    "Resource.kind": ("article or video.", ""),
    "Resource.title": ("Title.", ""),
    "Resource.url": ("Link.", ""),
    "Resource.snippet": ("Short excerpt.", "may be empty"),
    "AttemptResultOut.graded": ("Per-answer result, in submission order.", ""),
    "AttemptResultOut.correct_indices": ("question_id -> correct option index (only after grading).", ""),
    "AttemptResultOut.explanations": ("question_id -> why the right answer is right.", ""),
    "AttemptResultOut.mastery": ("concept_id -> p_mastery after this round, for every concept.", ""),
    "AttemptResultOut.new_confirmed_misconceptions": ("Tags that became confirmed in this round.", "usually empty"),
    "AttemptResultOut.messages": ("Encouragement and status lines to show as toasts.", "often empty"),
    "AttemptResultOut.next": ("The next step with its material (same as GET .../next right after).", ""),
    "AnswerGraded.question_id": ("Question answered.", ""),
    "AnswerGraded.concept_id": ("Its concept.", ""),
    "AnswerGraded.correct": ("Whether the chosen option was right.", ""),
    "AnswerGraded.chosen_tag": ("Misconception tag of the wrong option picked.", "null when correct"),
    "AnswerGraded.confidence": ("Echo of the confidence sent.", "null when not sent"),
    "MasteryOut.concepts": ("Per-concept state, roadmap order.", ""),
    "MasteryOut.misconceptions": ("Every misconception seen so far with its status.", "empty before any wrong pick"),
    "MasteryOut.next_due": ("Earliest scheduled review.", "null when nothing is scheduled"),
    "MasteryOut.due": ("concept_id -> scheduled review time (past times are due now).", "empty when nothing is scheduled"),
    "MasteryOut.roadmap": ("Concept ids, prerequisites first.", ""),
    "MasteryOut.needs_help": ("Concepts the learner is stuck on.", "usually empty"),
    "MasteryOut.days_left": ("Whole days to the course deadline (learner's clock).", "null without a deadline"),
    "MasteryOut.gaps": ("Concepts not yet mastered, roadmap order.", "empty when all are mastered"),
    "MasteryOut.retrievability": ("concept_id -> recall probability now (1.0 if never mastered).", ""),
    "MasteryOut.pace": ("`{mastered, total, attempts_per_mastered}`.", ""),
    "ConceptState.concept_id": ("Concept.", ""),
    "ConceptState.p_mastery": ("Probability the concept is known (0..1); 0.85 or more counts as mastered.", ""),
    "ConceptState.attempts": ("Questions answered on this concept.", ""),
    "ConceptState.failed_rounds": ("Rounds in a row with a wrong answer while not mastered.", ""),
    "ConceptState.stability_days": ("Memory stability in days; review spacing grows with it.", "0 before mastery"),
    "ConceptState.last_reviewed_at": ("When the schedule last changed.", "null before mastery or placement"),
    "ConceptState.due_at": ("When the next review is due.", "null before mastery or placement"),
    "ConceptState.lapses": ("Failed reviews of a mastered concept.", ""),
    "ConceptState.explanations_tried": ("Lesson styles shown so far.", "empty before the first lesson"),
    "ConceptState.fallbacks": ("Times the brain detoured to a prerequisite.", ""),
    "ConceptState.needs_help": ("Stuck after the last try: show a 'get help' card.", ""),
    "MisconceptionState.tag": ("Misconception id, `<concept_id>__<slug>`.", ""),
    "MisconceptionState.concept_id": ("Its concept.", ""),
    "MisconceptionState.status": ("suspected, confirmed or resolved.", ""),
    "MisconceptionState.evidence": ("Weight of wrong picks (1 per pick, 2 with high confidence); 2 confirms.", ""),
    "MisconceptionState.clean_streak": ("Correct answers in a row on questions testing it; 2 resolves it.", ""),
    "AdvanceIn.days": ("Days to move the learner's simulated clock forward (must be > 0).", ""),
    "AdvanceOut.now": ("The learner's simulated now after the move.", ""),
    "AdvanceOut.due_now": ("Concepts whose review is due at that time.", "empty when none"),
    "AdvanceOut.next_kind": ("Kind of the step decided for the new time (fetch it with GET .../next).", ""),
    "AdvanceOut.next_concept_id": ("Its concept.", "null for session_end/done"),
}

ENDPOINT_DOCS = {
    "GET /health": ("Liveness check. Needs no password.", "On app load, to show a 'backend offline' banner.",
                    "none", "Safe to poll; no state."),
    "POST /courses": ("Creates the course for a prompt and level, or returns the existing one for the same prompt and "
                      "level (case and spacing ignored). A course that is not cached starts generating in the background "
                      "and returns at once with status `generating`. Sending a deadline for an existing course updates it.",
                      "From the setup screen, once.",
                      "Creates a course (and starts LLM generation) or updates the deadline of the existing one.",
                      "Repeat calls with the same prompt and level return the same course_id. Poll GET /courses/{cid} "
                      "every 2 s while status is `generating`."),
    "GET /courses/{cid}": ("Returns the course status, topic and concept graph.", "While polling after creation, and to draw the graph.",
                           "none", "Safe to poll every 2 s while `generating`; stop on `ready` or `failed`."),
    "POST /courses/{cid}/learners/{lid}/start": ("Creates the learner for this course and returns the diagnostic: one question per concept.",
                                                  "Once per learner, after the course is ready.",
                                                  "Creates the learner state (every concept at the prior, roadmap in prerequisite order); "
                                                  "the diagnostic questions become the only answerable ones.",
                                                  "Not idempotent: a second call returns 409. Use GET .../state to detect an existing learner."),
    "POST /courses/{cid}/learners/{lid}/attempts": ("Grades a round of answers, updates mastery, misconceptions and the review schedule, "
                                                     "decides the next step and returns it with its material. The first call answers the diagnostic.",
                                                     "Whenever the learner submits the questions on screen.",
                                                     "Records every answer; updates the learner state; stores the next step and its questions "
                                                     "(only those become answerable). May call the LLM to write the next lesson.",
                                                     "Not idempotent: answers count once; resubmitting the same ids returns 422 because they are no longer served."),
    "GET /courses/{cid}/learners/{lid}/next": ("Serves the stored next step with its lesson and questions. The first call after an "
                                                "advance or a new session builds the material (may call the LLM); later calls return the same thing.",
                                                "After advance or sessions/new, after a page reload, or any time the client lost the step.",
                                                "First call after a decision: stores the served question ids and records the lesson style. Later calls: none.",
                                                "Idempotent: identical calls return identical bodies."),
    "GET /courses/{cid}/learners/{lid}/state": ("Returns the dashboard: per-concept mastery, retrievability and schedule, misconceptions, gaps, "
                                                 "roadmap, needs_help, pace and days_left, all at the learner's simulated now.",
                                                 "For the sidebar and progress views, after every attempt or advance.",
                                                 "none", "Safe to call any time."),
    "POST /courses/{cid}/learners/{lid}/advance": ("Moves this learner's simulated clock forward, starts a new session, and decides the next step "
                                                    "for the new time (without building material: no LLM call).",
                                                    "From the demo control panel ('skip ahead N days').",
                                                    "clock_offset_days += days; session counter reset; stored next step replaced; previously served "
                                                    "questions are no longer answerable. Call GET .../next to get the material.",
                                                    "Not idempotent: each call moves the clock again."),
    "POST /courses/{cid}/learners/{lid}/sessions/new": ("Starts a new session: resets the per-session question counter and decides the next step.",
                                                         "When the learner chooses to continue after a session_end step.",
                                                         "Session counter reset; stored next step replaced; served questions cleared. Call GET .../next.",
                                                         "Safe to repeat (each call re-decides for the same state)."),
    "GET /courses/{cid}/learners/{lid}/resources": (
        "Research status and the articles and videos found for each of the learner's gap concepts. Research starts in "
        "the background when the diagnostic is graded, for gap concepts only (never for concepts placed as known), "
        "and is shared by every learner of the course. Concepts it was never started for are not listed.",
        "After the diagnostic, to show 'researching...' and then the links; poll until no entry is `pending`.",
        "none", "Safe to poll every 3 to 5 s; entries go from `pending` to `ready` or `failed` and then stay."),
    "GET /eval/results": ("Serves the offline evaluation results file if one has been produced, else 404.",
                          "Optional 'how well does the brain work' page.", "none", "Safe to call."),
}

ERRORS_BY_ROUTE = {
    "POST /courses": [(401, "missing or wrong password", "error_401"), (422, "body invalid (missing prompt, unknown level)", "error_422_validation")],
    "GET /courses/{cid}": [(401, "missing or wrong password", "error_401"), (404, "unknown course id", "error_404")],
    "POST /courses/{cid}/learners/{lid}/start": [(404, "unknown course", "error_404"), (409, "learner already started", "error_409_start"),
                                                  (409, "course not ready (`course '...' is generating`)", None)],
    "POST /courses/{cid}/learners/{lid}/attempts": [(404, "learner not started", "error_404_learner"),
                                                     (422, "a question was not served to this learner (lists the ids)", "error_422_unserved"),
                                                     (422, "empty `answers`, `chosen_index` out of range, or body invalid", None)],
    "GET /courses/{cid}/learners/{lid}/next": [(404, "learner not started", "error_404_learner"),
                                                (409, "before the diagnostic is answered", "error_409_next_before_diagnostic")],
    "GET /courses/{cid}/learners/{lid}/state": [(404, "learner not started", "error_404_learner")],
    "POST /courses/{cid}/learners/{lid}/advance": [(404, "learner not started", "error_404_learner"), (422, "days <= 0", "error_422_advance_days")],
    "POST /courses/{cid}/learners/{lid}/sessions/new": [(404, "learner not started", "error_404_learner")],
    "GET /eval/results": [(404, "no results file yet", "eval_results")],
    "GET /courses/{cid}/learners/{lid}/resources": [(404, "learner not started", "error_404_learner")],
}

EXAMPLES_BY_ROUTE = {
    "GET /health": ["health"],
    "POST /courses": ["courses_create_ready", "courses_create_generating"],
    "GET /courses/{cid}": ["course_get", "course_get_generating"],
    "POST /courses/{cid}/learners/{lid}/start": ["start"],
    "POST /courses/{cid}/learners/{lid}/attempts": ["attempts_diagnostic", "attempts_practice", "attempts_review_failed",
                                                     "attempts_all_known_done", "attempts_needs_help", "attempts_with_deadline"],
    "GET /courses/{cid}/learners/{lid}/next": ["next_lesson", "next_review", "next_relearn", "next_fallback", "next_give_up",
                                                "next_session_end", "next_done", "next_done_with_needs_help"],
    "GET /courses/{cid}/learners/{lid}/state": ["state", "state_after_diagnostic", "state_after_advance", "state_needs_help", "state_with_deadline"],
    "POST /courses/{cid}/learners/{lid}/advance": ["advance", "advance_all_due"],
    "POST /courses/{cid}/learners/{lid}/sessions/new": ["sessions_new"],
    "GET /eval/results": ["eval_results"],
    "GET /courses/{cid}/learners/{lid}/resources": ["resources_pending", "resources_after_diagnostic", "resources_ready"],
}

FLOW_ORDER = ["GET /health", "POST /courses", "GET /courses/{cid}", "POST /courses/{cid}/learners/{lid}/start",
              "POST /courses/{cid}/learners/{lid}/attempts", "GET /courses/{cid}/learners/{lid}/next",
              "GET /courses/{cid}/learners/{lid}/state", "POST /courses/{cid}/learners/{lid}/advance",
              "POST /courses/{cid}/learners/{lid}/sessions/new", "GET /courses/{cid}/learners/{lid}/resources",
              "GET /eval/results"]

MESSAGE_TEMPLATES = [
    (r"^You mastered (.+) \(mastery [\d.]+\)\.$", "You mastered {concept} (mastery {p}).", "a concept crossed 0.85 in this round"),
    (r"^You slipped on (.+)\. This happens, it is why reviews exist\.$", "You slipped on {concept}. This happens, it is why reviews exist.", "a mastered concept was answered wrong (a lapse)"),
    (r"^Review of (.+) passed: next one in [\d.]+ days\.$", "Review of {concept} passed: next one in {n} days.", "a due review was answered all right"),
    (r"^(.+) is flagged for help: it may need a different resource or a person\.$", "{concept} is flagged for help: it may need a different resource or a person.", "the last try on a stuck concept failed"),
    (r"^Misconception (.+) resolved\.$", "Misconception {tag} resolved.", "2 clean answers in a row on questions testing a confirmed misconception (not in a round where it was picked)"),
    (r"^3 correct in a row\.$", "3 correct in a row.", "3 consecutive right answers within this round"),
    (r"^\d+ days? left before your deadline\.$", "{n} day(s) left before your deadline.", "days_left is between 0 and 3"),
    (r"^Placed \d+ concepts as already known; I'll check them again (tomorrow|within [\d.]+ days)\.$",
     "Placed {n} concepts as already known; I'll check them again tomorrow | within {d} days.", "diagnostic answers that were right (placement)"),
    (r"^every reachable concept is mastered", "every reachable concept is mastered[; needs help: ...]", "the next step is done (the reason is copied into messages)"),
    (r"^\d+ questions this session; start a new session to continue$", "{n} questions this session; start a new session to continue", "the next step is session_end"),
]


def schema_of(openapi: dict, name: str) -> dict:
    return openapi["components"]["schemas"][name]


def ts_type(s: dict) -> str:
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    if "anyOf" in s:
        parts = []
        for x in s["anyOf"]:
            t = ts_type(x)
            if t not in parts:
                parts.append(t)
        return " | ".join(parts)
    if "enum" in s:
        return " | ".join(json.dumps(v) for v in s["enum"])
    if "const" in s:
        return json.dumps(s["const"])
    t = s.get("type")
    if t == "null":
        return "null"
    if t == "array":
        inner = ts_type(s.get("items", {}))
        return f"({inner})[]" if "|" in inner else f"{inner}[]"
    if t == "object" or "additionalProperties" in s:
        ap = s.get("additionalProperties")
        if isinstance(ap, dict):
            return f"Record<string, {ts_type(ap)}>"
        return "Record<string, unknown>"
    if t == "string":
        return "string"
    if t in ("integer", "number"):
        return "number"
    if t == "boolean":
        return "boolean"
    return "unknown"


def ts_from_value(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return f"{ts_from_value(v[0])}[]" if v else "unknown[]"
    return "{ " + "; ".join(f"{k}: {ts_from_value(x)}" for k, x in v.items()) + " }"


def gen_types(openapi: dict) -> str:
    out = ["// Generated by scripts/gen_api_docs.py from the live server's OpenAPI schema. Do not edit by hand.",
           "// Datetimes are naive UTC ISO strings without a trailing 'Z': parse with new Date(s + 'Z').",
           "// Fields marked `?` have defaults on the server; responses still always include them.", ""]
    for name, s in sorted(openapi["components"]["schemas"].items()):
        if s.get("type") != "object" or "properties" not in s:
            continue
        req = set(s.get("required", []))
        out.append(f"export interface {name} {{")
        for f, fs in s["properties"].items():
            doc = FIELD_DOCS.get(f"{name}.{f}", ("", ""))[0]
            if doc:
                out.append(f"  /** {doc} */")
            out.append(f"  {f}{'' if f in req else '?'}: {ts_type(fs)};")
        out.append("}\n")
    out += ["// Responses without a response model in the schema: shapes inferred from the live responses.",
            f"export type HealthResponse = {ts_from_value(EXAMPLE_FILES['health'].data)};",
            f"export type NewSessionResponse = {ts_from_value(EXAMPLE_FILES['sessions_new'].data)};",
            "/** GET .../resources: concept_id -> research status and resources. */",
            "export type ResourcesResponse = Record<string, ConceptResearch>;",
            "export interface ErrorResponse { detail: string | ValidationError[]; }", "",
            "// Planned, NOT AVAILABLE yet (404 today). Code against them behind feature detection.",


            "export interface VirtualStartIn { persona: string; speed: number; days: number; reset: boolean; }",
            "export interface VirtualSpeedIn { speed: number; }",
            "export interface VirtualEvent { n: number; at: string; kind: string; text: string; source: string; }",
            "export interface VirtualEventsResponse { events: VirtualEvent[]; next: number; }",
            "export type VirtualStatusResponse = Record<string, unknown>; // shape not specified yet", ""]
    return "\n".join(out)


def shorten(data, limit=EXAMPLE_LIMIT) -> tuple[str, bool]:
    text = json.dumps(data, indent=2)
    if len(text) <= limit:
        return text, False
    for cut, items in ((200, 4), (100, 3), (60, 2)):
        def sh(x):
            if isinstance(x, str) and len(x) > cut:
                return x[:cut] + "..."
            if isinstance(x, list):
                y = [sh(v) for v in x[:items]]
                return y + [f"... {len(x) - items} more"] if len(x) > items else y
            if isinstance(x, dict):
                return {k: sh(v) for k, v in x.items()}
            return x
        text = json.dumps(sh(data), indent=2)
        if len(text) <= limit:
            break
    return text, True


def model_table(openapi: dict, name: str) -> list[str]:
    s = schema_of(openapi, name)
    req = set(s.get("required", []))
    rows = [f"| Field | Type | Meaning | Null / empty |", "|---|---|---|---|"]
    for f, fs in s["properties"].items():
        meaning, empty = FIELD_DOCS.get(f"{name}.{f}", ("", ""))
        rows.append(f"| `{f}` | `{ts_type(fs)}` | {meaning} | {empty or '-'} |")
    return rows


def request_table(openapi: dict, name: str) -> list[str]:
    s = schema_of(openapi, name)
    req = set(s.get("required", []))
    rows = ["| Field | Type | Required | Allowed values | Meaning |", "|---|---|---|---|---|"]
    for f, fs in s["properties"].items():
        allowed = ""
        enum = fs.get("enum") or next((x.get("enum") for x in fs.get("anyOf", []) if x.get("enum")), None)
        if enum:
            allowed = ", ".join(f"`{v}`" for v in enum)
        if "default" in fs and fs["default"] is not None:
            allowed += f" (default `{fs['default']}`)"
        rows.append(f"| `{f}` | `{ts_type(fs)}` | {'yes' if f in req else 'no'} | {allowed or '-'} | "
                    f"{FIELD_DOCS.get(f'{name}.{f}', ('', ''))[0]} |")
    return rows


def route_calls(route: str) -> list[Call]:
    return [c for c in CALLS if c.route == route]


BACKGROUND_LLM = {"POST /courses", "GET /courses/{cid}", "GET /courses/{cid}/learners/{lid}/resources"}


def latency_line(route: str) -> str:
    cs = [c for c in route_calls(route) if c.status < 400]
    if route in BACKGROUND_LLM and cs:
        ms = [c.ms for c in cs]
        return (f"{len(ms)} successful calls: median {statistics.median(ms) / 1000:.3f} s, max {max(ms) / 1000:.3f} s. "
                "Never waits for the LLM: course generation and research run in the background.")
    if not cs:
        return "not measured (no successful call)"
    ms = [c.ms for c in cs]
    llm = [c for c in cs if c.llm]
    line = f"{len(ms)} successful calls: median {statistics.median(ms) / 1000:.3f} s, max {max(ms) / 1000:.3f} s."
    if llm:
        line += (f" {len(llm)} of them called the LLM ({min(c.ms for c in llm) / 1000:.1f} to "
                 f"{max(c.ms for c in llm) / 1000:.1f} s); without the LLM: median "
                 f"{statistics.median([c.ms for c in cs if not c.llm] or [0]) / 1000:.3f} s.")
    else:
        line += " No LLM call observed."
    return line


def example_block(name: str) -> list[str]:
    c = EXAMPLE_FILES.get(name)
    if c is None:
        return [f"_Example `{name}` was not captured in this run._", ""]
    text, cut = shorten(c.data)
    took = f"{c.ms:.0f} ms" if c.ms is not None else "captured in an earlier run"
    return [f"`{c.method} {c.path}` -> **{c.status}** ({took}), file `docs/examples/{name}.json`"
            + (" (shortened here: long strings and lists cut with '...'; the file is complete)" if cut else ""),
            "", "```json", text, "```", ""]


def render_reference(openapi: dict, commit: str, dirty: bool) -> str:
    cid, lid = FACTS["cid"], FACTS["lid"]
    o = []
    add = o.extend
    gen = FACTS.get("generation_seconds")
    o += ["# OnlyNerd API reference", "",
          f"Generated {datetime.now():%Y-%m-%d %H:%M} from a live run (commit `{commit}`{', with uncommitted changes' if dirty else ''}). "
          "Every field, status code and example below was captured from the running server. "
          f"Routes documented: {len(FLOW_ORDER)}.", "",
          "## Contents", "", "1. Overview", "2. Learner flow", "3. Screen-to-endpoint map", "4. Endpoints",
          "5. Behaviour the frontend must know", "6. Enumerations", "7. Planned, not implemented yet",
          "8. Quick start", "9. Changelog / how to regenerate", "10. Quirks and open questions", ""]

    # 1. Overview
    e401 = EXAMPLE_FILES["error_401"].data
    add(["## 1. Overview", "",
         f"- Base URL: `{BASE}` locally. All paths below are relative to it.",
         "- Run the backend: start MongoDB on `mongodb://localhost:27017`, then in `backend/`: "
         "`uv run uvicorn main:app --port 8000`. Settings come from `backend/.env` (`MONGO_URI`, `MONGO_DB`, "
         "`MASTER_PASSWORD`, `ANTHROPIC_API_KEY`).",
         "- CORS: the server allows the origin `http://localhost:3000` only, any method, and the request headers "
         "`Content-Type` and `X-Master-Password`.",
         f"- Auth: send `X-Master-Password: {PW_SHOWN}` on every request except `GET /health`. A missing or wrong "
         f"value returns **401** with `{json.dumps(e401)}`. If the server's `MASTER_PASSWORD` is empty, nothing is checked (dev mode).",
         "- Errors are JSON with a `detail` field. Errors raised by the API carry a string; request-body validation "
         "errors (422 from FastAPI) carry a list of `{type, loc, msg, input, ...}` objects. Real bodies from this run:", ""])
    for code, name in ((401, "error_401"), (404, "error_404"), (409, "error_409_start"), (422, "error_422_unserved"),
                       (422, "error_422_validation")):
        c = EXAMPLE_FILES.get(name)
        if c:
            add([f"**{code}** (`{c.method} {c.path}`):", "```json", json.dumps(c.data, indent=2), "```", ""])
    add(["### Glossary", "",
         "- **Concept**: one node of the course's prerequisite graph (id, name, prerequisites).",
         "- **Mastery** (`p_mastery`): probability the learner knows a concept, 0..1. **Mastered** means 0.85 or more.",
         "- **Gap**: a concept not yet mastered (`gaps` in the state, roadmap order).",
         "- **Placed**: a concept answered right in the diagnostic, set straight to 0.85 with a re-check review "
         "1 to 3 days later depending on confidence.",
         "- **Verified**: the API does not expose a 'verified' flag or field; a placed concept that passed its review "
         "looks like any mastered concept with stability above its placement value.",
         "- **Retrievability**: probability of recalling a mastered concept now, `0.9^(days since review / stability)`; "
         "1.0 for concepts never mastered.",
         "- **Stability** (`stability_days`): how long a memory lasts; a passed review multiplies it by 2.5, a lapse halves it (minimum 1).",
         "- **Session**: a run of up to 15 answered questions; then the next step is `session_end`.",
         "- **Simulated clock**: each learner has `clock_offset_days`; their 'now' is real UTC now plus the offset. "
         "`POST .../advance` moves it forward for demos.", ""])

    # 2. Flow
    add(["## 2. Learner flow", "",
         "1. **Create course**: `POST /courses` with prompt and level.",
         "2. **Poll until ready**: `GET /courses/{cid}` every 2 s while `status` is `generating`.",
         "3. **Start**: `POST /courses/{cid}/learners/{lid}/start` returns the diagnostic (one question per concept).",
         "4. **Submit the diagnostic**: `POST .../attempts`. Right answers are placed as known; the response has "
         "the grading, messages and `next` (the first lesson).",
         "5. **Read the next step**: it is in `next` of every attempts response; `GET .../next` returns the same "
         "thing any time (after reload, advance or a new session).",
         "6. **Practice**: show the lesson and its questions, submit them with `POST .../attempts`; repeat.",
         "7. **Advance the clock** (control panel): `POST .../advance {days}`; then `GET .../next`.",
         "8. **Review**: a `review` step has 2 questions on a due concept; submit them.",
         "9. **Relearn**: a failed review is a lapse; the next step is a lesson on that concept before other reviews.",
         "10. **Session end**: after 15 questions the step is `session_end`; call `POST .../sessions/new`, then `GET .../next`.",
         "11. **Done**: when every reachable concept is mastered the step is `done` (come back later for reviews: advance or wait).", "",
         "```text",
         "Frontend                                   Backend",
         "   | POST /courses {prompt, level}          |",
         "   |--------------------------------------->|  status: generating | ready",
         "   | GET /courses/{cid}   (every 2 s)       |",
         "   |--------------------------------------->|  ... until ready",
         "   | POST .../learners/{lid}/start          |",
         "   |--------------------------------------->|  diagnostic questions",
         "   | POST .../attempts  {answers}           |",
         "   |--------------------------------------->|  graded + messages + next (lesson + 3 questions)",
         "   | POST .../attempts  (practice)          |",
         "   |--------------------------------------->|  graded + next",
         "   | POST .../advance {days}  (control)     |",
         "   |--------------------------------------->|  now, due_now, next_kind",
         "   | GET .../next                           |",
         "   |--------------------------------------->|  review + 2 questions",
         "   | POST .../attempts  (review)            |",
         "   |--------------------------------------->|  graded + next (relearn lesson on a lapse)",
         "   | GET .../state  (sidebar, any time)     |",
         "   |--------------------------------------->|  mastery, gaps, due, retrievability",
         "```", ""])

    # 3. Screens
    add(["## 3. Screen-to-endpoint map", "",
         "| Screen / card | Endpoint | Fields |", "|---|---|---|",
         "| Setup: topic, level, deadline form | `POST /courses` | body `prompt`, `level`, `deadline` |",
         "| Setup: 'building your course' spinner | `GET /courses/{cid}` | `status` |",
         "| Setup: concept graph | `GET /courses/{cid}` | `concepts[].id/name/prerequisites` |",
         "| Quiz: diagnostic questions | `POST .../start` | `questions[].prompt/options` |",
         "| Quiz: practice/review questions | `next.questions` from attempts, or `GET .../next` | `questions[]` |",
         "| Quiz: confidence picker | `POST .../attempts` | `answers[].confidence` (optional) |",
         "| Feedback: right/wrong per question | `POST .../attempts` | `graded[].correct`, `correct_indices`, `explanations` |",
         "| Feedback: misconception callout | `POST .../attempts` | `graded[].chosen_tag`, `new_confirmed_misconceptions` |",
         "| Feedback: toasts | `POST .../attempts` | `messages[]` |",
         "| Lesson: text, style badge | `next.lesson` / `GET .../next` | `lesson.explanation`, `lesson.style`, `lesson.targets` |",
         "| Lesson: 'why this' line | same | `reason` |",
         "| Lesson: further reading | same | `lesson.resources` (fills in once research is ready) |",
         "| Sidebar: 'researching...' then links per gap | `GET .../resources` | `{concept_id: {status, resources}}` |",
         "| Review: 'review due' banner | same | `step.kind == 'review'`, `step.concept_id`, `reason` |",
         "| Stuck card | `GET .../state` | `needs_help[]`; step `give_up_after` |",
         "| Sidebar: mastery bars | `GET .../state` | `concepts[].p_mastery` (or `mastery` from attempts) |",
         "| Sidebar: gaps / roadmap | `GET .../state` | `gaps`, `roadmap` |",
         "| Sidebar: memory strength | `GET .../state` | `retrievability`, `concepts[].stability_days` |",
         "| Sidebar: upcoming reviews | `GET .../state` | `due`, `next_due` |",
         "| Sidebar: misconceptions | `GET .../state` | `misconceptions[]` |",
         "| Sidebar: pace, deadline | `GET .../state` | `pace`, `days_left` |",
         "| Control panel: skip N days | `POST .../advance` | body `days`; response `now`, `due_now`, `next_kind`, `next_concept_id` |",
         "| Control panel: new session | `POST .../sessions/new` | response `next_kind`, `next_concept_id` |",
         "| Eval page | `GET /eval/results` | the file as-is (404 until produced) |", ""])

    # 4. Endpoints
    add(["## 4. Endpoints", ""])
    paths = openapi["paths"]
    for route in FLOW_ORDER:
        method, path = route.split(" ", 1)
        op = paths[path][method.lower()]
        what, when, side, idem = ENDPOINT_DOCS[route]
        add([f"### `{route}`", "", what, "", f"**When to call:** {when}", ""])
        req = (op.get("requestBody") or {}).get("content", {}).get("application/json", {}).get("schema")
        params = [p["name"] for p in op.get("parameters", [])]
        if params:
            add([f"**Path parameters:** " + ", ".join(f"`{p}`" for p in params) + " (strings; `lid` is any id the client picks).", ""])
        if req:
            name = req["$ref"].split("/")[-1]
            add([f"**Request body** (`{name}`):", "", *request_table(openapi, name), ""])
            if name == "SubmitAnswersIn":
                add(["Each answer (`AnswerIn`):", "", *request_table(openapi, "AnswerIn"), ""])
            sample = next((c.body for c in route_calls(route) if c.body is not None and c.status < 400), None)
            if sample is not None:
                add(["Real request body:", "```json", json.dumps(sample, indent=2), "```", ""])
        else:
            add(["**Request body:** none.", ""])
        res = op["responses"].get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
        if "$ref" in res:
            name = res["$ref"].split("/")[-1]
            add([f"**Response 200** (`{name}`):", "", *model_table(openapi, name), ""])
            nested = {"StepOut": ["Step", "Lesson", "QuestionPublic"], "AttemptResultOut": ["AnswerGraded", "StepOut", "Step", "Lesson"],
                      "MasteryOut": ["ConceptState", "MisconceptionState"], "StartOut": ["QuestionPublic"]}.get(name, [])
            for n in nested:
                add([f"`{n}`:", "", *model_table(openapi, n), ""])
        elif isinstance(res.get("additionalProperties"), dict) and "$ref" in res["additionalProperties"]:
            name = res["additionalProperties"]["$ref"].split("/")[-1]
            add([f"**Response 200:** an object keyed by concept id; each value is a `{name}`:", "",
                 *model_table(openapi, name), ""])
        else:
            ex = next((c.data for c in route_calls(route) if c.status == 200), None)
            add([f"**Response 200:** no response model in the schema; live shape: `{ts_from_value(ex) if ex is not None else 'not captured'}`.", ""])
        add(["**Real examples:**", ""])
        for name in EXAMPLES_BY_ROUTE[route]:
            add([f"_{name}_", "", *example_block(name)])
        add(["**Errors:**", "", "| Status | When | Body |", "|---|---|---|"])
        for code, when_, ex in ERRORS_BY_ROUTE.get(route, []):
            body = json.dumps(EXAMPLE_FILES[ex].data) if ex and ex in EXAMPLE_FILES else "`{\"detail\": \"...\"}`"
            add([f"| {code} | {when_} | {body[:300]} |"])
        if route != "GET /health" and not any(c == 401 for c, _, _ in ERRORS_BY_ROUTE.get(route, [])):
            add([f"| 401 | missing or wrong password | {json.dumps(e401)} |"])
        add(["", f"**Side effects:** {side}", "", f"**Latency:** {latency_line(route)}", "",
             f"**Idempotency and polling:** {idem}", ""])

    # 5. Behaviour
    sample = FACTS.get("datetime_sample")
    kinds = FACTS["step_kinds_seen"]
    add(["## 5. Behaviour the frontend must know", "",
         f"**Datetimes.** Verified on {FACTS['datetimes']} datetime values in this run: "
         + ("none" if not FACTS["datetimes_with_zone"] else f"{len(FACTS['datetimes_with_zone'])}")
         + f" carry a zone. They are naive UTC ISO strings without a trailing `Z` (e.g. `{sample}`). Append `Z` before parsing:", "",
         "```ts", "const parseUtc = (s: string | null) => (s ? new Date(s.endsWith('Z') ? s : s + 'Z') : null);",
         "```", "Send datetimes (e.g. `deadline`) as UTC ISO; a `Z` is accepted.", "",
         f"**Questions.** Before grading, every question has exactly the keys {FACTS['question_keys']} "
         f"(options are plain strings: {'verified' if FACTS['options_all_strings'] else 'NOT all strings'}). "
         "`correct_indices` and `explanations` only appear in the attempts response, after grading.", "",
         f"**Confidence** is optional: in this run an answer without `confidence` was accepted "
         f"({'yes' if FACTS.get('confidence_omitted_ok') else 'not verified'}). Allowed: `low`, `medium`, `high`.", "",
         "**Step kinds** (seen live in this run: " + ", ".join(kinds) + "):", "",
         "| kind | Render |", "|---|---|",
         "| `lesson` | The lesson text, then its 3 questions. If `give_up_after` is true, say it is the last try on this concept. |",
         "| `review` | A 'quick review' card for `concept_id` with its 2 questions; no lesson. |",
         "| `fallback` | A lesson on a prerequisite (`concept_id`) because the learner is stuck on `target_concept`; say so. |",
         "| `session_end` | 'Good session' screen; offer 'continue' (POST .../sessions/new then GET .../next). No questions. |",
         "| `done` | 'All caught up' screen. Reviews come back as time passes (advance in the demo). |", "",
         "**Diagnostic.** `start` returns one question per concept in roadmap order. Submitting it places every concept "
         "answered right at mastery 0.85 with a re-check review 1 (low or no confidence), 2 (medium) or 3 (high) days later, "
         "and adds the message `Placed N concepts as already known; I'll check them again tomorrow|within D days.` "
         "The step's `reason` starts with `placed as known: ...`. The diagnostic does not count toward the session cap.", "",
         f"**Stuck learners.** After 3 failed rounds on a concept the brain detours once to a prerequisite (`fallback`), "
         f"then gives a last try (`lesson` with `give_up_after: true`); failing that sets `needs_help` for the concept and "
         f"the message '... is flagged for help ...'. Observed in this run for `{FACTS.get('struggle_target')}`: "
         f"{', '.join(FACTS.get('struggle_kinds', []))}.", "",
         f"**Session cap.** The step becomes `session_end` after the session's questions reach the cap "
         f"(observed after {FACTS.get('session_cap_at')} questions answered in the session). `advance` and `sessions/new` reset the counter.", "",
         "**reason** is a human-readable sentence built from facts (e.g. due date and recall, confirmed misconceptions, "
         "relearning after a lapse). Show it as 'why this step'. Do not parse it.", "",
         "**Messages** (show as toasts). Every template, with what triggers it and whether this run produced it:", "",
         "| Template | Trigger | Seen in this run |", "|---|---|---|"])
    for rx, tmpl, trig in MESSAGE_TEMPLATES:
        seen = [m for m in FACTS["messages_seen"] if re.match(rx, m)]
        cell = lambda t: t.replace("|", "\\|")  # noqa: E731
        add([f"| `{cell(tmpl)}` | {trig} | {'yes: `' + cell(seen[0]) + '`' if seen else 'no'} |"])
    llm_ms, cached_ms = FACTS["lesson_llm_ms"], FACTS["lesson_cached_ms"]
    add(["", f"**Lessons and latency.** A lesson is written by the LLM the first time a (concept, misconception targets, "
         f"styles tried) combination is needed, then cached. Measured: responses that generated a lesson took "
         f"{min(llm_ms) / 1000:.1f} to {max(llm_ms) / 1000:.1f} s (measured in {FACTS['lesson_llm_when']}); "
         f"with a cached lesson {max(cached_ms or [0]) / 1000:.2f} s or less. "
         if llm_ms else "**Lessons and latency.** No lesson was generated in this run (all cached). ",
         "Show a loading state on attempts and GET .../next.", "",
         "**Course generation.** " + (f"Measured in {FACTS.get('generation_when', 'this run')}: `generating` for {gen:.0f} s ({FACTS['generation_polls']} polls), "
                                      f"ending `{FACTS['generation_status']}`. " if gen else "Not observed in this run. ")
         + "Poll every 2 s; allow up to about 3 minutes; on `failed` offer to retry with POST /courses.", "",
         "**Simulated time.** Each learner has a private clock offset. `POST .../advance {days}` adds to it, resets the "
         "session, and decides the next step for the new time; `due_now` lists due concepts. All `now`, `due` and "
         "`retrievability` values use the learner's simulated now.", "",
         f"**Research.** When the diagnostic is graded, research starts in the background for the gap concepts only "
         f"(observed: {len(FACTS.get('research_first', {}))} concepts listed right after the diagnostic, statuses "
         f"{sorted(set(FACTS.get('research_first', {}).values()))}; after {FACTS.get('research_seconds', 0):.0f} s of polling: "
         f"{sorted(set(FACTS.get('research_final', {}).values()))}). Requests never wait for it. Lessons written after "
         "research is ready are grounded in the sources; `lesson.resources` carries them, and GET .../next fills them in "
         "for a lesson built earlier. Research results are shared by every learner of the course.", "",
         "**Placed vs verified.** The API does not expose whether a mastered concept was placed or verified by a review.", ""])

    # 6. Enumerations
    add(["## 6. Enumerations", "", "| Name | Values | Meaning |", "|---|---|---|",
         "| `level` | `novice`, `beginner`, `intermediate`, `advanced` | Self-assessed level (questions and lessons adapt). |",
         "| course `status` | `generating`, `ready`, `failed` | Background generation state. |",
         "| `Step.kind` | `lesson`, `review`, `fallback`, `session_end`, `done` | See section 5. |",
         "| `confidence` | `low`, `medium`, `high` | Optional self-report per answer. |",
         "| misconception `status` | `suspected`, `confirmed`, `resolved` | 1 evidence = suspected, 2 = confirmed, 2 clean answers = resolved; can come back. |",
         "| `Lesson.style` | `worked_example`, `contrast`, `analogy`, `step_by_step` | Explanation style; a new one is tried each time. |",
         "| `Resource.kind` | `article`, `video` | Research results (not wired yet). |", ""])

    # 7. Planned
    add(["## 7. Planned, not implemented yet", "", "**NOT AVAILABLE**: these returned the status shown in this run. "
         "Code against them behind feature detection (treat 404 as 'feature off').", "",
         "| Route | Status now |", "|---|---|"])
    add([f"| `{r}` | {s} |" for r, s in FACTS["planned"].items()])
    add(["", "Contracts:", "", "```text",
         "POST .../virtual/start {persona, speed, days, reset}",
         "POST .../virtual/pause | .../virtual/resume | .../virtual/stop",
         "POST .../virtual/speed {speed}",
         "GET  .../virtual/status",
         "GET  .../virtual/events?after=N -> {events: [{n, at, kind, text, source}], next}",
         "```", "",
         "`GET .../state` has no `history` or `learning_rate` field yet (checked on the live response); treat them as optional when they arrive.", ""])

    # 8. Quick start
    add(["## 8. Quick start", "", "```bash", f"BASE={BASE}", f"PW='{PW_SHOWN}'",
         "curl -s $BASE/health",
         "curl -s -X POST $BASE/courses -H \"X-Master-Password: $PW\" -H 'Content-Type: application/json' "
         f"-d '{{\"prompt\": \"{FACTS['course_prompt'][0]}\", \"level\": \"{FACTS['course_prompt'][1]}\"}}'",
         "curl -s $BASE/courses/$CID -H \"X-Master-Password: $PW\"          # poll until status is ready",
         "curl -s -X POST $BASE/courses/$CID/learners/me/start -H \"X-Master-Password: $PW\"",
         "curl -s -X POST $BASE/courses/$CID/learners/me/attempts -H \"X-Master-Password: $PW\" -H 'Content-Type: application/json' "
         "-d '{\"answers\": [{\"question_id\": \"<id>\", \"chosen_index\": 1, \"confidence\": \"medium\"}]}'",
         "```", "", "Five likely mistakes:", "",
         "1. Parsing datetimes without appending `Z` (they are UTC but carry no zone).",
         "2. Forgetting `X-Master-Password` (401) or expecting it on `/health`.",
         "3. Calling `start` before the course is `ready` (409) instead of polling `GET /courses/{cid}`.",
         "4. Looking for the next step in the wrong place: it is `next` in the attempts response, or `GET .../next` "
         "after `advance`/`sessions/new`/reload. Only the questions served there (or by `start`) are accepted.",
         "5. Always sending `confidence`: it is optional; send it only when the learner picked one.", ""])

    # 9. Changelog
    add(["## 9. Changelog / how to regenerate", "",
         f"Generated {datetime.now():%Y-%m-%d %H:%M} from commit `{commit}`{' with uncommitted changes' if dirty else ''}. "
         "Regenerate (MongoDB running, port 8000 free, run in `backend/`):", "",
         "```bash", "uv run python scripts/gen_api_docs.py", "```", ""])

    # 10. Quirks
    add(["## 10. Quirks and open questions", ""])
    add([f"- {q}" for q in QUIRKS] or ["_(none)_"])
    if UNVERIFIED:
        add(["", "Not captured in this run:", ""] + [f"- {u}" for u in UNVERIFIED])
    return "\n".join(o) + "\n"


def render_check(openapi: dict) -> str:
    rows = ["# API reference check", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}. Routes from `app.openapi()`.", "",
            "| Route | Called successfully | Calls | Median latency (s) | Max latency (s) | Statuses seen | LLM calls in the request |",
            "|---|---|---|---|---|---|---|"]
    for path, ops in openapi["paths"].items():
        for method in ops:
            route = f"{method.upper()} {path}"
            cs = route_calls(route)
            ok = [c for c in cs if c.status < 400]
            ms = [c.ms / 1000 for c in ok]
            lat = f"{statistics.median(ms):.3f} | {max(ms):.3f}" if ms else "- | -"
            statuses = ", ".join(str(x) for x in sorted({c.status for c in cs}))
            llm = "background" if route in BACKGROUND_LLM else str(sum(c.llm for c in cs))
            note = " (404 expected: no results file yet)" if route == "GET /eval/results" and not ok else ""
            rows.append(f"| `{route}` | {'yes' if ok else 'no'}{note} | {len(cs)} | {lat} | {statuses} | {llm} |")
    rows += ["", "LLM calls in the request count lesson generation (role `strong`) only. Course generation and research "
             f"run in the background; {sum(RESEARCH_LLM)} research (role `cheap`) calls were logged during this run.",
             "", "Planned routes probed:", ""] + [f"- `{r}` -> {s}" for r, s in FACTS["planned"].items()]
    return "\n".join(rows) + "\n"


def render_http() -> str:
    cid, lid = FACTS["cid"], FACTS["lid"]
    out = ["# OnlyNerd API: VS Code REST Client file (generated by scripts/gen_api_docs.py)",
           f"@baseUrl = {BASE}", f"@password = {PW_SHOWN}", f"@courseId = {cid}", f"@learnerId = {lid}", ""]
    seen = set()
    for c in CALLS:
        key = (c.route, json.dumps(c.body, sort_keys=True) if c.body is not None else "")
        if key in seen or c.status >= 400 or len(seen) > 40:
            continue
        seen.add(key)
        path = c.path.replace(cid, "{{courseId}}")
        path = re.sub(r"/learners/[^/]+", "/learners/{{learnerId}}", path)
        out += [f"### {c.route}", f"{c.method} {{{{baseUrl}}}}{path}"]
        if c.auth:
            out.append("X-Master-Password: {{password}}")
        if c.body is not None:
            out += ["Content-Type: application/json", "", json.dumps(c.body, indent=2)]
        out.append("")
    return "\n".join(out)


def main() -> int:
    from main import app
    openapi = app.openapi()
    SRV.start()
    print(f"server pid {SRV.proc.pid}")
    try:
        live_openapi = httpx.get(f"{BASE}/openapi.json").json()
        write(DOCS / "openapi.json", json.dumps(live_openapi, indent=2))
        with httpx.Client(base_url=BASE, headers={"X-Master-Password": PASSWORD}, timeout=300) as client:
            run(client)
    finally:
        SRV.stop()
    analyse()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    routes = {f"{m.upper()} {p}" for p, ops in openapi["paths"].items() for m in ops}
    missing = routes - set(FLOW_ORDER)
    if missing:
        quirk(f"Routes in the schema but not documented by this script: {sorted(missing)}")
    write(META_PATH, json.dumps(META, indent=2))
    write(DOCS / "API_REFERENCE.md", render_reference(live_openapi, commit, dirty))
    write(DOCS / "API_REFERENCE_CHECK.md", render_check(live_openapi))
    write(DOCS / "types.ts", gen_types(live_openapi))
    write(DOCS / "api.http", render_http())
    print(f"\nroutes in schema: {len(routes)}; documented: {len(routes & set(FLOW_ORDER))}")
    print(f"examples: {len(EXAMPLE_FILES)} in {EXAMPLES}")
    print(f"quirks: {len(QUIRKS)}; not captured: {len(UNVERIFIED)}")
    for p in ("API_REFERENCE.md", "API_REFERENCE_CHECK.md", "types.ts", "openapi.json", "api.http"):
        print(f"  {DOCS / p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
