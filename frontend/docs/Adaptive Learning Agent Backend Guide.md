# Adaptive Learning Agent: Backend Guide

Stack: FastAPI, uv, Pydantic, MongoDB (PyMongo async), LangGraph/LangChain. Solo, about 24 hours.

## Part 1: How the system works

### The three parts

- **The writer (LLM)** creates content: the concept list, quiz questions, explanations and practice sets. It never decides anything about the learner.
- **The brain (plain Python)** keeps score of what the learner knows and decides what happens next. It is deterministic, so it can be tested and explained.
- **The memory (MongoDB)** stores courses, questions, answers and every learner's state.

### What the brain works with

1. **Concepts** are the small ideas that make up a topic, with prerequisites ("loops" needs "variables").
2. **Tagged questions.** Every question belongs to one concept, and every wrong option is tagged with the misconception it represents. Picking that option is evidence of that specific misunderstanding.
3. **Mastery (BKT, Bayesian Knowledge Tracing)** is a probability per concept of how likely the learner knows it. Every answer nudges it up or down. Mastered means 0.85 or higher at the moment of the answer. BKT has no forgetting, so the scheduler forgetting curve discounts mastery as time passes.
4. **Misconceptions.** If the same wrong-option tag shows up twice for a concept, it is confirmed, and the next lesson targets it directly.
5. **The policy** is one function that looks at the learner's state and picks the next step: review something that is due, teach the weakest unlocked concept, fall back to a prerequisite after 3 failed rounds, or finish.
6. **Revision.** When a concept is mastered, the scheduler gives it a review date based on its stability (the days until the chance of recalling it drops to 90%). A correct review pushes the next one further out. A lapse halves stability and brings it back sooner.
7. **Evaluation.** Simulated learners with hidden knowledge go through a static course and the adaptive one. A simulated clock runs 7 and 30 days, with review sessions inside the gap for the arm that has scheduling, then tests with both ordinary and transfer questions measure what stuck. A third arm with review switched off isolates what the scheduler adds.

### One cycle

The learner answers, the brain updates mastery and misconceptions, the policy picks the next step, the writer generates content for that step, and the loop repeats.

### The decisions, as rules (deterministic code)

| Decision | Rule |
| --- | --- |
| What to teach next | The unmastered concept whose prerequisites are all mastered, lowest mastery first |
| How to teach it | If a misconception is confirmed, target it with a contrasting explanation. If the learner failed last time, use a style not yet tried |
| What to practice | Questions on the weak concept, with difficulty matched to mastery, including options that map to the confirmed misconception |
| When to revisit | The scheduler sets the due date from stability |

### The live demo learner (local LLM)

For the demo, a local model plays a student on screen while the agent teaches it. The same simulator also powers the evaluation harness, so you build it once and use it twice.

The key design rule: **code decides, the LLM narrates.**

- Each simulated student has a hidden profile: concepts it knows, misconceptions it holds, and a forgetting rate.
- For each MCQ, code picks the answer from that profile. If the student knows the concept, it answers correctly (with a small slip chance). If it holds a misconception that one of the options is tagged with, it picks that option. Otherwise it guesses.
- The local model is then told which option was chosen and writes one or two sentences of reasoning in the voice of that student.

Why not let the model choose the answer itself? A capable model tends to answer correctly even when told to play a confused student, so the hidden misconception would leak away and the demo would stop being reproducible. Letting code pick the answer and the LLM explain it gives you the visible "thinking" that looks good, with reliable behaviour.

On screen, show the student's thought bubble, the agent's diagnosis, and the mastery map updating live. At the end, reveal the planted misconceptions next to what the agent found.

Be honest about what this shows. The simulated student's misconceptions are planted by your own code, so the demo illustrates the mechanism but is not evidence that it works. The evidence is the evaluation and, ideally, real people. So add a second mode, **judge as learner**: a judge answers the diagnostic live on the same screen, and the agent builds their misconception map in front of them. It is the same UI with human input instead of the simulator, it costs almost nothing, and it cannot be called a puppet show.

