# OnlyNerd API reference

Generated 2026-10-30 23:12 from a live run (commit `11b8da9`, with uncommitted changes). Every field, status code and example below was captured from the running server. Routes documented: 11.

## Contents

1. Overview
2. Learner flow
3. Screen-to-endpoint map
4. Endpoints
5. Behaviour the frontend must know
6. Enumerations
7. Planned, not implemented yet
8. Quick start
9. Changelog / how to regenerate
10. Quirks and open questions

## 1. Overview

- Base URL: `http://127.0.0.1:8000` locally. All paths below are relative to it.
- Run the backend: start MongoDB on `mongodb://localhost:27017`, then in `backend/`: `uv run uvicorn main:app --port 8000`. Settings come from `backend/.env` (`MONGO_URI`, `MONGO_DB`, `MASTER_PASSWORD`, `ANTHROPIC_API_KEY`).
- CORS: the server allows the origin `http://localhost:3000` only, any method, and the request headers `Content-Type` and `X-Master-Password`.
- Auth: send `X-Master-Password: <your-master-password>` on every request except `GET /health`. A missing or wrong value returns **401** with `{"detail": "missing or wrong master password"}`. If the server's `MASTER_PASSWORD` is empty, nothing is checked (dev mode).
- Errors are JSON with a `detail` field. Errors raised by the API carry a string; request-body validation errors (422 from FastAPI) carry a list of `{type, loc, msg, input, ...}` objects. Real bodies from this run:

**401** (`POST /courses`):
```json
{
  "detail": "missing or wrong master password"
}
```

**404** (`GET /courses/no-such-course`):
```json
{
  "detail": "course 'no-such-course' not found"
}
```

**409** (`POST /courses/b0dafa63/learners/docs-231157/start`):
```json
{
  "detail": "learner 'docs-231157' already started course 'b0dafa63'"
}
```

**422** (`POST /courses/b0dafa63/learners/docs-231157/attempts`):
```json
{
  "detail": "questions not served to this learner: ['f707cec4-language_model_basics-d2']"
}
```

**422** (`POST /courses`):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "prompt"
      ],
      "msg": "Field required",
      "input": {
        "level": "beginner"
      }
    }
  ]
}
```

### Glossary

- **Concept**: one node of the course's prerequisite graph (id, name, prerequisites).
- **Mastery** (`p_mastery`): probability the learner knows a concept, 0..1. **Mastered** means 0.85 or more.
- **Gap**: a concept not yet mastered (`gaps` in the state, roadmap order).
- **Placed**: a concept answered right in the diagnostic, set straight to 0.85 with a re-check review 1 to 3 days later depending on confidence.
- **Verified**: the API does not expose a 'verified' flag or field; a placed concept that passed its review looks like any mastered concept with stability above its placement value.
- **Retrievability**: probability of recalling a mastered concept now, `0.9^(days since review / stability)`; 1.0 for concepts never mastered.
- **Stability** (`stability_days`): how long a memory lasts; a passed review multiplies it by 2.5, a lapse halves it (minimum 1).
- **Session**: a run of up to 15 answered questions; then the next step is `session_end`.
- **Simulated clock**: each learner has `clock_offset_days`; their 'now' is real UTC now plus the offset. `POST .../advance` moves it forward for demos.

## 2. Learner flow

1. **Create course**: `POST /courses` with prompt and level.
2. **Poll until ready**: `GET /courses/{cid}` every 2 s while `status` is `generating`.
3. **Start**: `POST /courses/{cid}/learners/{lid}/start` returns the diagnostic (one question per concept).
4. **Submit the diagnostic**: `POST .../attempts`. Right answers are placed as known; the response has the grading, messages and `next` (the first lesson).
5. **Read the next step**: it is in `next` of every attempts response; `GET .../next` returns the same thing any time (after reload, advance or a new session).
6. **Practice**: show the lesson and its questions, submit them with `POST .../attempts`; repeat.
7. **Advance the clock** (control panel): `POST .../advance {days}`; then `GET .../next`.
8. **Review**: a `review` step has 2 questions on a due concept; submit them.
9. **Relearn**: a failed review is a lapse; the next step is a lesson on that concept before other reviews.
10. **Session end**: after 15 questions the step is `session_end`; call `POST .../sessions/new`, then `GET .../next`.
11. **Done**: when every reachable concept is mastered the step is `done` (come back later for reviews: advance or wait).

```text
Frontend                                   Backend
   | POST /courses {prompt, level}          |
   |--------------------------------------->|  status: generating | ready
   | GET /courses/{cid}   (every 2 s)       |
   |--------------------------------------->|  ... until ready
   | POST .../learners/{lid}/start          |
   |--------------------------------------->|  diagnostic questions
   | POST .../attempts  {answers}           |
   |--------------------------------------->|  graded + messages + next (lesson + 3 questions)
   | POST .../attempts  (practice)          |
   |--------------------------------------->|  graded + next
   | POST .../advance {days}  (control)     |
   |--------------------------------------->|  now, due_now, next_kind
   | GET .../next                           |
   |--------------------------------------->|  review + 2 questions
   | POST .../attempts  (review)            |
   |--------------------------------------->|  graded + next (relearn lesson on a lapse)
   | GET .../state  (sidebar, any time)     |
   |--------------------------------------->|  mastery, gaps, due, retrievability
```

## 3. Screen-to-endpoint map

| Screen / card | Endpoint | Fields |
|---|---|---|
| Setup: topic, level, deadline form | `POST /courses` | body `prompt`, `level`, `deadline` |
| Setup: 'building your course' spinner | `GET /courses/{cid}` | `status` |
| Setup: concept graph | `GET /courses/{cid}` | `concepts[].id/name/prerequisites` |
| Quiz: diagnostic questions | `POST .../start` | `questions[].prompt/options` |
| Quiz: practice/review questions | `next.questions` from attempts, or `GET .../next` | `questions[]` |
| Quiz: confidence picker | `POST .../attempts` | `answers[].confidence` (optional) |
| Feedback: right/wrong per question | `POST .../attempts` | `graded[].correct`, `correct_indices`, `explanations` |
| Feedback: misconception callout | `POST .../attempts` | `graded[].chosen_tag`, `new_confirmed_misconceptions` |
| Feedback: toasts | `POST .../attempts` | `messages[]` |
| Lesson: text, style badge | `next.lesson` / `GET .../next` | `lesson.explanation`, `lesson.style`, `lesson.targets` |
| Lesson: 'why this' line | same | `reason` |
| Lesson: further reading | same | `lesson.resources` (fills in once research is ready) |
| Sidebar: 'researching...' then links per gap | `GET .../resources` | `{concept_id: {status, resources}}` |
| Review: 'review due' banner | same | `step.kind == 'review'`, `step.concept_id`, `reason` |
| Stuck card | `GET .../state` | `needs_help[]`; step `give_up_after` |
| Sidebar: mastery bars | `GET .../state` | `concepts[].p_mastery` (or `mastery` from attempts) |
| Sidebar: gaps / roadmap | `GET .../state` | `gaps`, `roadmap` |
| Sidebar: memory strength | `GET .../state` | `retrievability`, `concepts[].stability_days` |
| Sidebar: upcoming reviews | `GET .../state` | `due`, `next_due` |
| Sidebar: misconceptions | `GET .../state` | `misconceptions[]` |
| Sidebar: pace, deadline | `GET .../state` | `pace`, `days_left` |
| Control panel: skip N days | `POST .../advance` | body `days`; response `now`, `due_now`, `next_kind`, `next_concept_id` |
| Control panel: new session | `POST .../sessions/new` | response `next_kind`, `next_concept_id` |
| Eval page | `GET /eval/results` | the file as-is (404 until produced) |

## 4. Endpoints

### `GET /health`

Liveness check. Needs no password.

**When to call:** On app load, to show a 'backend offline' banner.

**Request body:** none.

**Response 200:** no response model in the schema; live shape: `{ status: string }`.

**Real examples:**

_health_

`GET /health` -> **200** (47 ms), file `docs/examples/health.json`

```json
{
  "status": "ok"
}
```

**Errors:**

| Status | When | Body |
|---|---|---|

**Side effects:** none

**Latency:** 1 successful calls: median 0.047 s, max 0.047 s. No LLM call observed.

**Idempotency and polling:** Safe to poll; no state.

### `POST /courses`

Creates the course for a prompt and level, or returns the existing one for the same prompt and level (case and spacing ignored). A course that is not cached starts generating in the background and returns at once with status `generating`. Sending a deadline for an existing course updates it.

**When to call:** From the setup screen, once.

**Path parameters:** `x-master-password` (strings; `lid` is any id the client picks).

**Request body** (`CreateCourseIn`):

| Field | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `prompt` | `string` | yes | - | What the learner wants to learn, free text. Case and extra spaces do not matter for reuse. |
| `level` | `"novice" | "beginner" | "intermediate" | "advanced"` | no | `novice`, `beginner`, `intermediate`, `advanced` (default `beginner`) | Self-assessed level from a dropdown. |
| `deadline` | `string | null` | no | - | Optional target date (naive UTC ISO). Drives `days_left` and the deadline message. |

Real request body:
```json
{
  "prompt": "prompt engineering",
  "level": "beginner"
}
```

**Response 200** (`CreateCourseOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `course_id` | `string` | Id to use in every learner URL. | - |
| `status` | `string` | `generating`, `ready` or `failed`. | - |
| `topic` | `string` | Topic name for headings. While generating it is the prompt. | never null |
| `concepts` | `Record<string, unknown>[]` | Concept graph for the UI: `[{id, name, prerequisites}]`. | empty while generating or failed |

**Real examples:**

_courses_create_ready_

`POST /courses` -> **200** (16 ms), file `docs/examples/courses_create_ready.json`

```json
{
  "course_id": "b0dafa63",
  "status": "ready",
  "topic": "prompt engineering",
  "concepts": [
    {
      "id": "language_model_basics",
      "name": "Language model basics",
      "prerequisites": []
    },
    {
      "id": "prompt_structure",
      "name": "Prompt structure",
      "prerequisites": []
    },
    {
      "id": "sampling_temperature",
      "name": "Sampling temperature",
      "prerequisites": []
    },
    {
      "id": "context_window",
      "name": "Context window",
      "prerequisites": [
        "language_model_basics"
      ]
    },
    {
      "id": "clear_instructions",
      "name": "Clear instructions",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "role_prompting",
      "name": "Role prompting",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "few_shot_examples",
      "name": "Few-shot examples",
      "prerequisites": [
        "prompt_structure",
        "clear_instructions"
      ]
    },
    {
      "id": "output_formatting",
      "name": "Output formatting",
      "prerequisites": [
        "clear_instructions"
      ]
    },
    {
      "id": "iterative_refinement",
      "name": "Iterative refinement",
      "prerequisites": [
        "clear_instructions",
        "few_shot_examples"
      ]
    },
    {
      "id": "hallucination_checking",
      "name": "Hallucination checking",
      "prerequisites": [
        "context_window",
        "sampling_temperature"
      ]
    }
  ]
}
```

_courses_create_generating_

`POST /courses` -> **200** (captured in an earlier run), file `docs/examples/courses_create_generating.json`

