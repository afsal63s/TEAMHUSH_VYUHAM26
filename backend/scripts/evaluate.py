"""Offline evaluation: do OnlyNerd's interventions improve mastery AND retention?

Usage: uv run python scripts/evaluate.py

No LLM, no network, no server. Simulated learners with a hidden profile study a real course bundle
through the real engine (core.engine / core.policy / core.scheduler, simulated Clock) under three
arms, paired on the same learners:
  static              fixed concept order, untargeted lessons, no reviews
  adaptive_no_review  full adaptive policy, reviews disabled
  adaptive            full adaptive policy with scheduled reviews
Each arm: 15 questions per session, 5 sessions, one session per day. Then a held-out test (questions
never used in training, transfer questions included) right after the last session and at +7 and +30
simulated days.

Writes results/results.json (served as-is by GET /eval/results) and results/eval.md.

Simulator assumptions (also listed under "limits" and "assumptions" in results.json):
- Hidden knowledge k per concept is the chance the learner truly knows it. Not knowing, the learner
  picks the option tagged with a misconception they hold (70%) or guesses uniformly.
- A lesson raises k by pace * (1 - k); a lesson that targets a misconception the learner holds removes it.
- Each answered question (with its explanation) raises k by 0.2 * pace * (1 - k).
- Between days k decays toward the learner's prior with exp(-forgetting * days / stability). Answering a
  question on a concept at least a day after the previous one multiplies its stability (x1.8 if right,
  x1.2 if wrong): the spacing effect that scheduled reviews exploit.
"""

import hashlib
import inspect
import json
import math
import random
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.grading import topo_order  # noqa: E402
from api.learners import place_known  # noqa: E402  (the product's diagnostic placement)
from core import engine  # noqa: E402
from core.clock import Clock  # noqa: E402
from generation import CourseBundle  # noqa: E402
from schemas.content import Question  # noqa: E402
from schemas.learner import AnswerGraded, ConceptState, LearnerState, PolicyConfig  # noqa: E402

BUNDLES = ["python_novice", "python_advanced"]
LEARNERS = 100
SESSIONS, PER_SESSION = 5, 15
DELAYS = (7, 30)
BOOT = 2000
SEED = 20261031
START = datetime(2026, 1, 5, 18, 0)
RESULTS = ROOT / "results"

ARMS = {
    "static": PolicyConfig(adaptive=False, target_misconceptions=False, spaced_review=False),
    "adaptive_no_review": PolicyConfig(spaced_review=False),
    "adaptive": PolicyConfig(),
}
PLACEMENT = {"static": False, "adaptive_no_review": True, "adaptive": True}   # placement is an adaptive feature

GUESS, SLIP, MISCONCEPTION_PULL = 0.25, 0.1, 0.7
FEEDBACK_GAIN = 0.2
STABILITY_START, SPACED_RIGHT, SPACED_WRONG = 2.0, 1.8, 1.2

LIMITS = [
    "The learners are simulated, so these results measure the design of the system, not what real people would do.",
    "The effect of a lesson on hidden knowledge is an assumption of the simulator, so part of the gain from "
    "adaptivity (targeting misconceptions, choosing what to teach) is built into the model.",
    "The retention benefit of reviews rests on an assumed spacing effect (stability grows when a concept is "
    "practised again after at least a day), so the review arm's advantage is partly built in too.",
    "The confidence intervals reflect simulation noise (which learners were sampled) only, not uncertainty "
    "about whether the simulator matches real learning.",
]


# --- hidden learner ---

@dataclass
class Hidden:
    """Everything the simulated learner really is. The engine's LearnerState is never consulted."""
    prior: dict[str, float]
    knowledge: dict[str, float]
    stability: dict[str, float]
    last_retrieval_day: dict[str, float]
    misconceptions: list[str]
    pace: float
    forgetting: float

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def sample_profile(bundle: CourseBundle, seed: int) -> Hidden:
    rng = random.Random(seed)
    ability = rng.uniform(0.0, 0.5)
    prior = {c.id: min(0.9, max(0.0, ability + rng.gauss(0, 0.15))) for c in bundle.graph.concepts}
    tags = [m.tag for m in bundle.graph.misconceptions]
    return Hidden(
        prior=prior, knowledge=dict(prior), stability={c: STABILITY_START for c in prior},
        last_retrieval_day={}, misconceptions=sorted(rng.sample(tags, rng.randint(2, 4))),
        pace=rng.uniform(0.15, 0.35), forgetting=rng.uniform(0.3, 0.7),
    )