Risks and mitigations:

- **Slow or failed local generation.** Use a short timeout and fall back to a template sentence so the demo never stalls.
- **Heat.** A fanless laptop throttles under sustained load. Keep the local model small (8-9B) and plug in.
- **Live non-determinism.** Seed the random choices per persona so a run is repeatable, and record a backup video.
- **Fairness.** The student model should be weaker than the tutor model, never the same one.

## Part 2: Steps to finish the backend

Each step ends with a "done when" check so you know it is finished before moving on.

### Step 0: Setup and reuse (about 1h)

- Fix `pyproject.toml`: `uv add fastapi uvicorn pymongo pydantic-settings langgraph langchain-openai httpx`.
- Copy `config.py`, the DB connection, and logging from your autodidact repo, and stub one demo user instead of porting auth, refresh tokens and TTL indexes. Make the Tavily, YouTube and Google settings optional.
- Rewrite `structured_completion` as async, with separate retries for 429 errors and for JSON validation. Put model names in env vars (`MODEL_STRONG`, `MODEL_CHEAP`, `MODEL_LOCAL`).
- Done when: the server boots from a clean `.env`.

### Step 1: Schemas (about 0.5h)

- `Concept`, `ConceptGraph`, `Question` (with `concept_id`, `distractor_tags`, `explanation`, `difficulty`, `kind`), `Attempt`, `ConceptState, LearnerState`, `Misconception`, `Roadmap`, `LearnerProfile`.
- Done when: you can build a sample of each from a dict and validate it.

### Step 2: The brain, with no LLM and no database (about 2.5h)

- `clock.py`: an injectable `now()` that tests and the simulator can advance.
- `bkt.py`: the update function, with unit tests (with p\_guess 0.25, one correct answer takes 0.20 to 0.553, two reach 0.844 and the third passes 0.85; one correct then one wrong gives 0.27).
- `scheduler.py`: stability is the days until recall drops to 90% (1 day at first mastery), a success multiplies it by 1 + 1.5 x score, a lapse halves it and resets mastery to 0.5, retrievability is 0.9 to the power of days since review divided by stability, the policy ranks concepts by mastery x retrievability, `due_at = last_review + stability`.
- `policy.py`: `next_step(learner)` and `record_misconceptions(state, graded)`.
- Done when: a pytest script runs a fake learner through 10 answers and the steps and review dates match what you expect by hand.

### Step 3: Storage (about 0.5h)

- Collections: `questions`, `attempts`, `learner_states`, `misconceptions`, `events`. Indexes on `(learner_id, concept_id)` and `due_at`.
- Small repository functions: `get_state`, `save_state`, `log_event`.
- Done when: you can save and reload a learner's state from a script.

### Step 4: Content generation (about 3h, the riskiest step)

- LLM functions that return validated schemas: `generate_concept_graph`, `generate_diagnostic`, `generate_explanation`, `generate_practice`, `generate_transfer_variant`.
- Extra validators beyond the schema: the graph is acyclic, the correct index is in range, every distractor carries a tag.
- Cache generated courses by prompt so reruns do not burn calls, and keep one shared question bank for every evaluation learner. Add a blind-solver check: a cheap model answers each question without the key, and a question is dropped when it disagrees with the key or never picks the tagged distractor.
- Done when: 20 generation runs on one topic give valid output at least 90% of the time and the tags make sense on a spot check.

### Step 5: API endpoints (about 2.5h)

- `POST /courses`: returns `generating` and builds the concept graph and diagnostic in a background task.
- `POST /courses/{id}/diagnostic/submit`: grades, runs BKT, records misconceptions, builds the roadmap.
- `GET /courses/{id}/next`: calls `next_step`, then generates the lesson and practice for it.
- `POST /courses/{id}/attempts`: runs `engine.submit_answers` and returns feedback plus the next step.
- `GET /courses/{id}/reviews/due`, `GET /courses/{id}/mastery`, and a dev-only `POST /dev/clock/advance`.
- Strip answers from responses, as your existing code does.
- Done when: you can complete a diagnostic, two lessons and a review using only Swagger or Bruno.

