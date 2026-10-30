# OnlyNerd: how the API flow works (for the frontend)

Read this first. Then use `docs/API_REFERENCE.md` (every field), `docs/types.ts` (types), `docs/examples/`
(real responses, so you can build against mocks) and `docs/api.http` (try calls).

## 1. The idea in one minute

A learner types a topic and picks a level. The backend builds a course: a graph of 8 to 12 concepts
and 7 multiple-choice questions per concept. The learner takes a short **diagnostic** (one question per
concept). The backend works out what they already know and what they don't (the **gaps**), then teaches
the gaps one at a time with a short lesson and practice questions. Mastery updates after every answer.
Concepts the learner knew are **reviewed again** after a delay, because memory fades. A control panel
can move a simulated clock forward so you can watch the fading and the reviews happen.

**The frontend never decides what comes next.** The backend always tells you ("next step"). Your job is
to render what it says and send answers back.

## 2. Setup facts

| Thing | Value |
|---|---|
| Base URL | `http://localhost:8000` (start it: `cd backend && uv run uvicorn main:app --reload`; MongoDB must be running) |
| Auth | One shared password in the header `X-Master-Password` on every request except `GET /health`. A wrong or missing password gives **401**. |
| CORS | The backend allows `http://localhost:3000` and the `X-Master-Password` header. |
| Ids | `course_id` comes from the backend. `learner_id` is any string you choose (use `"demo"`). |
| Datetimes | ISO strings **without a trailing `Z`**, in UTC. **Append `Z` before `new Date(...)`**, or the browser reads them as local time and everything is off by hours. |
| Mastery | A number from 0 to 1. **0.85 or more means mastered.** |

## 3. The screens, as a state machine

```
 SETUP ──create──▶ BUILDING ──ready──▶ DIAGNOSTIC ──submit──▶ FEEDBACK ──▶ NEXT STEP
                      ▲                                                       │
                      │ (poll every 2 s, up to ~3 min)                        ▼
                                              ┌─────────────── lesson / fallback ──▶ PRACTICE ──submit──▶ FEEDBACK
                                              ├─────────────── review ─────────────▶ REVIEW QUESTIONS ──submit──▶ FEEDBACK
                                              ├─────────────── session_end ────────▶ "Come back tomorrow" ──▶ new session
                                              └─────────────── done ───────────────▶ "Everything covered"
```

## 4. The flow, call by call

### Step 1. Setup: create the course

`POST /courses`
```json
{ "prompt": "prompt engineering", "level": "beginner", "deadline": "2026-11-15T00:00:00" }
```
`level` is one of `novice`, `beginner`, `intermediate`, `advanced`. `deadline` is optional.

Response: `{ course_id, status, topic, concepts }`.
- If the course already exists for that topic and level, `status` is `"ready"` straight away.
- Otherwise `status` is `"generating"`. This takes **1 to 3 minutes**. Show "Building your course...".

### Step 2. Wait for it

`GET /courses/{course_id}` every **2 seconds** until `status` is `"ready"` (or `"failed"`: show an error and let
the user try again). Stop polling once it's ready. A ready response includes the `concepts`
(`id`, `name`, `prerequisites`) that you can use for a graph or sidebar.

### Step 3. Start the learner

`POST /courses/{course_id}/learners/{learner_id}/start` (no body)

Response: `{ questions: QuestionPublic[] }`: **one question per concept**, the diagnostic.
```ts
type QuestionPublic = { id: string; concept_id: string; prompt: string; options: string[] }  // 4 options
```
There is no `correct_index` here. The backend never reveals answers before grading.
Calling `start` twice for the same learner returns **409**.

### Step 4. Take the diagnostic

Show the questions one at a time (or all together). For each, collect the chosen option **index (0 to 3)** and
a **confidence** (`"low" | "medium" | "high"`, a three-button selector: "Not sure", "Fairly sure",
"Certain"). Confidence is optional, but it makes the system smarter: it affects how fast a misconception
is detected and how soon a review comes back. Send **all diagnostic answers in one request**:

`POST /courses/{course_id}/learners/{learner_id}/attempts`
```json
{ "answers": [ { "question_id": "...", "chosen_index": 1, "confidence": "medium" }, "..." ] }
```

Response (`AttemptResultOut`), the important fields:

| Field | What it is | What to render |
|---|---|---|
| `graded` | per answer: `question_id`, `concept_id`, `correct`, `chosen_tag`, `confidence` | right/wrong marks |
| `correct_indices` | `{ question_id: index }`, safe to show now | highlight the correct option |
| `explanations` | `{ question_id: text }` | "why" text under each question |
| `mastery` | `{ concept_id: 0..1 }` for every concept | sidebar bars |
| `new_confirmed_misconceptions` | tags of misconceptions just confirmed | "You may think..." chips |
| `messages` | encouragement strings | a highlighted box |
| `next` | the next step (see step 5) | the next screen |

**What happens to the diagnostic answers:** concepts answered correctly are **placed as known** (set to mastered,
with a verification review scheduled 1, 2 or 3 days out for low, medium or high confidence). Concepts answered
wrongly stay as gaps. You'll see a message like *"Placed 9 concepts as already known; I'll check them again
within 3 days."* Show it. It explains why the learner skips most lessons.

### Step 5. The next step

The attempts response contains `next`, and the same thing is available any time from:

`GET /courses/{course_id}/learners/{learner_id}/next`

It is **idempotent**: call it again (for example after a page reload) and you get the same lesson and the
same questions. It returns **409** only before the diagnostic.

```ts
type StepOut = {
  step: { kind: 'lesson'|'review'|'fallback'|'session_end'|'done';
          concept_id: string|null; target_misconceptions: string[]; give_up_after: boolean; ... }
  reason: string                 // plain-language "why this?", show it
  lesson: { concept_id; style; explanation; targets: string[]; resources: Resource[] } | null
  questions: QuestionPublic[]
}
```

| `step.kind` | Render |
|---|---|
| `lesson` | The lesson text (`lesson.explanation`, plain prose), the targeted misconceptions as chips, `lesson.resources` as links if any (it is empty until research is wired), then the `questions` (3 practice questions). |
| `fallback` | Same as `lesson`, but for a prerequisite: say "Let's go back to a building block first". |
| `review` | Heading "Time to review", the concept name, and the `questions` (2). There is no lesson. |
| `session_end` | "Great session. Come back tomorrow." plus a button that calls `POST .../sessions/new`. |
| `done` | "You've covered everything. Reviews will return as you start to forget." |

Also show `reason` as a small "Why this?" line. If `give_up_after` is true, it is the last try at a concept the
learner keeps failing: be encouraging.

**`lesson` can be `null`** on a lesson step if generation failed once. Call `GET .../next` again and it retries.

### Step 6. Practice and review: the loop

Answer the questions in `next.questions` exactly as in step 4 and send them to
`POST .../attempts` again. **Only submit question ids that you were given.** Anything else returns **422**.
Each submission is one "round". The response has the same shape as before (grading, mastery, messages,
and a new `next`), so the loop is always: **render `next`, collect answers, POST attempts, repeat.**

What the learner will experience:
- A concept reaches mastery (0.85 or more) after about three correct answers in a row.
- A wrong answer on a **mastered** concept is a "lapse": mastery drops and the learner gets a lesson on it
  again right away (a "relearn", the `reason` says so). The message says *"You slipped on X. This happens, it
  is why reviews exist."*
- After 15 questions in a session, the step becomes `session_end`.

### Step 7. Time passes

Tomorrow the learner returns, or a judge presses a clock button in the control panel.

`POST .../advance` with `{ "days": 3 }` (`days` must be greater than 0)

Response: `{ now, due_now, next_kind, next_concept_id }`. `now` is the learner's **simulated** date. `due_now`
lists the concepts due for review. **After `advance` you must call `GET .../next` before submitting any
answers**, because the old questions are no longer valid (an old id returns 422).

### Anytime: the state

`GET .../state` (poll it **every second** in the control panel, or after each attempt in the learner app). It gives you:

| Field | Meaning |
|---|---|
| `concepts[]` | per concept: `p_mastery`, `attempts`, `failed_rounds`, `stability_days`, `due_at`, `lapses`, `needs_help` ... |
| `misconceptions[]` | `tag`, `status` (suspected / confirmed / resolved), `evidence` |
| `gaps` | concepts not yet mastered, in roadmap order |
| `retrievability` | `{ concept_id: 0..1 }`, how likely the learner remembers it right now (the forgetting curve) |
| `due` | `{ concept_id: due time }` for reviews |
| `roadmap` | concept ids in prerequisite order |
| `needs_help` | concepts the learner keeps failing |
| `pace` | `{ mastered, total, attempts_per_mastered }` (numbers, even whole ones arrive as floats) |
| `days_left` | days to the deadline, or `null` |
| `now`, `history`, `learning_rate`, `avg_stability_days`, `stability` | for the control panel; may be missing until the backend update lands, so treat them as optional |