```json
{
  "course_id": "c6aaba84",
  "status": "generating",
  "topic": "SQL joins",
  "concepts": []
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |
| 422 | body invalid (missing prompt, unknown level) | {"detail": [{"type": "missing", "loc": ["body", "prompt"], "msg": "Field required", "input": {"level": "beginner"}}]} |

**Side effects:** Creates a course (and starts LLM generation) or updates the deadline of the existing one.

**Latency:** 2 successful calls: median 0.008 s, max 0.016 s. Never waits for the LLM: course generation and research run in the background.

**Idempotency and polling:** Repeat calls with the same prompt and level return the same course_id. Poll GET /courses/{cid} every 2 s while status is `generating`.

### `GET /courses/{cid}`

Returns the course status, topic and concept graph.

**When to call:** While polling after creation, and to draw the graph.

**Path parameters:** `cid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200** (`CreateCourseOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `course_id` | `string` | Id to use in every learner URL. | - |
| `status` | `string` | `generating`, `ready` or `failed`. | - |
| `topic` | `string` | Topic name for headings. While generating it is the prompt. | never null |
| `concepts` | `Record<string, unknown>[]` | Concept graph for the UI: `[{id, name, prerequisites}]`. | empty while generating or failed |

**Real examples:**

_course_get_

`GET /courses/b0dafa63` -> **200** (0 ms), file `docs/examples/course_get.json`

```json
{
  "course_id": "b0dafa63",
  "status": "ready",
  "topic": "prompt engineering",
  "concepts": [
    {
      "id": "language_model_basics",
      "name": "Language model basics",
      "prerequisites": []
    },
    {
      "id": "prompt_structure",
      "name": "Prompt structure",
      "prerequisites": []
    },
    {
      "id": "sampling_temperature",
      "name": "Sampling temperature",
      "prerequisites": []
    },
    {
      "id": "context_window",
      "name": "Context window",
      "prerequisites": [
        "language_model_basics"
      ]
    },
    {
      "id": "clear_instructions",
      "name": "Clear instructions",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "role_prompting",
      "name": "Role prompting",
      "prerequisites": [
        "prompt_structure"
      ]
    },
    {
      "id": "few_shot_examples",
      "name": "Few-shot examples",
      "prerequisites": [
        "prompt_structure",
        "clear_instructions"
      ]
    },
    {
      "id": "output_formatting",
      "name": "Output formatting",
      "prerequisites": [
        "clear_instructions"
      ]
    },
    {
      "id": "iterative_refinement",
      "name": "Iterative refinement",
      "prerequisites": [
        "clear_instructions",
        "few_shot_examples"
      ]
    },
    {
      "id": "hallucination_checking",
      "name": "Hallucination checking",
      "prerequisites": [
        "context_window",
        "sampling_temperature"
      ]
    }
  ]
}
```

_course_get_generating_

`GET /courses/c6aaba84` -> **200** (captured in an earlier run), file `docs/examples/course_get_generating.json`

```json
{
  "course_id": "c6aaba84",
  "status": "generating",
  "topic": "SQL joins",
  "concepts": []
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |
| 404 | unknown course id | {"detail": "course 'no-such-course' not found"} |

**Side effects:** none

**Latency:** 2 successful calls: median 0.000 s, max 0.000 s. Never waits for the LLM: course generation and research run in the background.

**Idempotency and polling:** Safe to poll every 2 s while `generating`; stop on `ready` or `failed`.

### `POST /courses/{cid}/learners/{lid}/start`

Creates the learner for this course and returns the diagnostic: one question per concept.

**When to call:** Once per learner, after the course is ready.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200** (`StartOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `questions` | `QuestionPublic[]` | The diagnostic: one question per concept, in roadmap order. | - |

`QuestionPublic`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `id` | `string` | Question id; send it back in an answer. | - |
| `concept_id` | `string` | Concept this question tests. | - |
| `prompt` | `string` | Question text (plain text, may contain code inline). | - |
| `options` | `string[]` | Exactly 4 option texts. Answer with the 0-based index. | - |

**Real examples:**

_start_

`POST /courses/b0dafa63/learners/docs-231157/start` -> **200** (16 ms), file `docs/examples/start.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "questions": [
    {
      "id": "f707cec4-language_model_basics-d1",
      "concept_id": "language_model_basics",
      "prompt": "What does a language model do when it receives a prompt?",
      "options": [
        "Understands the prompt's meaning the way a person does",
        "Predicts the likely next text given the input",
        "Picks a fixed reply it wrote for that exact prompt",
        "Searches a stored database for the matching answer"
      ]
    },
    {
      "id": "f707cec4-prompt_structure-d1",
      "concept_id": "prompt_structure",
      "prompt": "Which part of a prompt tells the model what task to perform?",
      "options": [
        "Input data",
        "Instruction",
        "Context",
        "Output format"
      ]
    },
    {
      "id": "f707cec4-sampling_temperature-d1",
      "concept_id": "sampling_temperature",
      "prompt": "What does a low sampling temperature mainly change in a model's output?",
      "options": [
        "It makes the model pick its least likely words",
        "It makes word choices more predictable and repeatable",
        "It makes the model's answers more factually accurate",
        "It teaches the model new facts for the reply"
      ]
    },
    {
      "id": "f707cec4-context_window-d1",
      "concept_id": "context_window",
      "prompt": "A user chatted with a model for an hour, then sends a new request containing none of that earlier text. What can the model use to answer?",
      "options": [
        "A saved summary of the earlier chat",
        "Only the last sentence the user typed before",
        "Only the text included in this new request",
        "Everything from the previous hour of chat"
      ]
    },
    "... 6 more"
  ]
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | unknown course | {"detail": "course 'no-such-course' not found"} |
| 409 | learner already started | {"detail": "learner 'docs-231157' already started course 'b0dafa63'"} |
| 409 | course not ready (`course '...' is generating`) | `{"detail": "..."}` |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** Creates the learner state (every concept at the prior, roadmap in prerequisite order); the diagnostic questions become the only answerable ones.

**Latency:** 5 successful calls: median 0.016 s, max 0.078 s. No LLM call observed.

**Idempotency and polling:** Not idempotent: a second call returns 409. Use GET .../state to detect an existing learner.

### `POST /courses/{cid}/learners/{lid}/attempts`

Grades a round of answers, updates mastery, misconceptions and the review schedule, decides the next step and returns it with its material. The first call answers the diagnostic.

**When to call:** Whenever the learner submits the questions on screen.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body** (`SubmitAnswersIn`):

| Field | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `answers` | `AnswerIn[]` | yes | - | One entry per answered question. Only questions served to this learner are accepted. |

Each answer (`AnswerIn`):

| Field | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `question_id` | `string` | yes | - | Id of a served question. |
| `chosen_index` | `number` | yes | - | 0-based index into `options`. |
| `confidence` | `"low" | "medium" | "high" | null` | no | `low`, `medium`, `high` | Optional self-reported confidence. Low confidence on a right answer counts less; high confidence on a wrong answer counts as stronger misconception evidence; on the diagnostic it sets how soon placed concepts are re-checked (low 1 day, medium 2, high 3). |

Real request body:
```json
{
  "answers": [
    {
      "question_id": "f707cec4-language_model_basics-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-prompt_structure-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-sampling_temperature-d1",
      "chosen_index": 1,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-d1",
      "chosen_index": 0,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-clear_instructions-d1",
      "chosen_index": 0
    },
    {
      "question_id": "f707cec4-role_prompting-d1",
      "chosen_index": 0,
      "confidence": "low"
    },
    {
      "question_id": "f707cec4-few_shot_examples-d1",
      "chosen_index": 2,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-output_formatting-d1",
      "chosen_index": 2,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-iterative_refinement-d1",
      "chosen_index": 0,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-hallucination_checking-d1",
      "chosen_index": 3,
      "confidence": "high"
    }
  ]
}
```

**Response 200** (`AttemptResultOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `graded` | `AnswerGraded[]` | Per-answer result, in submission order. | - |
| `correct_indices` | `Record<string, number>` | question_id -> correct option index (only after grading). | - |
| `explanations` | `Record<string, string>` | question_id -> why the right answer is right. | - |
| `mastery` | `Record<string, number>` | concept_id -> p_mastery after this round, for every concept. | - |
| `new_confirmed_misconceptions` | `string[]` | Tags that became confirmed in this round. | usually empty |
| `messages` | `string[]` | Encouragement and status lines to show as toasts. | often empty |
| `next` | `StepOut` | The next step with its material (same as GET .../next right after). | - |

`AnswerGraded`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `question_id` | `string` | Question answered. | - |
| `concept_id` | `string` | Its concept. | - |
| `correct` | `boolean` | Whether the chosen option was right. | - |
| `chosen_tag` | `string | null` | Misconception tag of the wrong option picked. | null when correct |
| `confidence` | `string | null` | Echo of the confidence sent. | null when not sent |

`StepOut`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `step` | `Step` | The brain's decision: what to show next. | - |
| `reason` | `string` | Human-readable explanation of the decision, built from facts. | never empty in this run |
| `lesson` | `Lesson | null` | Lesson for lesson/fallback steps. | null for review, session_end, done; null if generation failed |
| `questions` | `QuestionPublic[]` | Questions to answer next (3 for lessons, 2 for reviews). | empty for session_end and done |

`Step`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `kind` | `"lesson" | "review" | "fallback" | "session_end" | "done"` | What to render: lesson, review, fallback, session_end, done. | - |
| `concept_id` | `string | null` | Concept to teach or review. For fallback it is the prerequisite being revisited. | null for session_end and done |
| `target_misconceptions` | `string[]` | Confirmed misconception tags this lesson addresses. | empty when none are confirmed |
| `avoid_styles` | `string[]` | Lesson styles already tried for this concept (informational). | often empty |
| `difficulty` | `number | null` | Reserved. | always null in this run |
| `target_concept` | `string | null` | For fallback: the concept the learner is stuck on. | null except for fallback |
| `give_up_after` | `boolean` | True on the last attempt before the concept is flagged needs_help. | - |

`Lesson`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `concept_id` | `string` | Concept taught. | - |
| `style` | `string` | worked_example, contrast, analogy or step_by_step. | - |
| `explanation` | `string` | Lesson text, 120 to 200 words, plain text. | - |
| `targets` | `string[]` | Misconception tags addressed. | empty when none |
| `resources` | `Resource[]` | Researched articles and videos for the concept. | empty until the concept's research is ready |

**Real examples:**

_attempts_diagnostic_

`POST /courses/b0dafa63/learners/docs-231157/attempts` -> **200** (16 ms), file `docs/examples/attempts_diagnostic.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "graded": [
    {
      "question_id": "f707cec4-language_model_basics-d1",
      "concept_id": "language_model_basics",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-prompt_structure-d1",
      "concept_id": "prompt_structure",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    "... 8 more"
  ],
  "correct_indices": {
    "f707cec4-prompt_structure-d1": 1,
    "f707cec4-iterative_refinement-d1": 0,
    "f707cec4-role_prompting-d1": 1,
    "f707cec4-context_window-d1": 2,
    "f707cec4-output_formatting-d1": 2,
    "f707cec4-language_model_basics-d1": 1,
    "f707cec4-clear_instructions-d1": 0,
    "f707cec4-few_shot_examples-d1": 2,
    "f707cec4-hallucination_checking-d1": 3,
    "f707cec4-sampling_temperature-d1": 1
  },
  "explanations": {
    "f707cec4-prompt_structure-d1": "The instruction states the task, such as summarize or transl...",
    "f707cec4-iterative_refinement-d1": "A prompt needs testing across varied inputs to show where it...",
    "f707cec4-role_prompting-d1": "A role changes the style, focus and perspective of the same ...",
    "f707cec4-context_window-d1": "The model only sees the text inside the current request's co...",
    "f707cec4-output_formatting-d1": "Fixed structure lets code extract values directly. Format de...",
    "f707cec4-language_model_basics-d1": "A language model generates text by predicting which text is ...",
    "f707cec4-clear_instructions-d1": "A specific format and count tells the model exactly what out...",
    "f707cec4-few_shot_examples-d1": "Examples demonstrate the output pattern, so labeled examples...",
    "f707cec4-hallucination_checking-d1": "Confident wording does not indicate accuracy, so claims need...",
    "f707cec4-sampling_temperature-d1": "Low temperature concentrates sampling on the highest-probabi..."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.1774193548387097,
    "clear_instructions": 0.85,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [
    "context_window__model_remembers_everything"
  ],
  "messages": [
    "3 correct in a row.",
    "Placed 8 concepts as already known; I'll check them again wi..."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "context_window",
      "target_misconceptions": [
        "context_window__model_remembers_everything"
      ],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "placed as known: language_model_basics, prompt_structure, sa...",
    "lesson": {
      "concept_id": "context_window",
      "style": "contrast",
      "explanation": "Here is the key idea: a context window is the fixed amount o...",
      "targets": [
        "context_window__model_remembers_everything"
      ],
      "resources": [
        {
          "kind": "article",
          "title": "AI Prompting (3/10): Context Windows Explained ...",
          "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/...",
          "snippet": "A context window is the amount of text an AI model can \"see\"..."
        },
        {
          "kind": "article",
          "title": "What is a context window? | IBM",
          "url": "https://www.ibm.com/think/topics/context-window",
          "snippet": "An LLM\u2019s context window can be thought of as the equivalent ..."
        },
        "... 1 more"
      ]
    },
    "questions": [
      {
        "id": "f707cec4-context_window-p1",
        "concept_id": "context_window",
        "prompt": "A 500-word English paragraph uses more than 500 tokens in a ...",
        "options": [
          "Tokens are often shorter than words, so one word can span se...",
          "The window also stores a saved copy of the words",
          "... 2 more"
        ]
      },
      {
        "id": "f707cec4-context_window-p2",
        "concept_id": "context_window",
        "prompt": "You need a model to analyze a 60-page report, but the chat's...",
        "options": [
          "Assume the first pages stay visible while the rest is droppe...",
          "Count pages as words and assume the report fits",
          "... 2 more"
        ]
      },
      "... 1 more"
    ]
  }
}
```

_attempts_practice_

`POST /courses/b0dafa63/learners/docs-231157/attempts` -> **200** (16 ms), file `docs/examples/attempts_practice.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "graded": [
    {
      "question_id": "f707cec4-context_window-p1",
      "concept_id": "context_window",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-p2",
      "concept_id": "context_window",
      "correct": true,
      "chosen_tag": null,
      "confidence": "medium"
    },
    "... 1 more"
  ],
  "correct_indices": {
    "f707cec4-context_window-t1": 0,
    "f707cec4-context_window-p1": 0,
    "f707cec4-context_window-p2": 3
  },
  "explanations": {
    "f707cec4-context_window-t1": "A new session only includes the text sent in that request. W...",
    "f707cec4-context_window-p1": "The window is measured in tokens, and a single word can be s...",
    "f707cec4-context_window-p2": "Only text inside the window is usable, so sending the most r..."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.4814035218438767,
    "clear_instructions": 0.85,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "Misconception context_window__model_remembers_everything res..."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "role_prompting",
      "target_misconceptions": [],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "role_prompting: mastery 0.18, lowest among unlocked concepts",
    "lesson": {
      "concept_id": "role_prompting",
      "style": "worked_example",
      "explanation": "Role prompting means assigning the model a role, persona, or...",
      "targets": [],
      "resources": [
        {
          "kind": "article",
          "title": "Assigning Roles to Chatbots",
          "url": "https://learnprompting.org/docs/basics/roles",
          "snippet": "Role prompting is a technique that involves assigning a role..."
        },
        {
          "kind": "article",
          "title": "Does Role Prompting Work? What the Research Says",
          "url": "https://www.jdhwilkins.com/role-prompting-giving-ai-a-person...",
          "snippet": "Role prompting means giving an AI model a character, job tit..."
        },
        "... 1 more"
      ]
    },
    "questions": [
      {
        "id": "f707cec4-role_prompting-p1",
        "concept_id": "role_prompting",
        "prompt": "A prompt says 'You are a tax lawyer' and asks about a studen...",
        "options": [
          "Any professional role would be equally accurate here",
          "The role only changes style; facts can still be wrong",
          "... 2 more"
        ]
      },
      {
        "id": "f707cec4-role_prompting-p2",
        "concept_id": "role_prompting",
        "prompt": "You want a critical review of a startup pitch. Which role an...",
        "options": [
          "A skeptical investor asked to flag risks",
          "A licensed CPA who audits the numbers",
          "... 2 more"
        ]
      },
      "... 1 more"
    ]
  }
}
```

_attempts_review_failed_

`POST /courses/b0dafa63/learners/docs-231157/attempts` -> **200** (16 ms), file `docs/examples/attempts_review_failed.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "graded": [
    {
      "question_id": "f707cec4-clear_instructions-p1",
      "concept_id": "clear_instructions",
      "correct": false,
      "chosen_tag": "clear_instructions__model_reads_intent",
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-clear_instructions-p2",
      "concept_id": "clear_instructions",
      "correct": false,
      "chosen_tag": "clear_instructions__vague_request_is_fine",
      "confidence": "high"
    }
  ],
  "correct_indices": {
    "f707cec4-clear_instructions-p2": 2,
    "f707cec4-clear_instructions-p1": 2
  },
  "explanations": {
    "f707cec4-clear_instructions-p2": "Naming the specific change and the constraint tells the model the exact task, rather than leaving 'improve' open to interpretation.",
    "f707cec4-clear_instructions-p1": "Naming the target audience and style describes the desired behavior, which is more actionable than a prohibition or a vague quality request."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.4814035218438767,
    "clear_instructions": 0.255723006486074,
    "role_prompting": 0.1774193548387097,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [
    "clear_instructions__model_reads_intent",
    "clear_instructions__vague_request_is_fine"
  ],
  "messages": [
    "You slipped on clear_instructions. This happens, it is why reviews exist."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "clear_instructions",
      "target_misconceptions": [
        "clear_instructions__model_reads_intent",
        "clear_instructions__vague_request_is_fine"
      ],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "relearning clear_instructions first: it was mastered, slipped to 0.26 (lapses 1)",
    "lesson": {
      "concept_id": "clear_instructions",
      "style": "contrast",
      "explanation": "Here is the right idea set against the belief it replaces. You may think the model knows the goals you leave unstated, such as who the audience is or how long the answer should be. It does not. The mo...",
      "targets": [
        "clear_instructions__model_reads_intent",
        "clear_instructions__vague_request_is_fine"
      ],
      "resources": []
    },
    "questions": [
      {
        "id": "f707cec4-clear_instructions-t1",
        "concept_id": "clear_instructions",
        "prompt": "You want a customer support reply that includes a refund policy link. Which instruction is clearest?",
        "options": [
          "Reply in under 100 words with the refund link.",
          "Don't write a long reply or leave out key items.",
          "Write a helpful reply to the customer.",
          "Reply briefly and cover the usual details."
        ]
      },
      {
        "id": "f707cec4-clear_instructions-t2",
        "concept_id": "clear_instructions",
        "prompt": "A model keeps adding disclaimers to medical summaries. Which change most directly fixes it?",
        "options": [
          "Specify: output only the summary paragraph.",
          "Don't add any disclaimers to the reply.",
          "You understand why disclaimers aren't needed here.",
          "Write the summary the way you normally would."
        ]
      },
      {
        "id": "f707cec4-clear_instructions-d2",
        "concept_id": "clear_instructions",
        "prompt": "Which instruction states the desired behavior directly?",
        "options": [
          "Answer as you think best.",
          "Don't include extra commentary.",
          "Reply with only the final answer.",
          "Answer the question somehow."
        ]
      }
    ]
  }
}
```

_attempts_all_known_done_

`POST /courses/b0dafa63/learners/docs-231157-all/attempts` -> **200** (16 ms), file `docs/examples/attempts_all_known_done.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "graded": [
    {
      "question_id": "f707cec4-language_model_basics-d1",
      "concept_id": "language_model_basics",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-prompt_structure-d1",
      "concept_id": "prompt_structure",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    {
      "question_id": "f707cec4-sampling_temperature-d1",
      "concept_id": "sampling_temperature",
      "correct": true,
      "chosen_tag": null,
      "confidence": "high"
    },
    "... 7 more"
  ],
  "correct_indices": {
    "f707cec4-prompt_structure-d1": 1,
    "f707cec4-iterative_refinement-d1": 0,
    "f707cec4-role_prompting-d1": 1,
    "f707cec4-context_window-d1": 2,
    "f707cec4-output_formatting-d1": 2,
    "f707cec4-language_model_basics-d1": 1,
    "f707cec4-clear_instructions-d1": 0,
    "f707cec4-few_shot_examples-d1": 2,
    "f707cec4-hallucination_checking-d1": 3,
    "f707cec4-sampling_temperature-d1": 1
  },
  "explanations": {
    "f707cec4-prompt_structure-d1": "The instruction states the task, such as summarize or translate. The other parts supply information ...",
    "f707cec4-iterative_refinement-d1": "A prompt needs testing across varied inputs to show where it works and where it fails. Revising base...",
    "f707cec4-role_prompting-d1": "A role changes the style, focus and perspective of the same model. It does not add knowledge the mod...",
    "f707cec4-context_window-d1": "The model only sees the text inside the current request's context window. Earlier chats are not avai...",
    "f707cec4-output_formatting-d1": "Fixed structure lets code extract values directly. Format determines whether output can be used by s...",
    "f707cec4-language_model_basics-d1": "A language model generates text by predicting which text is likely to come next, based on the input ...",
    "f707cec4-clear_instructions-d1": "A specific format and count tells the model exactly what output to produce, so it does not have to g...",
    "f707cec4-few_shot_examples-d1": "Examples demonstrate the output pattern, so labeled examples in the exact format teach the model wha...",
    "f707cec4-hallucination_checking-d1": "Confident wording does not indicate accuracy, so claims need checking against reliable sources.",
    "f707cec4-sampling_temperature-d1": "Low temperature concentrates sampling on the highest-probability words, so outputs become more predi..."
  },
  "mastery": {
    "language_model_basics": 0.85,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.85,
    "clear_instructions": 0.85,
    "role_prompting": 0.85,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "3 correct in a row.",
    "Placed 10 concepts as already known; I'll check them again within 3 days.",
    "every reachable concept is mastered"
  ],
  "next": {
    "step": {
      "kind": "done",
      "concept_id": null,
      "target_misconceptions": [],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "placed as known: language_model_basics, prompt_structure, sampling_temperature, context_window, clea...",
    "lesson": null,
    "questions": []
  }
}
```

_attempts_needs_help_

`POST /courses/b0dafa63/learners/docs-231157-stuck/attempts` -> **200** (15 ms), file `docs/examples/attempts_needs_help.json`

```json
{
  "graded": [
    {
      "question_id": "f707cec4-context_window-p1",
      "concept_id": "context_window",
      "correct": false,
      "chosen_tag": "context_window__model_remembers_everything",
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-p2",
      "concept_id": "context_window",
      "correct": false,
      "chosen_tag": "context_window__earlier_text_always_visible",
      "confidence": "medium"
    },
    {
      "question_id": "f707cec4-context_window-t1",
      "concept_id": "context_window",
      "correct": false,
      "chosen_tag": "context_window__limit_is_only_words",
      "confidence": "medium"
    }
  ],
  "correct_indices": {
    "f707cec4-context_window-t1": 0,
    "f707cec4-context_window-p1": 0,
    "f707cec4-context_window-p2": 3
  },
  "explanations": {
    "f707cec4-context_window-t1": "A new session only includes the text sent in that request. Without the day-one text, the model has no access to the order number.",
    "f707cec4-context_window-p1": "The window is measured in tokens, and a single word can be split into several tokens. So a word count can understate the token count.",
    "f707cec4-context_window-p2": "Only text inside the window is usable, so sending the most relevant sections in pieces works within the limit. Relying on memory or assuming a fit does not."
  },
  "mastery": {
    "language_model_basics": 0.9977042871374661,
    "prompt_structure": 0.85,
    "sampling_temperature": 0.85,
    "context_window": 0.17307692307692307,
    "clear_instructions": 0.85,
    "role_prompting": 0.85,
    "few_shot_examples": 0.85,
    "output_formatting": 0.85,
    "iterative_refinement": 0.85,
    "hallucination_checking": 0.85
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "context_window is flagged for help: it may need a different resource or a person.",
    "every reachable concept is mastered; needs help: context_window"
  ],
  "next": {
    "step": {
      "kind": "done",
      "concept_id": null,
      "target_misconceptions": [],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "every reachable concept is mastered; needs help: context_window",
    "lesson": null,
    "questions": []
  }
}
```

_attempts_with_deadline_

`POST /courses/c6aaba84/learners/docs-231157-deadline/attempts` -> **200** (15 ms), file `docs/examples/attempts_with_deadline.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "graded": [
    {
      "question_id": "d3f0e36a-tables_rows_columns-d1",
      "concept_id": "tables_rows_columns",
      "correct": false,
      "chosen_tag": "tables_rows_columns__table_is_one_value",
      "confidence": null
    },
    {
      "question_id": "d3f0e36a-select_columns-d1",
      "concept_id": "select_columns",
      "correct": false,
      "chosen_tag": "select_columns__select_changes_data",
      "confidence": null
    },
    "... 8 more"
  ],
  "correct_indices": {
    "d3f0e36a-primary_keys-d1": 1,
    "d3f0e36a-table_aliases-d1": 1,
    "d3f0e36a-join_multiple_tables-d1": 1,
    "d3f0e36a-select_columns-d1": 2,
    "d3f0e36a-inner_join-d1": 2,
    "d3f0e36a-where_filtering-d1": 1,
    "d3f0e36a-null_values-d1": 2,
    "d3f0e36a-tables_rows_columns-d1": 3,
    "d3f0e36a-left_join-d1": 3,
    "d3f0e36a-foreign_keys-d1": 1
  },
  "explanations": {
    "d3f0e36a-primary_keys-d1": "A student_id gives each student a unique value that identifi...",
    "d3f0e36a-table_aliases-d1": "The alias e is declared in FROM and exists only for this que...",
    "d3f0e36a-join_multiple_tables-d1": "Each JOIN adds one table through its own matching keys, so t...",
    "d3f0e36a-select_columns-d1": "SELECT only reads data and returns it as a result; the store...",
    "d3f0e36a-inner_join-d1": "INNER JOIN keeps only rows where the ON condition matches, p...",
    "d3f0e36a-where_filtering-d1": "WHERE filters rows, so only rows where the condition is true...",
    "d3f0e36a-null_values-d1": "NULL marks a value that is absent or unknown. It is not a nu...",
    "d3f0e36a-tables_rows_columns-d1": "A row is one record, holding one customer's values across th...",
    "d3f0e36a-left_join-d1": "LEFT JOIN keeps every left-table row, so each customer appea...",
    "d3f0e36a-foreign_keys-d1": "A foreign key stores only the referenced primary key value, ..."
  },
  "mastery": {
    "tables_rows_columns": 0.1774193548387097,
    "select_columns": 0.1774193548387097,
    "null_values": 0.1774193548387097,
    "primary_keys": 0.1774193548387097,
    "foreign_keys": 0.1774193548387097,
    "where_filtering": 0.1774193548387097,
    "table_aliases": 0.1774193548387097,
    "inner_join": 0.1774193548387097,
    "left_join": 0.1774193548387097,
    "join_multiple_tables": 0.1774193548387097
  },
  "new_confirmed_misconceptions": [],
  "messages": [
    "2 days left before your deadline."
  ],
  "next": {
    "step": {
      "kind": "lesson",
      "concept_id": "tables_rows_columns",
      "target_misconceptions": [],
      "avoid_styles": [],
      "difficulty": null,
      "target_concept": null,
      "give_up_after": false
    },
    "reason": "tables_rows_columns: mastery 0.18, lowest among unlocked con...",
    "lesson": {
      "concept_id": "tables_rows_columns",
      "style": "worked_example",
      "explanation": "Think of a table as a spreadsheet with a fixed structure. It...",
      "targets": [],
      "resources": []
    },
    "questions": [
      {
        "id": "d3f0e36a-tables_rows_columns-p1",
        "concept_id": "tables_rows_columns",
        "prompt": "A table stores orders with columns order_id, customer and to...",
        "options": [
          "An update to the single table value",
          "A new row with one value per column",
          "... 2 more"
        ]
      },
      {
        "id": "d3f0e36a-tables_rows_columns-p2",
        "concept_id": "tables_rows_columns",
        "prompt": "A table has one row per student and columns for name and gra...",
        "options": [
          "Each row is one student's record",
          "The whole table holds one class grade",
          "... 2 more"
        ]
      },
      "... 1 more"
    ]
  }
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 422 | a question was not served to this learner (lists the ids) | {"detail": "questions not served to this learner: ['f707cec4-language_model_basics-d2']"} |
| 422 | empty `answers`, `chosen_index` out of range, or body invalid | `{"detail": "..."}` |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** Records every answer; updates the learner state; stores the next step and its questions (only those become answerable). May call the LLM to write the next lesson.

**Latency:** 14 successful calls: median 0.016 s, max 0.203 s. No LLM call observed.

**Idempotency and polling:** Not idempotent: answers count once; resubmitting the same ids returns 422 because they are no longer served.

### `GET /courses/{cid}/learners/{lid}/next`

Serves the stored next step with its lesson and questions. The first call after an advance or a new session builds the material (may call the LLM); later calls return the same thing.

**When to call:** After advance or sessions/new, after a page reload, or any time the client lost the step.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200** (`StepOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `step` | `Step` | The brain's decision: what to show next. | - |
| `reason` | `string` | Human-readable explanation of the decision, built from facts. | never empty in this run |
| `lesson` | `Lesson | null` | Lesson for lesson/fallback steps. | null for review, session_end, done; null if generation failed |
| `questions` | `QuestionPublic[]` | Questions to answer next (3 for lessons, 2 for reviews). | empty for session_end and done |

`Step`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `kind` | `"lesson" | "review" | "fallback" | "session_end" | "done"` | What to render: lesson, review, fallback, session_end, done. | - |
| `concept_id` | `string | null` | Concept to teach or review. For fallback it is the prerequisite being revisited. | null for session_end and done |
| `target_misconceptions` | `string[]` | Confirmed misconception tags this lesson addresses. | empty when none are confirmed |
| `avoid_styles` | `string[]` | Lesson styles already tried for this concept (informational). | often empty |
| `difficulty` | `number | null` | Reserved. | always null in this run |
| `target_concept` | `string | null` | For fallback: the concept the learner is stuck on. | null except for fallback |
| `give_up_after` | `boolean` | True on the last attempt before the concept is flagged needs_help. | - |

`Lesson`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `concept_id` | `string` | Concept taught. | - |
| `style` | `string` | worked_example, contrast, analogy or step_by_step. | - |
| `explanation` | `string` | Lesson text, 120 to 200 words, plain text. | - |
| `targets` | `string[]` | Misconception tags addressed. | empty when none |
| `resources` | `Resource[]` | Researched articles and videos for the concept. | empty until the concept's research is ready |

`QuestionPublic`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `id` | `string` | Question id; send it back in an answer. | - |
| `concept_id` | `string` | Concept this question tests. | - |
| `prompt` | `string` | Question text (plain text, may contain code inline). | - |
| `options` | `string[]` | Exactly 4 option texts. Answer with the 0-based index. | - |

**Real examples:**

_next_lesson_

`GET /courses/b0dafa63/learners/docs-231157/next` -> **200** (15 ms), file `docs/examples/next_lesson.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "step": {
    "kind": "lesson",
    "concept_id": "context_window",
    "target_misconceptions": [
      "context_window__model_remembers_everything"
    ],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "context_window__model_remembers_everything confirmed, evidence 2; context_window needs it",
  "lesson": {
    "concept_id": "context_window",
    "style": "contrast",
    "explanation": "Here is the key idea: a context window is the fixed amount of text a model can consider in one request, like its working memory. Many learners believe the model remembers every past chat, but that is ...",
    "targets": [
      "context_window__model_remembers_everything"
    ],
    "resources": [
      {
        "kind": "article",
        "title": "AI Prompting (3/10): Context Windows Explained ...",
        "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/ai_prompting_310_context_windows",
        "snippet": "A context window is the amount of text an AI model can \"see\" and consider at once. Think of it like the AI's working memory - everything it can"
      },
      {
        "kind": "article",
        "title": "What is a context window? | IBM",
        "url": "https://www.ibm.com/think/topics/context-window",
        "snippet": "An LLM\u2019s context window can be thought of as the equivalent of its working memory. It determines how long of a conversation it can carry out without forgetting details from earlier in the exchange. It..."
      },
      {
        "kind": "video",
        "title": "Why AI Models Forget Previous Messages ?What Is Context Length in LLMs?",
        "url": "https://www.youtube.com/watch?v=bUOfdbyCDFA",
        "snippet": "Why does ChatGPT forget past conversations? Is it really forgetting \u2014 or is something else happening? In this video, I explain ..."
      }
    ]
  },
  "questions": [
    {
      "id": "f707cec4-context_window-p1",
      "concept_id": "context_window",
      "prompt": "A 500-word English paragraph uses more than 500 tokens in a model's context window. Why?",
      "options": [
        "Tokens are often shorter than words, so one word can span several",
        "The window also stores a saved copy of the words",
        "Tokens are counted per sentence rather than per word",
        "Each word is counted twice in the window"
      ]
    },
    {
      "id": "f707cec4-context_window-p2",
      "concept_id": "context_window",
      "prompt": "You need a model to analyze a 60-page report, but the chat's context window is too small to hold all of it. What is the best approach?",
      "options": [
        "Assume the first pages stay visible while the rest is dropped",
        "Count pages as words and assume the report fits",
        "Expect the model to recall the report from last week's chat",
        "Split the report and send the key sections that fit the window"
      ]
    },
    {
      "id": "f707cec4-context_window-t1",
      "concept_id": "context_window",
      "prompt": "A support bot answers a customer's question correctly on day one. On day two, in a new session with no earlier text, it ignores the order number the customer gave on day one. What is the most likely c...",
      "options": [
        "The day-one text is no longer in the context window",
        "The order number used more words than the bot's limit",
        "Earlier messages stay in view but were misread",
        "The bot saved the order number in permanent memory and forgot it"
      ]
    }
  ]
}
```

_next_review_

`GET /courses/b0dafa63/learners/docs-231157/next` -> **200** (15 ms), file `docs/examples/next_review.json`

```json
{
  "step": {
    "kind": "review",
    "concept_id": "clear_instructions",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "clear_instructions review due since 2026-10-31; recall now 0.90",
  "lesson": null,
  "questions": [
    {
      "id": "f707cec4-clear_instructions-p1",
      "concept_id": "clear_instructions",
      "prompt": "You want a model to avoid technical terms. Which rewrite is clearest?",
      "options": [
        "Explain this simply; you know what I mean.",
        "Don't use technical terms in your explanation.",
        "Explain this in plain words for a child.",
        "Explain this in a way that is good."
      ]
    },
    {
      "id": "f707cec4-clear_instructions-p2",
      "concept_id": "clear_instructions",
      "prompt": "A prompt says 'Improve this code.' The model only renames variables. What is the best fix?",
      "options": [
        "Make this code better and cleaner overall.",
        "Improve this code; don't change what it does.",
        "Refactor this function to remove duplication.",
        "Improve this code; you know what I'm going for."
      ]
    }
  ]
}
```

_next_relearn_

`GET /courses/b0dafa63/learners/docs-231157/next` -> **200** (15 ms), file `docs/examples/next_relearn.json`

```json
{
  "step": {
    "kind": "lesson",
    "concept_id": "clear_instructions",
    "target_misconceptions": [
      "clear_instructions__model_reads_intent",
      "clear_instructions__vague_request_is_fine"
    ],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "relearning clear_instructions first: it was mastered, slipped to 0.26 (lapses 1)",
  "lesson": {
    "concept_id": "clear_instructions",
    "style": "contrast",
    "explanation": "Here is the right idea set against the belief it replaces. You may think the model knows the goals you leave unstated, such as who the audience is or how long the answer should be. It does not. The model only acts on what is written in your prompt, so anything you omit is a guess. Compare two requests. The vague one says: Write about our product. The clear one says: Write a 100-word product description for busy parents, mentioning price and the free returns policy, in a friendly tone. The vague version forces the model to choose the topic, length, audience, and tone on its own, and each choice is another chance to miss what you wanted. The belief that vague requests get good results breaks here: vagueness does not make the model smarter, it only increases guessing. A specific task removes most of those guesses, so the output is more likely to match your intent. Before you send a prompt, ask yourself what the model would have to guess, then write that answer down.",
    "targets": [
      "clear_instructions__model_reads_intent",
      "clear_instructions__vague_request_is_fine"
    ],
    "resources": []
  },
  "questions": [
    {
      "id": "f707cec4-clear_instructions-t1",
      "concept_id": "clear_instructions",
      "prompt": "You want a customer support reply that includes a refund policy link. Which instruction is clearest?",
      "options": [
        "Reply in under 100 words with the refund link.",
        "Don't write a long reply or leave out key items.",
        "Write a helpful reply to the customer.",
        "Reply briefly and cover the usual details."
      ]
    },
    {
      "id": "f707cec4-clear_instructions-t2",
      "concept_id": "clear_instructions",
      "prompt": "A model keeps adding disclaimers to medical summaries. Which change most directly fixes it?",
      "options": [
        "Specify: output only the summary paragraph.",
        "Don't add any disclaimers to the reply.",
        "You understand why disclaimers aren't needed here.",
        "Write the summary the way you normally would."
      ]
    },
    {
      "id": "f707cec4-clear_instructions-d2",
      "concept_id": "clear_instructions",
      "prompt": "Which instruction states the desired behavior directly?",
      "options": [
        "Answer as you think best.",
        "Don't include extra commentary.",
        "Reply with only the final answer.",
        "Answer the question somehow."
      ]
    }
  ]
}
```

_next_fallback_

`GET /courses/b0dafa63/learners/docs-231157-stuck/next` -> **200** (0 ms), file `docs/examples/next_fallback.json`

```json
{
  "step": {
    "kind": "fallback",
    "concept_id": "language_model_basics",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": "context_window",
    "give_up_after": false
  },
  "reason": "stuck on context_window; revisiting prerequisite language_model_basics (mastery 0.85)",
  "lesson": {
    "concept_id": "language_model_basics",
    "style": "worked_example",
    "explanation": "Let's see how a language model predicts text using one small example. Suppose you give it the prompt: \"The cat sat on the\". The model does not look up a fact or understand the sentence the way you do. Instead, it scores many possible next words based on patterns it learned from huge amounts of text. Step one: it reads your prompt as a sequence of tokens, which are chunks of words. Step two: it estimates probabilities for every possible next token. Words like \"mat\" or \"floor\" might get high scores, while \"piano\" gets a low one. Step three: it picks one token, often one of the most likely, and adds it to the text. Step four: it repeats the process with the longer text until it reaches a stopping point. So if your prompt is \"The cat sat on the\", the output is likely \"mat\", then a period, then more words. Notice what this means for you: the model continues whatever text it receives, so the wording of your prompt directly shapes what comes next. Keep this in mind as you write prompts, because a clearer starting text usually leads to a more useful continuation.",
    "targets": [],
    "resources": []
  },
  "questions": [
    {
      "id": "f707cec4-language_model_basics-p1",
      "concept_id": "language_model_basics",
      "prompt": "A model completes 'The sky is' with 'blue' most of the time. What is the most accurate explanation?",
      "options": [
        "It was told to answer blue and will repeat it exactly",
        "It judged blue to be the true color, as a person would",
        "Blue follows that phrase most often in its training text",
        "It checked a stored fact that the sky is blue"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-p2",
      "concept_id": "language_model_basics",
      "prompt": "Why might running the same prompt twice produce different completions?",
      "options": [
        "Completions are sampled from probabilities, so lower-ranked words can be picked",
        "The model rethinks its earlier answer and changes its mind",
        "The model rewrites its stored answer each time it is queried",
        "The prompt reaches the model in a slightly different form each run"
      ]
    },
    {
      "id": "f707cec4-language_model_basics-t1",
      "concept_id": "language_model_basics",
      "prompt": "A support bot is asked for the refund policy of a company whose documents it never saw, and it writes a convincing policy. What best explains this?",
      "options": [
        "It returns the same policy text on every run, so it repeats itself",
        "It continues learned text patterns, so it can invent plausible policy details",
        "It searched the company's policy page and copied the rule",
        "It understood the question and worked out the rule logically"
      ]
    }
  ]
}
```

_next_give_up_

`GET /courses/b0dafa63/learners/docs-231157-stuck/next` -> **200** (0 ms), file `docs/examples/next_give_up.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "step": {
    "kind": "lesson",
    "concept_id": "context_window",
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": true
  },
  "reason": "last try on context_window after 3 failed rounds",
  "lesson": {
    "concept_id": "context_window",
    "style": "worked_example",
    "explanation": "A context window is the amount of text an AI model can see and consider at once, like its working memory. Let's walk through a small example. Suppose the window holds about 40 words, and you have sent...",
    "targets": [],
    "resources": [
      {
        "kind": "article",
        "title": "AI Prompting (3/10): Context Windows Explained ...",
        "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/ai_prompting_310_context_windows",
        "snippet": "A context window is the amount of text an AI model can \"see\" and consider at once. Think of it like the AI's working memory - everything it can"
      },
      {
        "kind": "article",
        "title": "What is a context window? | IBM",
        "url": "https://www.ibm.com/think/topics/context-window",
        "snippet": "An LLM\u2019s context window can be thought of as the equivalent of its working memory. It determines how long of a conversation it can carry out without forgetting details from earlier in the exchange. It..."
      },
      {
        "kind": "video",
        "title": "Why AI Models Forget Previous Messages ?What Is Context Length in LLMs?",
        "url": "https://www.youtube.com/watch?v=bUOfdbyCDFA",
        "snippet": "Why does ChatGPT forget past conversations? Is it really forgetting \u2014 or is something else happening? In this video, I explain ..."
      }
    ]
  },
  "questions": [
    {
      "id": "f707cec4-context_window-p1",
      "concept_id": "context_window",
      "prompt": "A 500-word English paragraph uses more than 500 tokens in a model's context window. Why?",
      "options": [
        "Tokens are often shorter than words, so one word can span several",
        "The window also stores a saved copy of the words",
        "Tokens are counted per sentence rather than per word",
        "Each word is counted twice in the window"
      ]
    },
    {
      "id": "f707cec4-context_window-p2",
      "concept_id": "context_window",
      "prompt": "You need a model to analyze a 60-page report, but the chat's context window is too small to hold all of it. What is the best approach?",
      "options": [
        "Assume the first pages stay visible while the rest is dropped",
        "Count pages as words and assume the report fits",
        "Expect the model to recall the report from last week's chat",
        "Split the report and send the key sections that fit the window"
      ]
    },
    {
      "id": "f707cec4-context_window-t1",
      "concept_id": "context_window",
      "prompt": "A support bot answers a customer's question correctly on day one. On day two, in a new session with no earlier text, it ignores the order number the customer gave on day one. What is the most likely c...",
      "options": [
        "The day-one text is no longer in the context window",
        "The order number used more words than the bot's limit",
        "Earlier messages stay in view but were misread",
        "The bot saved the order number in permanent memory and forgot it"
      ]
    }
  ]
}
```

_next_session_end_

`GET /courses/b0dafa63/learners/docs-231157-stuck/next` -> **200** (15 ms), file `docs/examples/next_session_end.json`

```json
{
  "step": {
    "kind": "session_end",
    "concept_id": null,
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "15 questions this session; start a new session to continue",
  "lesson": null,
  "questions": []
}
```

_next_done_

`GET /courses/b0dafa63/learners/docs-231157-all/next` -> **200** (16 ms), file `docs/examples/next_done.json`

```json
{
  "step": {
    "kind": "done",
    "concept_id": null,
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "every reachable concept is mastered",
  "lesson": null,
  "questions": []
}
```

_next_done_with_needs_help_

`GET /courses/b0dafa63/learners/docs-231157-stuck/next` -> **200** (16 ms), file `docs/examples/next_done_with_needs_help.json`

```json
{
  "step": {
    "kind": "done",
    "concept_id": null,
    "target_misconceptions": [],
    "avoid_styles": [],
    "difficulty": null,
    "target_concept": null,
    "give_up_after": false
  },
  "reason": "every reachable concept is mastered; needs help: context_window",
  "lesson": null,
  "questions": []
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 409 | before the diagnostic is answered | {"detail": "no step decided yet: answer the diagnostic from /start first"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** First call after a decision: stores the served question ids and records the lesson style. Later calls: none.

**Latency:** 14 successful calls: median 0.015 s, max 0.016 s. No LLM call observed.

**Idempotency and polling:** Idempotent: identical calls return identical bodies.

### `GET /courses/{cid}/learners/{lid}/state`

Returns the dashboard: per-concept mastery, retrievability and schedule, misconceptions, gaps, roadmap, needs_help, pace and days_left, all at the learner's simulated now.

**When to call:** For the sidebar and progress views, after every attempt or advance.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200** (`MasteryOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `concepts` | `ConceptState[]` | Per-concept state, roadmap order. | - |
| `misconceptions` | `MisconceptionState[]` | Every misconception seen so far with its status. | empty before any wrong pick |
| `next_due` | `string | null` | Earliest scheduled review. | null when nothing is scheduled |
| `due` | `Record<string, string>` | concept_id -> scheduled review time (past times are due now). | empty when nothing is scheduled |
| `roadmap` | `string[]` | Concept ids, prerequisites first. | - |
| `needs_help` | `string[]` | Concepts the learner is stuck on. | usually empty |
| `days_left` | `number | null` | Whole days to the course deadline (learner's clock). | null without a deadline |
| `gaps` | `string[]` | Concepts not yet mastered, roadmap order. | empty when all are mastered |
| `retrievability` | `Record<string, number>` | concept_id -> recall probability now (1.0 if never mastered). | - |
| `pace` | `Record<string, number>` | `{mastered, total, attempts_per_mastered}`. | - |

`ConceptState`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `concept_id` | `string` | Concept. | - |
| `p_mastery` | `number` | Probability the concept is known (0..1); 0.85 or more counts as mastered. | - |
| `attempts` | `number` | Questions answered on this concept. | - |
| `failed_rounds` | `number` | Rounds in a row with a wrong answer while not mastered. | - |
| `stability_days` | `number` | Memory stability in days; review spacing grows with it. | 0 before mastery |
| `last_reviewed_at` | `string | null` | When the schedule last changed. | null before mastery or placement |
| `due_at` | `string | null` | When the next review is due. | null before mastery or placement |
| `lapses` | `number` | Failed reviews of a mastered concept. | - |
| `explanations_tried` | `string[]` | Lesson styles shown so far. | empty before the first lesson |
| `fallbacks` | `number` | Times the brain detoured to a prerequisite. | - |
| `needs_help` | `boolean` | Stuck after the last try: show a 'get help' card. | - |

`MisconceptionState`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `tag` | `string` | Misconception id, `<concept_id>__<slug>`. | - |
| `concept_id` | `string` | Its concept. | - |
| `status` | `"suspected" | "confirmed" | "resolved"` | suspected, confirmed or resolved. | - |
| `evidence` | `number` | Weight of wrong picks (1 per pick, 2 with high confidence); 2 confirms. | - |
| `clean_streak` | `number` | Correct answers in a row on questions testing it; 2 resolves it. | - |

**Real examples:**

_state_

`GET /courses/b0dafa63/learners/docs-231157/state` -> **200** (16 ms), file `docs/examples/state.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    "... 6 more"
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "clear_instructions__model_reads_intent",
      "concept_id": "clear_instructions",
      "status": "confirmed",
      "evidence": 2.0,
      "clean_streak": 0
    },
    "... 1 more"
  ],
  "next_due": "2026-11-01T17:42:07.820000",
  "due": {
    "language_model_basics": "2026-11-01T17:42:07.820000",
    "prompt_structure": "2026-11-01T17:42:07.820000",
    "sampling_temperature": "2026-11-01T17:42:07.820000",
    "clear_instructions": "2026-11-01T17:42:07.946000",
    "few_shot_examples": "2026-11-02T17:42:07.820000",
    "output_formatting": "2026-11-02T17:42:07.820000",
    "iterative_refinement": "2026-11-02T17:42:07.820000",
    "hallucination_checking": "2026-11-02T17:42:07.820000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "... 6 more"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "clear_instructions",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.948683205280355,
    "prompt_structure": 0.948683205280355,
    "sampling_temperature": 0.948683205280355,
    "context_window": 1.0,
    "clear_instructions": 0.9999999580740763,
    "role_prompting": 1.0,
    "few_shot_examples": 0.9654893216632301,
    "output_formatting": 0.9654893216632301,
    "iterative_refinement": 0.9654893216632301,
    "hallucination_checking": 0.9654893216632301
  },
  "pace": {
    "mastered": 7.0,
    "total": 10.0,
    "attempts_per_mastered": 2.142857142857143
  }
}
```

_state_after_diagnostic_

`GET /courses/b0dafa63/learners/docs-231157/state` -> **200** (16 ms), file `docs/examples/state_after_diagnostic.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    "... 6 more"
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "confirmed",
      "evidence": 2.0,
      "clean_streak": 0
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-10-31T17:42:07.820000",
  "due": {
    "language_model_basics": "2026-11-01T17:42:07.820000",
    "prompt_structure": "2026-11-01T17:42:07.820000",
    "sampling_temperature": "2026-11-01T17:42:07.820000",
    "clear_instructions": "2026-10-31T17:42:07.820000",
    "few_shot_examples": "2026-11-02T17:42:07.820000",
    "output_formatting": "2026-11-02T17:42:07.820000",
    "iterative_refinement": "2026-11-02T17:42:07.820000",
    "hallucination_checking": "2026-11-02T17:42:07.820000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "... 6 more"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9999999786084011,
    "prompt_structure": 0.9999999786084011,
    "sampling_temperature": 0.9999999786084011,
    "context_window": 1.0,
    "clear_instructions": 0.9999999572168027,
    "role_prompting": 1.0,
    "few_shot_examples": 0.999999985738934,
    "output_formatting": 0.999999985738934,
    "iterative_refinement": 0.999999985738934,
    "hallucination_checking": 0.999999985738934
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.25
  }
}
```

_state_after_advance_

`GET /courses/b0dafa63/learners/docs-231157/state` -> **200** (0 ms), file `docs/examples/state_after_advance.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:07.820000",
      "due_at": "2026-11-01T17:42:07.820000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.4814035218438767,
      "attempts": 4,
      "failed_rounds": 2,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "contrast"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    "... 6 more"
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "resolved",
      "evidence": 0.0,
      "clean_streak": 2
    },
    {
      "tag": "role_prompting__any_role_works_equally",
      "concept_id": "role_prompting",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-10-31T17:42:07.820000",
  "due": {
    "language_model_basics": "2026-11-01T17:42:07.820000",
    "prompt_structure": "2026-11-01T17:42:07.820000",
    "sampling_temperature": "2026-11-01T17:42:07.820000",
    "clear_instructions": "2026-10-31T17:42:07.820000",
    "few_shot_examples": "2026-11-02T17:42:07.820000",
    "output_formatting": "2026-11-02T17:42:07.820000",
    "iterative_refinement": "2026-11-02T17:42:07.820000",
    "hallucination_checking": "2026-11-02T17:42:07.820000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "... 6 more"
  ],
  "needs_help": [],
  "days_left": null,
  "gaps": [
    "context_window",
    "role_prompting"
  ],
  "retrievability": {
    "language_model_basics": 0.9486832365280501,
    "prompt_structure": 0.9486832365280501,
    "sampling_temperature": 0.9486832365280501,
    "context_window": 1.0,
    "clear_instructions": 0.8999998832693362,
    "role_prompting": 1.0,
    "few_shot_examples": 0.9654893428640662,
    "output_formatting": 0.9654893428640662,
    "iterative_refinement": 0.9654893428640662,
    "hallucination_checking": 0.9654893428640662
  },
  "pace": {
    "mastered": 8.0,
    "total": 10.0,
    "attempts_per_mastered": 1.625
  }
}
```

_state_needs_help_

`GET /courses/b0dafa63/learners/docs-231157-stuck/state` -> **200** (0 ms), file `docs/examples/state_needs_help.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "concepts": [
    {
      "concept_id": "language_model_basics",
      "p_mastery": 0.9977042871374661,
      "attempts": 4,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:08.050000",
      "due_at": "2026-11-01T17:42:08.050000",
      "lapses": 0,
      "explanations_tried": [
        "worked_example"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "prompt_structure",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:08.050000",
      "due_at": "2026-11-01T17:42:08.050000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "sampling_temperature",
      "p_mastery": 0.85,
      "attempts": 1,
      "failed_rounds": 0,
      "stability_days": 2.0,
      "last_reviewed_at": "2026-10-30T17:42:08.050000",
      "due_at": "2026-11-01T17:42:08.050000",
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "context_window",
      "p_mastery": 0.17307692307692307,
      "attempts": 19,
      "failed_rounds": 4,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example",
        "contrast",
        "analogy",
        "step_by_step"
      ],
      "fallbacks": 1,
      "needs_help": true
    },
    "... 6 more"
  ],
  "misconceptions": [
    {
      "tag": "context_window__model_remembers_everything",
      "concept_id": "context_window",
      "status": "confirmed",
      "evidence": 6.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__earlier_text_always_visible",
      "concept_id": "context_window",
      "status": "confirmed",
      "evidence": 7.0,
      "clean_streak": 0
    },
    {
      "tag": "context_window__limit_is_only_words",
      "concept_id": "context_window",
      "status": "confirmed",
      "evidence": 6.0,
      "clean_streak": 0
    }
  ],
  "next_due": "2026-11-01T17:42:08.050000",
  "due": {
    "language_model_basics": "2026-11-01T17:42:08.050000",
    "prompt_structure": "2026-11-01T17:42:08.050000",
    "sampling_temperature": "2026-11-01T17:42:08.050000",
    "clear_instructions": "2026-11-01T17:42:08.050000",
    "role_prompting": "2026-11-01T17:42:08.050000",
    "few_shot_examples": "2026-11-01T17:42:08.050000",
    "output_formatting": "2026-11-01T17:42:08.050000",
    "iterative_refinement": "2026-11-01T17:42:08.050000",
    "hallucination_checking": "2026-11-01T17:42:08.050000"
  },
  "roadmap": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "... 6 more"
  ],
  "needs_help": [
    "context_window"
  ],
  "days_left": null,
  "gaps": [
    "context_window"
  ],
  "retrievability": {
    "language_model_basics": 0.9999998663281228,
    "prompt_structure": 0.9999998663281228,
    "sampling_temperature": 0.9999998663281228,
    "context_window": 1.0,
    "clear_instructions": 0.9999998663281228,
    "role_prompting": 0.9999998663281228,
    "few_shot_examples": 0.9999998663281228,
    "output_formatting": 0.9999998663281228,
    "iterative_refinement": 0.9999998663281228,
    "hallucination_checking": 0.9999998663281228
  },
  "pace": {
    "mastered": 9.0,
    "total": 10.0,
    "attempts_per_mastered": 3.4444444444444446
  }
}
```

_state_with_deadline_

`GET /courses/c6aaba84/learners/docs-231157-deadline/state` -> **200** (0 ms), file `docs/examples/state_with_deadline.json` (shortened here: long strings and lists cut with '...'; the file is complete)

```json
{
  "concepts": [
    {
      "concept_id": "tables_rows_columns",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [
        "worked_example"
      ],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "select_columns",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "null_values",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    {
      "concept_id": "primary_keys",
      "p_mastery": 0.1774193548387097,
      "attempts": 1,
      "failed_rounds": 1,
      "stability_days": 0.0,
      "last_reviewed_at": null,
      "due_at": null,
      "lapses": 0,
      "explanations_tried": [],
      "fallbacks": 0,
      "needs_help": false
    },
    "... 6 more"
  ],
  "misconceptions": [
    {
      "tag": "tables_rows_columns__table_is_one_value",
      "concept_id": "tables_rows_columns",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "select_columns__select_changes_data",
      "concept_id": "select_columns",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "null_values__null_equals_zero",
      "concept_id": "null_values",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    {
      "tag": "primary_keys__keys_can_repeat",
      "concept_id": "primary_keys",
      "status": "suspected",
      "evidence": 1.0,
      "clean_streak": 0
    },
    "... 6 more"
  ],
  "next_due": null,
  "due": {},
  "roadmap": [
    "tables_rows_columns",
    "select_columns",
    "null_values",
    "primary_keys",
    "... 6 more"
  ],
  "needs_help": [],
  "days_left": 2,
  "gaps": [
    "tables_rows_columns",
    "select_columns",
    "null_values",
    "primary_keys",
    "... 6 more"
  ],
  "retrievability": {
    "tables_rows_columns": 1.0,
    "select_columns": 1.0,
    "null_values": 1.0,
    "primary_keys": 1.0,
    "foreign_keys": 1.0,
    "where_filtering": 1.0,
    "table_aliases": 1.0,
    "inner_join": 1.0,
    "left_join": 1.0,
    "join_multiple_tables": 1.0
  },
  "pace": {
    "mastered": 0.0,
    "total": 10.0,
    "attempts_per_mastered": 0.0
  }
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** none

**Latency:** 6 successful calls: median 0.007 s, max 0.016 s. No LLM call observed.

**Idempotency and polling:** Safe to call any time.

### `POST /courses/{cid}/learners/{lid}/advance`

Moves this learner's simulated clock forward, starts a new session, and decides the next step for the new time (without building material: no LLM call).

**When to call:** From the demo control panel ('skip ahead N days').

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body** (`AdvanceIn`):

| Field | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `days` | `number` | yes | - | Days to move the learner's simulated clock forward (must be > 0). |

Real request body:
```json
{
  "days": 1
}
```

**Response 200** (`AdvanceOut`):

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `now` | `string` | The learner's simulated now after the move. | - |
| `due_now` | `string[]` | Concepts whose review is due at that time. | empty when none |
| `next_kind` | `string | null` | Kind of the step decided for the new time (fetch it with GET .../next). | - |
| `next_concept_id` | `string | null` | Its concept. | null for session_end/done |

**Real examples:**

_advance_

`POST /courses/b0dafa63/learners/docs-231157/advance` -> **200** (16 ms), file `docs/examples/advance.json`

```json
{
  "now": "2026-10-31T17:42:07.919518",
  "due_now": [
    "clear_instructions"
  ],
  "next_kind": "review",
  "next_concept_id": "clear_instructions"
}
```

_advance_all_due_

`POST /courses/b0dafa63/learners/docs-231157-all/advance` -> **200** (0 ms), file `docs/examples/advance_all_due.json`

```json
{
  "now": "2026-11-02T17:42:08.035263",
  "due_now": [
    "language_model_basics",
    "prompt_structure",
    "sampling_temperature",
    "context_window",
    "clear_instructions",
    "role_prompting",
    "few_shot_examples",
    "output_formatting",
    "iterative_refinement",
    "hallucination_checking"
  ],
  "next_kind": "review",
  "next_concept_id": "language_model_basics"
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 422 | days <= 0 | {"detail": "days must be positive"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** clock_offset_days += days; session counter reset; stored next step replaced; previously served questions are no longer answerable. Call GET .../next to get the material.

**Latency:** 2 successful calls: median 0.008 s, max 0.016 s. No LLM call observed.

**Idempotency and polling:** Not idempotent: each call moves the clock again.

### `POST /courses/{cid}/learners/{lid}/sessions/new`

Starts a new session: resets the per-session question counter and decides the next step.

**When to call:** When the learner chooses to continue after a session_end step.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200:** no response model in the schema; live shape: `{ session_questions: number; next_kind: string; next_concept_id: string }`.

**Real examples:**

_sessions_new_

`POST /courses/b0dafa63/learners/docs-231157/sessions/new` -> **200** (0 ms), file `docs/examples/sessions_new.json`

```json
{
  "session_questions": 0,
  "next_kind": "lesson",
  "next_concept_id": "clear_instructions"
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** Session counter reset; stored next step replaced; served questions cleared. Call GET .../next.

**Latency:** 2 successful calls: median 0.000 s, max 0.000 s. No LLM call observed.

**Idempotency and polling:** Safe to repeat (each call re-decides for the same state).

### `GET /courses/{cid}/learners/{lid}/resources`

Research status and the articles and videos found for each of the learner's gap concepts. Research starts in the background when the diagnostic is graded, for gap concepts only (never for concepts placed as known), and is shared by every learner of the course. Concepts it was never started for are not listed.

**When to call:** After the diagnostic, to show 'researching...' and then the links; poll until no entry is `pending`.

**Path parameters:** `cid`, `lid`, `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200:** an object keyed by concept id; each value is a `ConceptResearch`:

| Field | Type | Meaning | Null / empty |
|---|---|---|---|
| `status` | `"pending" | "ready" | "failed"` | `pending` while research runs, then `ready` or `failed`. | - |
| `resources` | `Resource[]` | Articles and videos found (at most 2 articles and 1 video). | empty while pending and when failed |

**Real examples:**

_resources_pending_

`GET /courses/b0dafa63/learners/docs-231157-new/resources` -> **200** (16 ms), file `docs/examples/resources_pending.json`

```json
{
  "language_model_basics": {
    "status": "pending",
    "resources": []
  },
  "prompt_structure": {
    "status": "pending",
    "resources": []
  },
  "sampling_temperature": {
    "status": "pending",
    "resources": []
  },
  "context_window": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "AI Prompting (3/10): Context Windows Explained ...",
        "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/ai_prompting_310_context_windows",
        "snippet": "A context window is the amount of text an AI model can \"see\" and consider at once. Think of it like the AI's working memory - everything it can"
      },
      {
        "kind": "article",
        "title": "What is a context window? | IBM",
        "url": "https://www.ibm.com/think/topics/context-window",
        "snippet": "An LLM\u2019s context window can be thought of as the equivalent of its working memory. It determines how long of a conversation it can carry out without forgetting details from earlier in the exchange. It also determines the maximum size of documents or code samples that it can process at once. When a prompt, conversation, document or code base exceeds an artificial intelligence model\u2019s context window"
      },
      {
        "kind": "video",
        "title": "Why AI Models Forget Previous Messages ?What Is Context Length in LLMs?",
        "url": "https://www.youtube.com/watch?v=bUOfdbyCDFA",
        "snippet": "Why does ChatGPT forget past conversations? Is it really forgetting \u2014 or is something else happening? In this video, I explain ..."
      }
    ]
  },
  "clear_instructions": {
    "status": "pending",
    "resources": []
  },
  "role_prompting": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "Assigning Roles to Chatbots",
        "url": "https://learnprompting.org/docs/basics/roles",
        "snippet": "Role prompting is a technique that involves assigning a role or persona to an AI model, such as \"food critic\" or \"mathematician,\" to control the style or accuracy of its responses.\n\nBy instructing the model to take on a specific role, you can shape how it processes and delivers information. This technique is widely used across many applications, from creative writing to problem-solving.\n\n## Applic"
      },
      {
        "kind": "article",
        "title": "Does Role Prompting Work? What the Research Says",
        "url": "https://www.jdhwilkins.com/role-prompting-giving-ai-a-persona",
        "snippet": "Role prompting means giving an AI model a character, job title, or area of expertise before asking it to complete a task. A basic example:\n\n```\nYou are an experienced HR manager. Review the following job description and suggest improvements. \n```\n\nThe model has not changed. Its training data and knowledge base are no different. But the assigned persona shapes how it interprets the request and how "
      },
      {
        "kind": "video",
        "title": "Role Prompting Explained | Make ChatGPT Think Like an Expert (\u0627\u0631\u062f\u0648 + \u0939\u093f\u0902\u0926\u0940)",
        "url": "https://www.youtube.com/watch?v=xe11nwZznXo",
        "snippet": "Role prompting is the simplest way to make ChatGPT give expert-level answers. In this video, I explain role prompting from zero to ..."
      }
    ]
  },
  "few_shot_examples": {
    "status": "pending",
    "resources": []
  },
  "output_formatting": {
    "status": "pending",
    "resources": []
  },
  "iterative_refinement": {
    "status": "pending",
    "resources": []
  },
  "hallucination_checking": {
    "status": "pending",
    "resources": []
  }
}
```

_resources_after_diagnostic_

`GET /courses/b0dafa63/learners/docs-231157/resources` -> **200** (0 ms), file `docs/examples/resources_after_diagnostic.json`

```json
{
  "context_window": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "AI Prompting (3/10): Context Windows Explained ...",
        "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/ai_prompting_310_context_windows",
        "snippet": "A context window is the amount of text an AI model can \"see\" and consider at once. Think of it like the AI's working memory - everything it can"
      },
      {
        "kind": "article",
        "title": "What is a context window? | IBM",
        "url": "https://www.ibm.com/think/topics/context-window",
        "snippet": "An LLM\u2019s context window can be thought of as the equivalent of its working memory. It determines how long of a conversation it can carry out without forgetting details from earlier in the exchange. It also determines the maximum size of documents or code samples that it can process at once. When a prompt, conversation, document or code base exceeds an artificial intelligence model\u2019s context window"
      },
      {
        "kind": "video",
        "title": "Why AI Models Forget Previous Messages ?What Is Context Length in LLMs?",
        "url": "https://www.youtube.com/watch?v=bUOfdbyCDFA",
        "snippet": "Why does ChatGPT forget past conversations? Is it really forgetting \u2014 or is something else happening? In this video, I explain ..."
      }
    ]
  },
  "role_prompting": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "Assigning Roles to Chatbots",
        "url": "https://learnprompting.org/docs/basics/roles",
        "snippet": "Role prompting is a technique that involves assigning a role or persona to an AI model, such as \"food critic\" or \"mathematician,\" to control the style or accuracy of its responses.\n\nBy instructing the model to take on a specific role, you can shape how it processes and delivers information. This technique is widely used across many applications, from creative writing to problem-solving.\n\n## Applic"
      },
      {
        "kind": "article",
        "title": "Does Role Prompting Work? What the Research Says",
        "url": "https://www.jdhwilkins.com/role-prompting-giving-ai-a-persona",
        "snippet": "Role prompting means giving an AI model a character, job title, or area of expertise before asking it to complete a task. A basic example:\n\n```\nYou are an experienced HR manager. Review the following job description and suggest improvements. \n```\n\nThe model has not changed. Its training data and knowledge base are no different. But the assigned persona shapes how it interprets the request and how "
      },
      {
        "kind": "video",
        "title": "Role Prompting Explained | Make ChatGPT Think Like an Expert (\u0627\u0631\u062f\u0648 + \u0939\u093f\u0902\u0926\u0940)",
        "url": "https://www.youtube.com/watch?v=xe11nwZznXo",
        "snippet": "Role prompting is the simplest way to make ChatGPT give expert-level answers. In this video, I explain role prompting from zero to ..."
      }
    ]
  }
}
```

_resources_ready_

`GET /courses/b0dafa63/learners/docs-231157/resources` -> **200** (16 ms), file `docs/examples/resources_ready.json`

```json
{
  "context_window": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "AI Prompting (3/10): Context Windows Explained ...",
        "url": "https://www.reddit.com/r/PromptEngineering/comments/1iftklk/ai_prompting_310_context_windows",
        "snippet": "A context window is the amount of text an AI model can \"see\" and consider at once. Think of it like the AI's working memory - everything it can"
      },
      {
        "kind": "article",
        "title": "What is a context window? | IBM",
        "url": "https://www.ibm.com/think/topics/context-window",
        "snippet": "An LLM\u2019s context window can be thought of as the equivalent of its working memory. It determines how long of a conversation it can carry out without forgetting details from earlier in the exchange. It also determines the maximum size of documents or code samples that it can process at once. When a prompt, conversation, document or code base exceeds an artificial intelligence model\u2019s context window"
      },
      {
        "kind": "video",
        "title": "Why AI Models Forget Previous Messages ?What Is Context Length in LLMs?",
        "url": "https://www.youtube.com/watch?v=bUOfdbyCDFA",
        "snippet": "Why does ChatGPT forget past conversations? Is it really forgetting \u2014 or is something else happening? In this video, I explain ..."
      }
    ]
  },
  "role_prompting": {
    "status": "ready",
    "resources": [
      {
        "kind": "article",
        "title": "Assigning Roles to Chatbots",
        "url": "https://learnprompting.org/docs/basics/roles",
        "snippet": "Role prompting is a technique that involves assigning a role or persona to an AI model, such as \"food critic\" or \"mathematician,\" to control the style or accuracy of its responses.\n\nBy instructing the model to take on a specific role, you can shape how it processes and delivers information. This technique is widely used across many applications, from creative writing to problem-solving.\n\n## Applic"
      },
      {
        "kind": "article",
        "title": "Does Role Prompting Work? What the Research Says",
        "url": "https://www.jdhwilkins.com/role-prompting-giving-ai-a-persona",
        "snippet": "Role prompting means giving an AI model a character, job title, or area of expertise before asking it to complete a task. A basic example:\n\n```\nYou are an experienced HR manager. Review the following job description and suggest improvements. \n```\n\nThe model has not changed. Its training data and knowledge base are no different. But the assigned persona shapes how it interprets the request and how "
      },
      {
        "kind": "video",
        "title": "Role Prompting Explained | Make ChatGPT Think Like an Expert (\u0627\u0631\u062f\u0648 + \u0939\u093f\u0902\u0926\u0940)",
        "url": "https://www.youtube.com/watch?v=xe11nwZznXo",
        "snippet": "Role prompting is the simplest way to make ChatGPT give expert-level answers. In this video, I explain role prompting from zero to ..."
      }
    ]
  }
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | learner not started | {"detail": "learner 'docs-231157' has not started course 'b0dafa63'"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** none

**Latency:** 3 successful calls: median 0.016 s, max 0.016 s. Never waits for the LLM: course generation and research run in the background.

**Idempotency and polling:** Safe to poll every 3 to 5 s; entries go from `pending` to `ready` or `failed` and then stay.

### `GET /eval/results`

Serves the offline evaluation results file if one has been produced, else 404.

**When to call:** Optional 'how well does the brain work' page.

**Path parameters:** `x-master-password` (strings; `lid` is any id the client picks).

**Request body:** none.

**Response 200:** no response model in the schema; live shape: `not captured`.

**Real examples:**

_eval_results_

`GET /eval/results` -> **404** (0 ms), file `docs/examples/eval_results.json`

```json
{
  "detail": "no eval results yet"
}
```

**Errors:**

| Status | When | Body |
|---|---|---|
| 404 | no results file yet | {"detail": "no eval results yet"} |
| 401 | missing or wrong password | {"detail": "missing or wrong master password"} |

**Side effects:** none

**Latency:** not measured (no successful call)

**Idempotency and polling:** Safe to call.

## 5. Behaviour the frontend must know

**Datetimes.** Verified on 130 datetime values in this run: none carry a zone. They are naive UTC ISO strings without a trailing `Z` (e.g. `2026-10-30T17:42:07.820000`). Append `Z` before parsing:

```ts
const parseUtc = (s: string | null) => (s ? new Date(s.endsWith('Z') ? s : s + 'Z') : null);
```
Send datetimes (e.g. `deadline`) as UTC ISO; a `Z` is accepted.

**Questions.** Before grading, every question has exactly the keys ['concept_id', 'id', 'options', 'prompt'] (options are plain strings: verified). `correct_indices` and `explanations` only appear in the attempts response, after grading.

**Confidence** is optional: in this run an answer without `confidence` was accepted (yes). Allowed: `low`, `medium`, `high`.

**Step kinds** (seen live in this run: done, fallback, lesson, lesson (give_up_after), review, session_end):

| kind | Render |
|---|---|
| `lesson` | The lesson text, then its 3 questions. If `give_up_after` is true, say it is the last try on this concept. |
| `review` | A 'quick review' card for `concept_id` with its 2 questions; no lesson. |
| `fallback` | A lesson on a prerequisite (`concept_id`) because the learner is stuck on `target_concept`; say so. |
| `session_end` | 'Good session' screen; offer 'continue' (POST .../sessions/new then GET .../next). No questions. |
| `done` | 'All caught up' screen. Reviews come back as time passes (advance in the demo). |

**Diagnostic.** `start` returns one question per concept in roadmap order. Submitting it places every concept answered right at mastery 0.85 with a re-check review 1 (low or no confidence), 2 (medium) or 3 (high) days later, and adds the message `Placed N concepts as already known; I'll check them again tomorrow|within D days.` The step's `reason` starts with `placed as known: ...`. The diagnostic does not count toward the session cap.

**Stuck learners.** After 3 failed rounds on a concept the brain detours once to a prerequisite (`fallback`), then gives a last try (`lesson` with `give_up_after: true`); failing that sets `needs_help` for the concept and the message '... is flagged for help ...'. Observed in this run for `context_window`: done, fallback, lesson, lesson_give_up, session_end.

**Session cap.** The step becomes `session_end` after the session's questions reach the cap (observed after 15 questions answered in the session). `advance` and `sessions/new` reset the counter.

**reason** is a human-readable sentence built from facts (e.g. due date and recall, confirmed misconceptions, relearning after a lapse). Show it as 'why this step'. Do not parse it.

**Messages** (show as toasts). Every template, with what triggers it and whether this run produced it:

| Template | Trigger | Seen in this run |
|---|---|---|
| `You mastered {concept} (mastery {p}).` | a concept crossed 0.85 in this round | no |
| `You slipped on {concept}. This happens, it is why reviews exist.` | a mastered concept was answered wrong (a lapse) | yes: `You slipped on clear_instructions. This happens, it is why reviews exist.` |
| `Review of {concept} passed: next one in {n} days.` | a due review was answered all right | no |
| `{concept} is flagged for help: it may need a different resource or a person.` | the last try on a stuck concept failed | yes: `context_window is flagged for help: it may need a different resource or a person.` |
| `Misconception {tag} resolved.` | 2 clean answers in a row on questions testing a confirmed misconception (not in a round where it was picked) | yes: `Misconception context_window__model_remembers_everything resolved.` |
| `3 correct in a row.` | 3 consecutive right answers within this round | yes: `3 correct in a row.` |
| `{n} day(s) left before your deadline.` | days_left is between 0 and 3 | yes: `2 days left before your deadline.` |
| `Placed {n} concepts as already known; I'll check them again tomorrow \| within {d} days.` | diagnostic answers that were right (placement) | yes: `Placed 8 concepts as already known; I'll check them again within 3 days.` |
| `every reachable concept is mastered[; needs help: ...]` | the next step is done (the reason is copied into messages) | yes: `every reachable concept is mastered` |
| `{n} questions this session; start a new session to continue` | the next step is session_end | yes: `15 questions this session; start a new session to continue` |

**Lessons and latency.** A lesson is written by the LLM the first time a (concept, misconception targets, styles tried) combination is needed, then cached. Measured: responses that generated a lesson took 3.2 to 3.2 s (measured in an earlier run of this script (2026-10-30 23:08)); with a cached lesson 0.20 s or less. 
Show a loading state on attempts and GET .../next.

**Course generation.** Measured in an earlier run of this script (2026-10-30 22:28): `generating` for 142 s (71 polls), ending `ready`. Poll every 2 s; allow up to about 3 minutes; on `failed` offer to retry with POST /courses.

**Simulated time.** Each learner has a private clock offset. `POST .../advance {days}` adds to it, resets the session, and decides the next step for the new time; `due_now` lists due concepts. All `now`, `due` and `retrievability` values use the learner's simulated now.

**Research.** When the diagnostic is graded, research starts in the background for the gap concepts only (observed: 2 concepts listed right after the diagnostic, statuses ['ready']; after 0 s of polling: ['ready']). Requests never wait for it. Lessons written after research is ready are grounded in the sources; `lesson.resources` carries them, and GET .../next fills them in for a lesson built earlier. Research results are shared by every learner of the course.

**Placed vs verified.** The API does not expose whether a mastered concept was placed or verified by a review.

## 6. Enumerations

| Name | Values | Meaning |
|---|---|---|
| `level` | `novice`, `beginner`, `intermediate`, `advanced` | Self-assessed level (questions and lessons adapt). |
| course `status` | `generating`, `ready`, `failed` | Background generation state. |
| `Step.kind` | `lesson`, `review`, `fallback`, `session_end`, `done` | See section 5. |
| `confidence` | `low`, `medium`, `high` | Optional self-report per answer. |
| misconception `status` | `suspected`, `confirmed`, `resolved` | 1 evidence = suspected, 2 = confirmed, 2 clean answers = resolved; can come back. |
| `Lesson.style` | `worked_example`, `contrast`, `analogy`, `step_by_step` | Explanation style; a new one is tried each time. |
| `Resource.kind` | `article`, `video` | Research results (not wired yet). |

## 7. Planned, not implemented yet

**NOT AVAILABLE**: these returned the status shown in this run. Code against them behind feature detection (treat 404 as 'feature off').

| Route | Status now |
|---|---|
| `POST .../learners/{lid}/virtual/start` | 404 |
| `POST .../learners/{lid}/virtual/pause` | 404 |
| `POST .../learners/{lid}/virtual/resume` | 404 |
| `POST .../learners/{lid}/virtual/stop` | 404 |
| `POST .../learners/{lid}/virtual/speed` | 404 |
| `GET .../learners/{lid}/virtual/status` | 404 |
| `GET .../learners/{lid}/virtual/events?after=0` | 404 |

Contracts:

```text
POST .../virtual/start {persona, speed, days, reset}
POST .../virtual/pause | .../virtual/resume | .../virtual/stop
POST .../virtual/speed {speed}
GET  .../virtual/status
GET  .../virtual/events?after=N -> {events: [{n, at, kind, text, source}], next}
```

`GET .../state` has no `history` or `learning_rate` field yet (checked on the live response); treat them as optional when they arrive.

## 8. Quick start

```bash
BASE=http://127.0.0.1:8000
PW='<your-master-password>'
curl -s $BASE/health
curl -s -X POST $BASE/courses -H "X-Master-Password: $PW" -H 'Content-Type: application/json' -d '{"prompt": "prompt engineering", "level": "beginner"}'
curl -s $BASE/courses/$CID -H "X-Master-Password: $PW"          # poll until status is ready
curl -s -X POST $BASE/courses/$CID/learners/me/start -H "X-Master-Password: $PW"
curl -s -X POST $BASE/courses/$CID/learners/me/attempts -H "X-Master-Password: $PW" -H 'Content-Type: application/json' -d '{"answers": [{"question_id": "<id>", "chosen_index": 1, "confidence": "medium"}]}'
```

Five likely mistakes:

1. Parsing datetimes without appending `Z` (they are UTC but carry no zone).
2. Forgetting `X-Master-Password` (401) or expecting it on `/health`.
3. Calling `start` before the course is `ready` (409) instead of polling `GET /courses/{cid}`.
4. Looking for the next step in the wrong place: it is `next` in the attempts response, or `GET .../next` after `advance`/`sessions/new`/reload. Only the questions served there (or by `start`) are accepted.
5. Always sending `confidence`: it is optional; send it only when the learner picked one.

## 9. Changelog / how to regenerate

Generated 2026-10-30 23:12 from commit `11b8da9` with uncommitted changes. Regenerate (MongoDB running, port 8000 free, run in `backend/`):

```bash
uv run python scripts/gen_api_docs.py
```

## 10. Quirks and open questions

- A lesson built before its concept's research is ready comes with `resources: []`; GET .../next returns the same lesson with the resources once research is ready.
- `pace.mastered` and `pace.total` are counts but are sent as floats (e.g. 4.0), because `pace` is typed dict[str, float].
- Datetimes: 130 values, fraction digits seen [6]; 128 of them end in '000' (values stored in MongoDB keep only milliseconds). Open question: Python omits the fraction entirely when the microseconds are 0 (not observed here), so parse with a lenient ISO parser.
- POST .../sessions/new has no response model in the OpenAPI schema (a plain object); its shape below is taken from the live response.