### Step 6: Event log and stop rules (about 0.5h, built into the engine)

- Log every answer, lesson and review as an event.
- Enforce the caps: 3 rounds per concept, then the prerequisite fallback, plus a session limit.
- Done when: the loop always terminates, even for a learner who gets everything wrong.

### Step 7: Simulator and evaluation harness (about 4h)

- `simulator.py`: hidden profile plus the deterministic MCQ answering rule from Part 1. Its forgetting curve must have a different shape from the scheduler (the scheduler is exponential, so use a power law with a different rate per learner), or the evaluation grades itself. A lesson that targets a held misconception clears it with probability p\_clear, and an untargeted lesson with a lower probability; both are swept parameters, not facts. The local model is used only for narration and for any short-answer questions.
- Three arms, all required: static (fixed order, no adaptation, no reviews), adaptive without review, and adaptive with review. The gap between the last two isolates the scheduler. Same code, with the adaptive rules switched off for the static arm.
- Runner: pre-test, course, immediate post-test, then 7 and 30 days with review sessions at days 2 and 5 (and 14 for the 30-day horizon) for the arm that has them, and a delayed test at each horizon. Every test mixes ordinary and transfer questions, so forgetting is not confused with question difficulty. Skip lesson generation during evaluation runs, since the simulator ignores lesson text.
- Metrics: learning gain, delayed score and score drop (immediate minus delayed, never a ratio, which breaks when the immediate score is low), misconception resolution, diagnosis accuracy, results at matched interaction budgets, and mastery calibration (does the agent mastery estimate predict the delayed result better than raw quiz percent?).
- `POST /evaluation/run` and `GET /evaluation/results/{run_id}`.
- Done when: at least 30 paired learners (the same profile through every arm) produce means with bootstrap 95% confidence intervals, a parameter sweep over forgetting rate and p\_clear, and a results table that includes the cases where adaptive does not help. Report whatever comes out.

### Step 8: Live demo mode (about 1.5h)

- `POST /demo/start` takes a persona and a topic, and creates either a simulated student or a human session (judge as learner) bound to a real course. In human mode the answers come from the browser instead of the simulator, and the same events drive the same live mastery map.
- `GET /demo/stream` sends Server-Sent Events: `question_shown`, `learner_thought`, `learner_answer`, `diagnosis`, `mastery_update`, `next_step`.
- Controls: autopilot with a speed setting, a manual "next" button, and a "skip 7 days" button that advances the clock so the review appears.
- Local model call: structured output `{"thought": str}`, a short timeout, and a template fallback.
- A `reveal` event at the end listing the planted misconceptions and what the agent found.
- Done when: a full demo runs end to end offline from one seeded course and one persona.

### Step 9: Hardening and seed data (about 0.5h)

- Rate-limit backoff, a retry cap on generation, and clear error responses.
- A seed script that creates one pre-generated course and two personas, so the live demo never waits on slow generation.
- Done when: a full run works from a fresh database with one command.

### If time runs short

Build in this order: steps 0, 1, 2, 4, 5, then 7, then 8, then 3, 6 and 9. Steps 2 and 7 are the core of what you are judged on, and step 8 is what makes the demo memorable.

LangGraph is not a step. Add it after step 5 only if lesson generation becomes messy as plain functions.

## Evaluation design: what a skeptical judge will challenge

The first evaluation design graded itself in several places. The build steps above now assume the fixes below.