def p_correct(hidden: Hidden, q: Question) -> float:
    """Chance of a right answer, from the hidden state only."""
    k = hidden.knowledge[q.concept_id]
    tempted = any(o.misconception_tag in hidden.misconceptions for o in q.options if o.misconception_tag)
    p_guess = (1 - MISCONCEPTION_PULL) * GUESS if tempted else GUESS
    return k * (1 - SLIP) + (1 - k) * p_guess


def answer(hidden: Hidden, q: Question, rng: random.Random) -> tuple[int, str]:
    """Pick an option and a confidence from the hidden state only."""
    knows = rng.random() < hidden.knowledge[q.concept_id]
    if knows and rng.random() > SLIP:
        return q.correct_index, ("high" if rng.random() < 0.6 else "medium")
    held = [i for i, o in enumerate(q.options) if o.misconception_tag in hidden.misconceptions]
    if held and rng.random() < MISCONCEPTION_PULL:
        return rng.choice(held), "high"
    return rng.randrange(len(q.options)), rng.choice(["low", "low", "medium", "high"])


def practise(hidden: Hidden, concept: str, correct: bool, day: float) -> None:
    k = hidden.knowledge[concept]
    hidden.knowledge[concept] = k + FEEDBACK_GAIN * hidden.pace * (1 - k)
    last = hidden.last_retrieval_day.get(concept)
    if last is not None and day - last >= 1:
        hidden.stability[concept] *= SPACED_RIGHT if correct else SPACED_WRONG
    hidden.last_retrieval_day[concept] = day


def teach(hidden: Hidden, concept: str, targets: list[str]) -> None:
    k = hidden.knowledge[concept]
    hidden.knowledge[concept] = k + hidden.pace * (1 - k)
    hidden.misconceptions = [m for m in hidden.misconceptions if m not in targets]


def decay(hidden: Hidden, days: float) -> None:
    for c, k in hidden.knowledge.items():
        p0 = hidden.prior[c]
        hidden.knowledge[c] = p0 + (k - p0) * math.exp(-hidden.forgetting * days / hidden.stability[c])


# --- course split: training pool vs held-out test ---

def split(bundle: CourseBundle) -> tuple[dict[str, list[Question]], list[Question], dict[str, Question]]:
    """Per concept: the last transfer and last diagnostic question are held out; the rest is the training pool."""
    pool, held, diag = {}, [], {}
    for c in bundle.graph.concepts:
        qs = sorted((q for q in bundle.questions if q.concept_id == c.id), key=lambda q: q.id)
        out = [next(q for q in reversed(qs) if q.kind == k) for k in ("transfer", "diagnostic")
               if any(q.kind == k for q in qs)]
        held += out
        pool[c.id] = [q for q in qs if q not in out]
        diag[c.id] = next((q for q in pool[c.id] if q.kind == "diagnostic"), pool[c.id][0])
    return pool, held, diag


def test_score(hidden: Hidden, held: list[Question]) -> float:
    return sum(p_correct(hidden, q) for q in held) / len(held)


# --- one learner through one arm ---

RANK = {"practice": 0, "review": 0, "transfer": 1, "diagnostic": 2}