## 5. The control panel flow

The panel is a second window (`/control`) that watches the same learner. It stores `course_id`, `learner_id`
and the password in `localStorage`, so both windows share them. Every second it calls `GET .../state`. The
buttons it needs:

| Button | Call |
|---|---|
| +1 / +3 / +7 / +30 days | `POST .../advance` |
| New session | `POST .../sessions/new` |
| Create demo course | `POST /courses`, then poll, then `POST .../start` |

After a clock jump the memory bars (retrievability) visibly drop and reviews become due. That is the whole
demo: learn, jump time, watch it fade, review it.

## 6. Loading states (measured)

| What | How long | UI |
|---|---|---|
| Course build (new topic) | 1 to 3 minutes | "Building your course..." and a poll every 2 s |
| Course for a topic that already exists | instant | none |
| First lesson of a step | about 5 to 10 seconds | spinner, disable buttons |
| Everything else | under a second | none |

## 7. Errors

| Status | Meaning | What to do |
|---|---|---|
| 401 | Wrong or missing password | send the user back to the password field |
| 404 | Unknown course or learner | check the ids |
| 409 | `start` called twice, `next` before the diagnostic, or the course is not ready | read `detail` and show it |
| 422 | Bad input: an unserved question id, a bad option index, or `days` of 0 or less | read `detail`, fix the request |

Errors look like `{ "detail": "..." }`.

## 8. Minimal main loop (TypeScript sketch)

```ts
const H = { 'Content-Type': 'application/json', 'X-Master-Password': password }
const api = (path: string, init?: RequestInit) =>
  fetch(`${BASE}${path}`, { ...init, headers: H }).then(async r => {
    if (!r.ok) throw Object.assign(new Error((await r.json()).detail ?? r.statusText), { status: r.status })
    return r.json()
  })
const utc = (s: string) => new Date(s.endsWith('Z') ? s : s + 'Z')   // naive UTC strings

// 1. setup
let c = await api('/courses', { method: 'POST', body: JSON.stringify({ prompt, level }) })
while (c.status === 'generating') { await sleep(2000); c = await api(`/courses/${c.course_id}`) }
if (c.status !== 'ready') throw new Error('Course failed')

// 2. diagnostic
const base = `/courses/${c.course_id}/learners/${learnerId}`
let { questions } = await api(`${base}/start`, { method: 'POST' })

// 3. loop: render, collect, submit, repeat
while (true) {
  const answers = await askUser(questions)   // [{ question_id, chosen_index, confidence }]
  const result = await api(`${base}/attempts`, { method: 'POST', body: JSON.stringify({ answers }) })
  showFeedback(result)                       // graded, correct_indices, explanations, messages
  const next = result.next                   // StepOut
  if (next.step.kind === 'done' || next.step.kind === 'session_end') break
  showStep(next)                             // lesson / review
  questions = next.questions
}
```

## 9. Common mistakes

1. Forgetting the `X-Master-Password` header: you get 401 on every call.
2. Parsing datetimes without adding `Z`.
3. Polling the course forever: stop at `ready` or `failed`.
4. Submitting answers after `advance` without calling `GET .../next` first (422).
5. Not sending `confidence`: it still works, but misconceptions are detected more slowly.
6. Computing "what next" yourself: always render the `next` the backend returns.
7. Treating `lesson: null` as final: call `GET .../next` again.

## 10. Not available yet (code against it behind feature detection)

- `GET .../resources`: articles and videos found by the research agent (until then `lesson.resources` is `[]`).
- The virtual student: `POST .../virtual/start | pause | resume | stop | speed`, `GET .../virtual/status`,
  `GET .../virtual/events?after=N`. These return 404 until they exist. Treat a 404 as "not available".
- `history`, `learning_rate`, `avg_stability_days`, `stability`, `now` on `/state`: optional for now.