| Problem | Fix |
| --- | --- |
| Circular: the simulator and the agent share the same assumptions, so adaptive wins by construction | The simulator forgets on a power law with a different rate per learner while the scheduler assumes an exponential. Sweep forgetting rate and p\_clear, and report the settings where adaptive does not help |
| No review happens in the gap, so scheduling cannot change the delayed test | Review sessions at days 2 and 5 (and 14 for the 30-day horizon) for the arms that have them. A mandatory no-review arm isolates the scheduler |
| Explanation quality is never tested, because the simulator ignores lesson text | State it as a limit. The only lesson effect is the p\_clear assumption, which is swept. Log whether the next attempt improved, but do not build style selection |
| The retention ratio mixes forgetting with question type and breaks at low scores | Both question types on every test. Report delayed score and score drop, and compare at matched interaction budgets |
| Ten learners, and a success criterion chosen in advance | 30+ paired profiles, bootstrap 95% confidence intervals, report whatever comes out |
| Diagnosis is scored against your own LLM-written catalog | Blind-solver filter on questions. Say plainly that a closed catalog cannot find unanticipated misconceptions. Add a few short-answer items if time allows |
| The demo is a puppet show | Call it an illustration, add judge-as-learner mode, and run a small human pilot |

### Protocol

1. Generate one course and one shared question bank (ordinary and transfer questions, blind-solver filtered).
2. Sample 30+ seeded learner profiles. Each profile runs through all three arms: static, adaptive without review, adaptive with review.
3. Pre-test, course, immediate post-test.
4. For the gap, the arm with review answers scheduled review sessions, and the simulator applies its own forgetting between sessions.
5. Delayed tests at day 7 and day 30. Every test has the same mix of ordinary and transfer questions.
6. Report means with bootstrap confidence intervals, the parameter sweep, and the cases where adaptive does not win.

### Forgetting model, defined

- Stability S is the number of days until the chance of recall drops to 90%. It starts at 1 day on first mastery.
- In the agent, retrievability after t days is 0.9 to the power of t divided by S. A review is due when it reaches 0.9, which is t = S.
- A correct review multiplies S by 1 + 1.5 x score. A lapse halves S and resets mastery to 0.5.
- The policy ranks concepts by mastery x retrievability, so a mastered concept that has faded is not treated as known.
- The simulator uses a different curve: recall = 1 / (1 + t / (9 x s)), with a different s per learner. It also gives 90% at t = s, but its shape is a power law.

### Using confidence

- A wrong answer given with high confidence adds 2 to misconception evidence instead of 1. This separates a misconception from a slip.
- A correct answer given with low confidence is treated as a likely guess: use p\_guess 0.5 for that update.
- Pace and time spent were dropped from the schemas because nothing used them.

### The headline chart: calibration

For each learner and concept, compare the agent mastery estimate at the immediate test with whether the learner is correct at the delayed test. Plot it against the raw immediate quiz percent as a predictor, and report AUC or Brier score. If the estimate predicts delayed performance better than quiz percent, you have shown directly that short-term quiz scores mislead, which is the point of the brief.

### What the evaluation can and cannot claim

- It measures sequencing, misconception targeting and review scheduling, under assumptions that are swept parameters rather than facts.
- It does not measure explanation quality, because the simulator ignores lesson text.
- Diagnosis accuracy is scored against your own catalog, so it shows the agent can find tags that were planted, not that it finds real misconceptions.
- Real people are stronger evidence than any simulation. Aim for 5 volunteers on the judge-as-learner path, and label the result a pilot, not a significance test.

### Revised time budget

| Item | Hours |
| --- | --- |
| Step 0 Setup and reuse (stub the user) | 1 |
| Step 1 Schemas | 0.5 |
| Step 2 The brain | 2.5 |
| Step 3 Storage | 0.5 |
| Step 4 Content generation (cached bank, blind solver) | 3 |
| Step 5 API endpoints | 2.5 |
| Step 6 Stop rules (inside the engine) | 0.5 |
| Step 7 Simulator and evaluation | 4 |
| Step 8 Live demo and judge mode | 1.5 |
| Step 9 Hardening and seed data | 0.5 |
| Backend subtotal | 16.5 |
| Frontend | 3.5 |
| README and pitch | 2 |
| Buffer | 2 |
| Total | 24 |