def run_arm(arm: str, bundle: CourseBundle, seed: int, pool, held, diag, audit: dict) -> dict:
    hidden = sample_profile(bundle, seed)
    audit["fingerprints"].setdefault(seed, set()).add(hidden.fingerprint())
    rng = random.Random(seed * 7 + 1)                        # same answer stream per learner in every arm
    config, clock = ARMS[arm], Clock(START)
    roadmap = topo_order(bundle.graph)
    state = LearnerState(learner_id=f"sim{seed}", course_id=bundle.course_id, roadmap=roadmap,
                         concepts={c: ConceptState(concept_id=c) for c in roadmap})
    held_ids = {q.id for q in held}
    seen: set[str] = set()
    counts = {"questions": 0, "lessons": 0, "reviews": 0, "fallbacks": 0, "targeted": 0}

    def answer_round(questions: list[Question], day: float) -> list[AnswerGraded]:
        graded = []
        for q in questions:
            if q.id in held_ids:
                audit["held_out_served"] += 1
            chosen, conf = answer(hidden, q, rng)
            correct = chosen == q.correct_index
            practise(hidden, q.concept_id, correct, day)
            graded.append(AnswerGraded(question_id=q.id, concept_id=q.concept_id, correct=correct,
                                       chosen_tag=q.options[chosen].misconception_tag, confidence=conf))
            seen.add(q.id)
        counts["questions"] += len(questions)
        return graded

    for day in range(SESSIONS):
        if day:
            clock.advance(days=1)
            decay(hidden, 1)
        state.session_questions, used = 0, 0
        if day == 0:                                         # the diagnostic: one question per concept
            qs = [diag[c] for c in roadmap]
            graded = answer_round(qs, day)
            engine.submit_answers(state, qs, graded, config, clock)
            if PLACEMENT[arm]:
                place_known(state, graded, clock.now())
            used = len(qs)
            state.session_questions = used
        while used < PER_SESSION:
            step = engine.get_next(state, bundle.graph, config, clock)
            if step.kind in ("done", "session_end"):
                break
            cid = step.concept_id
            if step.kind in ("lesson", "fallback"):
                teach(hidden, cid, step.target_misconceptions)
                counts["lessons"] += 1
                counts["fallbacks"] += step.kind == "fallback"
                counts["targeted"] += bool(step.target_misconceptions)
                n = 3
            else:
                counts["reviews"] += 1
                n = 2
            ordered = sorted(pool[cid], key=lambda q: (RANK[q.kind], q.id))
            qs = ([q for q in ordered if q.id not in seen] + [q for q in ordered if q.id in seen])[:min(n, PER_SESSION - used)]
            graded = answer_round(qs, day)
            engine.submit_answers(state, qs, graded, config, clock)
            used += len(qs)

    out = {"immediate": test_score(hidden, held), **counts,
           "tracked_mastered": sum(cs.p_mastery >= 0.85 for cs in state.concepts.values())}
    elapsed = 0
    for d in DELAYS:
        decay(hidden, d - elapsed)
        elapsed = d
        out[f"d{d}"] = test_score(hidden, held)
    return out


# --- statistics ---

def boot_ci(values: list[float], seed: int) -> dict:
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT))
    return {"mean": sum(values) / n, "ci95": [means[int(0.025 * BOOT)], means[int(0.975 * BOOT) - 1]]}


def summarize(rows: dict[str, list[dict]], seed: int) -> dict:
    arms = {}
    for arm, rs in rows.items():
        m = {"immediate": boot_ci([r["immediate"] for r in rs], seed)}
        for d in DELAYS:
            m[f"retention_d{d}"] = boot_ci([r[f"d{d}"] for r in rs], seed + d)
            m[f"drop_d{d}"] = boot_ci([r["immediate"] - r[f"d{d}"] for r in rs], seed + 100 + d)
        m["mean_counts"] = {k: sum(r[k] for r in rs) / len(rs)
                            for k in ("questions", "lessons", "reviews", "fallbacks", "targeted", "tracked_mastered")}
        arms[arm] = m
    paired = {}
    for a, b in (("adaptive", "static"), ("adaptive", "adaptive_no_review")):
        p = {}
        for key in ("immediate", *(f"d{d}" for d in DELAYS)):
            p[key] = boot_ci([x[key] - y[key] for x, y in zip(rows[a], rows[b])], seed + 7 + len(key))
        paired[f"{a}_minus_{b}"] = p
    return {"arms": arms, "paired": paired}


def fmt(m: dict, pct: bool = True) -> str:
    k = 100 if pct else 1
    return f"{m['mean'] * k:5.1f} [{m['ci95'][0] * k:5.1f}, {m['ci95'][1] * k:5.1f}]"