### Cut list

- Cut: auth, refresh tokens, TTL indexes, Google OAuth. Stub one demo user.
- Cut: the Tavily and YouTube research agent from the core loop.
- Cut: a bandit over explanation styles. Log the outcome, do not build the selection.
- Cut: LangGraph, unless lesson generation becomes messy as plain functions.

## Part 3: Reference (modules, routes, data structures)

Use this part as a checklist while coding. Part 2 says in what order to build; this part says what each piece is called and what it contains.

### Folder layout

```
backend/
  main.py
  config.py
  db/            connection.py, repos.py
  auth/          (ported from autodidact: signup, login, refresh, me)
  schemas/       content.py, learner.py, api.py, evaluation.py, demo.py
  core/          clock.py, bkt.py, scheduler.py, policy.py, engine.py
  generation/    llm.py, prompts.py, validators.py, course_gen.py
  routers/       courses.py, learning.py, reviews.py, evaluation.py, demo.py, dev.py
  sim/           persona.py, simulator.py, narrator.py
  evaluation/    arms.py, runner.py, metrics.py
  scripts/       seed.py
  tests/
```

One dependency rule keeps this testable: **`core/` is pure Python.** It imports only from `schemas/`, never from `db/`, `generation/` or the LLM. That way the whole brain can be unit tested and reused by the API, the simulator and the evaluation harness without a database or network.

### The parts (modules)

| Module | Job | Uses LLM | Uses DB |
| --- | --- | --- | --- |
| `core/clock.py` | Injectable `now()` and `advance(days)`. Everything time-based reads this, never `datetime.now()` | No | No |
| `core/bkt.py` | `bkt_update(p, correct, params)` returns the new mastery probability | No | No |
| `core/scheduler.py` | `schedule_after_mastery`, `update_after_review(success)`, `due_items(state, now)` | No | No |
| `core/policy.py` | `next_step(state, graph, config)` picks review, lesson, fallback or done. `record_misconceptions(...)` | No | No |
| `core/engine.py` | The single entry point: `get_next(...)` and `submit_answers(...)`. Combines bkt, scheduler and policy. Takes a `PolicyConfig` so the static baseline is the same code with adaptation off | No | No |
| `generation/llm.py` | Async `structured_completion` with separate 429 and validation retries, model chosen by role | Yes | No |
| `generation/course_gen.py` | `generate_concept_graph`, `generate_misconception_catalog`, `generate_diagnostic`, `generate_lesson`, `generate_practice`, `generate_transfer_variant` | Yes | No |
| `generation/validators.py` | Checks the schema cannot: graph is acyclic, prerequisites exist, correct index in range, every distractor tagged, tags come from the catalog | No | No |
| `db/repos.py` | `CourseRepo`, `QuestionRepo`, `StateRepo`, `AttemptRepo`, `EventRepo` | No | Yes |
| `sim/persona.py` | Builds hidden learner profiles (`SimProfile`) with a seed | No | No |
| `sim/simulator.py` | Picks an MCQ answer from the hidden profile and applies forgetting when the clock advances | No | No |
| `sim/narrator.py` | Asks the local model for one or two sentences of student-voice reasoning, with timeout and template fallback | Local | No |
| `evaluation/arms.py` | `PolicyConfig` presets: `static` and `adaptive` (plus the required `no_review`) | No | No |
| `evaluation/runner.py` | Pre-test, course, immediate post-test, advance 7 days, delayed transfer test | Via generation | Yes |
| `evaluation/metrics.py` | Learning gain, retention, misconception resolution, diagnosis precision and recall | No | No |

The engine is the important design choice. The API, the evaluation runner and the live demo all call the same `engine.submit_answers(...)`. If all three share it, whatever you show in the demo is exactly what you measured in the evaluation.

### Routes

All routes except `/auth/signup`, `/auth/login` and `/dev/*` need a bearer token, unless you stub a single demo user and skip auth entirely, which is what I would do in 24 hours.

| Method | Path | Request | Response | Calls |
| --- | --- | --- | --- | --- |
| POST | `/auth/signup` | `SignupIn` | `TokenPair` | auth (ported) |
| POST | `/auth/login` | `LoginIn` | `TokenPair` | auth (ported) |
| POST | `/auth/refresh` | `RefreshIn` | `TokenPair` | auth (ported) |
| GET | `/auth/me` | none | `UserPublic` | auth (ported) |
| POST | `/courses` | `CreateCourseIn` (prompt) | `CreateCourseOut` (status generating) | `course_gen` in a background task |
| GET | `/courses/{id}` | none | `CourseOverviewOut` (concepts, roadmap, status) | `CourseRepo` |
| GET | `/courses/{id}/diagnostic` | none | `DiagnosticOut` (public questions, no answers) | `QuestionRepo` |
| POST | `/courses/{id}/diagnostic/submit` | `SubmitAnswersIn` | `DiagnosticResultOut` (mastery map, misconceptions, roadmap) | `engine.submit_answers`, then roadmap generation |
| GET | `/courses/{id}/next` | none | `StepOut` (lesson plus practice, review, or done) | `engine.get_next`, then `generate_lesson` |
| POST | `/courses/{id}/attempts` | `SubmitAnswersIn` | `AttemptResultOut` (feedback, updated mastery, next step) | `engine.submit_answers` |
| GET | `/courses/{id}/reviews/due` | none | `DueReviewsOut` | `scheduler.due_items` |
| GET | `/courses/{id}/mastery` | none | `MasteryOut` (per concept, misconceptions, next due) | `StateRepo` |
| POST | `/evaluation/run` | `RunEvalIn` (topic, n, arms) | `EvalRunOut` (run id) | `evaluation.runner` in a background task |
| GET | `/evaluation/results/{run_id}` | none | `EvalResultsOut` | `metrics` |
| POST | `/demo/start` | `DemoStartIn` (persona, course) | `DemoSessionOut` | `sim.persona`, engine |
| GET | `/demo/{session}/stream` | none | Server-Sent Events of `DemoEvent` | simulator, narrator, engine |
| POST | `/demo/{session}/control` | `DemoControlIn` (play, pause, step, speed) | `DemoSessionOut` | demo session |
| POST | `/demo/{session}/skip-days` | `SkipDaysIn` | `DemoSessionOut` | `clock.advance` |
| POST | `/dev/clock/advance` | `SkipDaysIn` | `ClockOut` | `clock` (dev only) |
| GET | `/health` | none | `{status}` | none |

Route ordering reminder from your autodidact notes: register fixed-prefix routes before any `/{id}` route, or the id route swallows them.

### What happens inside `POST /courses/{id}/attempts`

1. Load the `LearnerState` and the questions for the submitted ids.
2. Grade each answer by index lookup: correct or not, and which misconception tag the chosen option carries.
3. `engine.submit_answers` runs BKT per concept, updates misconception evidence, applies mastery or lapse scheduling, and increments `failed_rounds` when needed.
4. Save the new state and write one `events` document per answer.
5. Ask the policy for the next step and return it with the feedback.

No LLM is called in steps 1 to 5. The LLM runs later, on `GET /next`, only to write the content for the step the policy chose.

### Pydantic structures

#### Content (generated by the LLM, validated by code)