def main() -> int:
    audit = {"fingerprints": {}, "held_out_served": 0}
    results = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "description": "Offline simulation: does adaptive teaching with scheduled reviews improve mastery and retention?",
        "config": {"learners_per_arm_per_bundle": LEARNERS, "sessions": SESSIONS, "questions_per_session": PER_SESSION,
                   "delays_days": list(DELAYS), "bootstrap_resamples": BOOT, "seed": SEED,
                   "arms": {"static": "fixed concept order, untargeted lessons, no reviews, no placement",
                            "adaptive_no_review": "adaptive policy with diagnostic placement and targeted lessons, no reviews",
                            "adaptive": "adaptive policy with placement, targeted lessons and scheduled reviews"},
                   "score": "held-out test: mean probability of a right answer over questions never used in training "
                            "(the last transfer and last diagnostic question of each concept)"},
        "assumptions": [
            "Not knowing a concept, a learner picks an option tagged with a misconception they hold 70% of the time, else guesses.",
            "A lesson raises hidden knowledge by pace*(1-k); a lesson targeting a held misconception removes it.",
            "Each answered question raises hidden knowledge by 0.2*pace*(1-k).",
            "Knowledge decays toward the prior with exp(-forgetting*days/stability); practising a concept again after "
            ">= 1 day multiplies its stability by 1.8 (right) or 1.2 (wrong).",
        ],
        "limits": LIMITS,
        "bundles": {},
    }
    signature_ok = list(inspect.signature(answer).parameters) == ["hidden", "q", "rng"] and \
        list(inspect.signature(p_correct).parameters) == ["hidden", "q"] and \
        not any(f.type in ("LearnerState", LearnerState) for f in Hidden.__dataclass_fields__.values())

    lines = []
    for b_i, name in enumerate(BUNDLES):
        bundle = CourseBundle.model_validate(json.loads((ROOT / "fixtures" / f"{name}.json").read_text(encoding="utf-8")))
        pool, held, diag = split(bundle)
        rows = {arm: [] for arm in ARMS}
        for i in range(LEARNERS):
            seed = SEED + 1000 * b_i + i
            for arm in ARMS:
                rows[arm].append(run_arm(arm, bundle, seed, pool, held, diag, audit))
        summary = summarize(rows, SEED + b_i)
        summary["held_out_questions"] = len(held)
        summary["training_pool_questions"] = sum(len(v) for v in pool.values())
        results["bundles"][name] = summary

        lines += [f"\n### {name} ({LEARNERS} learners per arm; held-out test: {len(held)} questions)\n",
                  "| Arm | Immediate | +7 days | +30 days | Drop at +7 | Drop at +30 | Lessons | Reviews |",
                  "|---|---|---|---|---|---|---|---|"]
        for arm, m in summary["arms"].items():
            c = m["mean_counts"]
            lines.append(f"| {arm} | {fmt(m['immediate'])} | {fmt(m['retention_d7'])} | {fmt(m['retention_d30'])} | "
                         f"{fmt(m['drop_d7'])} | {fmt(m['drop_d30'])} | {c['lessons']:.1f} | {c['reviews']:.1f} |")
        lines += ["", "| Paired difference | Immediate | +7 days | +30 days |", "|---|---|---|---|"]
        for k, p in summary["paired"].items():
            lines.append(f"| {k.replace('_minus_', ' minus ')} | {fmt(p['immediate'])} | {fmt(p['d7'])} | {fmt(p['d30'])} |")

    identical = all(len(fps) == 1 for fps in audit["fingerprints"].values())
    invariants = {
        "answers_read_only_hidden_state": "PASS" if signature_ok else "FAIL",
        "hidden_profile_identical_across_arms": "PASS" if identical else "FAIL",
        "no_held_out_question_served_in_training": "PASS" if audit["held_out_served"] == 0 else
        f"FAIL ({audit['held_out_served']} served)",
    }
    results["invariants"] = invariants

    verdicts = []
    for name, s in results["bundles"].items():
        for d in DELAYS:
            p = s["paired"]["adaptive_minus_static"][f"d{d}"]
            lo, hi = p["ci95"]
            word = "beats" if lo > 0 else "does NOT beat" if hi < 0 or p["mean"] <= 0 else "is not clearly better than"
            verdicts.append(f"{name}: adaptive {word} static on retention at +{d} days "
                            f"({p['mean'] * 100:+.1f} points, 95% CI [{lo * 100:+.1f}, {hi * 100:+.1f}]).")
    results["verdicts"] = verdicts

    head = ["# OnlyNerd offline evaluation", "",
            f"Generated {results['generated_at']}. Scores are % chance of a right answer on held-out questions "
            "(mean [95% bootstrap CI]); drops and differences are in percentage points.", ""]
    body = head + lines + ["", "## Verdicts", ""] + [f"- {v}" for v in verdicts] + \
        ["", "## Invariants", ""] + [f"- {k}: {v}" for k, v in invariants.items()] + \
        ["", "## Assumptions", ""] + [f"- {a}" for a in results["assumptions"]] + \
        ["", "## Limits", ""] + [f"- {x}" for x in LIMITS]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (RESULTS / "eval.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    print("\n".join(body))
    return 0 if all(v == "PASS" for v in invariants.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