```python
class Concept(BaseModel):
    id: str
    name: str
    description: str
    prerequisites: list[str] = []

class MisconceptionDef(BaseModel):
    tag: str                      # stable id, e.g. 'loop_off_by_one'
    concept_id: str
    description: str

class ConceptGraph(BaseModel):
    topic: str
    concepts: list[Concept]       # validator: acyclic, prerequisites exist
    misconceptions: list[MisconceptionDef]

class Option(BaseModel):
    text: str
    misconception_tag: str | None = None   # None only on the correct option

class Question(BaseModel):
    id: str
    course_id: str
    concept_id: str
    kind: Literal['diagnostic', 'practice', 'review', 'transfer']
    prompt: str
    options: list[Option]         # validator: exactly 4
    correct_index: int            # validator: in range, that option has no tag
    explanation: str
    difficulty: float = Field(ge=0, le=1)
    variant_of: str | None = None # set on transfer questions

class Lesson(BaseModel):
    concept_id: str
    style: str                    # e.g. 'analogy', 'worked_example', 'contrast'
    explanation: str
    targets: list[str] = []       # misconception tags addressed
```

Generate the misconception catalog first, then ask for questions that may only use tags from that catalog. That keeps tags consistent across questions, which BKT and misconception counting depend on.

#### Learner state (stored in MongoDB, owned by `core/`)

```python
class ConceptState(BaseModel):
    concept_id: str
    p_mastery: float = 0.2
    attempts: int = 0
    failed_rounds: int = 0
    stability_days: float = 0.0
    last_reviewed_at: datetime | None = None
    due_at: datetime | None = None
    lapses: int = 0
    explanations_tried: list[str] = []

class MisconceptionState(BaseModel):
    tag: str
    concept_id: str
    status: Literal['suspected', 'confirmed', 'resolved'] = 'suspected'
    evidence: float = 0.0             # +1 per tagged pick, +2 if high confidence; confirmed at 2
    clean_streak: int = 0         # resolved after 2 correct answers on targeted questions

class LearnerState(BaseModel):
    learner_id: str
    course_id: str
    concepts: dict[str, ConceptState]
    misconceptions: dict[str, MisconceptionState]
    roadmap: list[str]            # ordered concept ids
    session_questions: int = 0

class BktParams(BaseModel):
    p_init: float = 0.2
    p_learn: float = 0.15
    p_slip: float = 0.1
    p_guess: float = 0.25         # 4-option MCQ
    mastery_threshold: float = 0.85
```

#### Engine and policy

```python
class PolicyConfig(BaseModel):
    adaptive: bool = True               # False = static baseline
    target_misconceptions: bool = True
    spaced_review: bool = True
    max_rounds_per_concept: int = 3
    max_questions_per_session: int = 15

class Step(BaseModel):
    kind: Literal['lesson', 'review', 'fallback', 'done']
    concept_id: str | None = None
    target_misconceptions: list[str] = []
    avoid_styles: list[str] = []
    difficulty: float | None = None

class AnswerIn(BaseModel):
    question_id: str
    chosen_index: int
    confidence: Literal['low', 'medium', 'high'] | None = None
    # time_ms dropped: nothing uses it

class AnswerGraded(BaseModel):
    question_id: str
    concept_id: str
    correct: bool
    chosen_tag: str | None
    confidence: str | None

class LearnerProfile(BaseModel):    # the JSON handed to the LLM, instead of a prose prompt
    mastery: dict[str, float]
    confirmed_misconceptions: list[MisconceptionDef]
    avoid_styles: dict[str, list[str]]
    # pace dropped: nothing uses it
```

#### API request and response models

```python
class CreateCourseIn(BaseModel):
    prompt: str

class SubmitAnswersIn(BaseModel):
    answers: list[AnswerIn]

class QuestionPublic(BaseModel):    # never includes correct_index or tags
    id: str
    concept_id: str
    prompt: str
    options: list[str]

class StepOut(BaseModel):
    step: Step
    lesson: Lesson | None = None
    questions: list[QuestionPublic] = []

class AttemptResultOut(BaseModel):
    graded: list[AnswerGraded]
    explanations: dict[str, str]    # question_id -> explanation, revealed after answering
    mastery: dict[str, float]
    new_confirmed_misconceptions: list[str]
    next_step: Step

class MasteryOut(BaseModel):
    concepts: list[ConceptState]
    misconceptions: list[MisconceptionState]
    next_due: datetime | None
```

#### Evaluation and simulation

```python
class SimProfile(BaseModel):        # hidden from the agent
    id: str
    seed: int
    knows: list[str]                # concept ids known at the start
    misconceptions: dict[str, str]  # concept_id -> planted tag
    learn_rate: float = 0.15
    forget_rate: float = 0.08       # per day, power-law curve (not the scheduler exponential); add p_clear_targeted and p_clear_untargeted
    slip: float = 0.1
    guess: float = 0.25

class ArmResult(BaseModel):
    arm: Literal['static', 'adaptive', 'no_review']
    profile_id: str
    pre: float
    immediate_post: float
    delayed_post: dict[int, float]             # horizon in days to score, e.g. 7 and 30; tests mix ordinary and transfer questions
    interactions: int
    planted: list[str]
    detected: list[str]
    resolved: list[str]

class EvalMetrics(BaseModel):
    arm: str
    n: int
    learning_gain: float            # (post - pre) / (1 - pre)
    score_drop: float                # immediate minus delayed, never a ratio
    misconception_resolution: float
    diagnosis_precision: float
    diagnosis_recall: float
    mean_interactions: float        # also report at matched budgets

class EvalRunOut(BaseModel):
    run_id: str
    status: Literal['running', 'done', 'failed']
```

#### Live demo

```python
class DemoEvent(BaseModel):
    type: Literal[
        'question_shown', 'learner_thought', 'learner_answer',
        'diagnosis', 'mastery_update', 'next_step',
        'clock_advanced', 'review_due', 'reveal',
    ]
    payload: dict
    ts: datetime

class DemoControlIn(BaseModel):
    action: Literal['play', 'pause', 'step']
    speed: float = 1.0

class SkipDaysIn(BaseModel):
    days: int = Field(ge=1, le=60)
```

The `reveal` event carries the planted misconceptions next to what the agent detected. That is the moment in the demo that proves the agent worked.

### MongoDB collections

| Collection | Key fields | Index |
| --- | --- | --- |
| `users`, `refresh_tokens` | as in autodidact | TTL on `expires_at` |
| `courses` | `graph`, `roadmap`, `status`, `topic`, `user_id` | `user_id`, TTL on `failed_at` |
| `questions` | `Question` fields | `(course_id, concept_id, kind)` |
| `learner_states` | `LearnerState` | unique `(learner_id, course_id)` |
| `attempts` | graded answers with timestamp | `(learner_id, concept_id)` |
| `lessons` | generated `Lesson` plus whether the next attempt improved | `(learner_id, concept_id)` |
| `events` | append-only log used by evaluation and the demo | `(run_id, ts)` |
| `eval_runs` | config, status, `ArmResult` list, `EvalMetrics` | `run_id` |

### Mapping to the build steps

| Part 2 step | Files you create |
| --- | --- |
| 0 Setup | `config.py`, `db/connection.py`, `auth/`, `generation/llm.py` |
| 1 Schemas | everything in `schemas/` |
| 2 The brain | `core/clock.py`, `bkt.py`, `scheduler.py`, `policy.py`, `engine.py`, plus tests |
| 3 Storage | `db/repos.py` |
| 4 Content generation | `generation/prompts.py`, `validators.py`, `course_gen.py` |
| 5 API | `routers/courses.py`, `learning.py`, `reviews.py` |
| 6 Stop rules | limits inside `policy.py` and `engine.py` |
| 7 Evaluation | `sim/persona.py`, `simulator.py`, `evaluation/*`, `routers/evaluation.py` |
| 8 Live demo | `sim/narrator.py`, `routers/demo.py` |
| 9 Hardening | `scripts/seed.py`, error handlers in `main.py` |
