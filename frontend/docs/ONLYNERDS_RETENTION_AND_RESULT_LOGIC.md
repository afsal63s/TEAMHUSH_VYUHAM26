# OnlyNerds: Retention Screen and Assessment Result Logic

**Purpose:** Frontend implementation notes for the OnlyNerds Retention page, assessment results, mastery calculations, review scheduling, and edge-case handling.

**Backend reference used:** `API_REFERENCE.md` generated from a live run on 2026-10-30, plus `Adaptive Learning Agent Backend Guide.md` for the learning model. The live API reference is the source of truth for currently implemented routes and response fields. The Backend Guide describes the intended internal algorithm and may contain older or more detailed design notes.

> Important: The frontend displays and formats the backend's learning estimates. It must not reimplement BKT, update mastery itself, invent assessment history, or pretend an unavailable endpoint exists.

---

## 1. What the Retention page should contain

The Retention page should be a **course-specific view of memory and review status**, not just another quiz score dashboard.

### Recommended page layout

#### A. Retention overview

Show:
- Mastered concepts: `pace.mastered` out of `pace.total`.
- Mastery coverage: `pace.mastered / pace.total * 100`.
- Earliest scheduled review: `next_due`.
- Number of due/overdue concepts: count the entries in `due` whose scheduled timestamps have passed relative to the learner's current clock.

Use `pace.mastered` and `pace.total` when available. If computing the percentage yourself, guard against `pace.total === 0` and show `--` / "No mastery data" instead of dividing by zero.

**Label carefully:** mastery coverage means the share of concepts currently at or above the backend's mastery threshold. It is not the learner's average quiz score and not a measured retention accuracy percentage.

#### B. Concept mastery list

For every course concept, show:
- Concept name.
- Mastery probability: `p_mastery * 100`.
- Mastered / Developing status.
- Attempts: `attempts`.
- Next review date: `due_at`, when present.
- Memory stability: `stability_days`.
- Lapses: `lapses`.
- Help status: `needs_help`.

The learner state contains concept IDs, not display names. Join `state.concepts[].concept_id` to `GET /courses/{cid}` → `concepts[].id/name` before rendering names.

#### C. Recall strength / retrievability

Use `state.retrievability[concept_id]` as the source for the recall-strength bar or indicator.

The backend defines retrievability as an estimated probability of recalling a mastered concept now. It is **not** a quiz result.

Important edge case: the API documentation says retrievability is `1.0` for concepts that have never been mastered. Do not display that as "100% remembered". For concepts with `p_mastery < 0.85`, or with no established review stability, label recall strength as "Not established" / "Not yet mastered" rather than 100% retention.

Do not independently recompute retrievability in the frontend. The API already returns it and the backend uses a simulated learner clock.

#### D. Review schedule

Use:
- `next_due`: earliest scheduled review.
- `due`: map of `concept_id -> scheduled review timestamp`.
- `ConceptState.due_at`: per-concept next review timestamp.

Display separate states:
- **Not scheduled:** `due_at` is null.
- **Upcoming:** due time is in the future.
- **Due now:** due time is at or before the learner's current time.
- **Overdue:** due time is earlier than the learner's current time.

The API's `due` field includes scheduled review timestamps; its documentation says past timestamps are due now. Do not equate a concept with `due_at: null` to an overdue concept. A null date means no review is scheduled in the returned state.

#### E. Misconception tracker

Use `state.misconceptions[]` and group by `status`:
- `suspected`
- `confirmed`
- `resolved`

For each item show its concept name, status, `evidence`, and `clean_streak` if useful.

The `tag` is an identifier shaped like `<concept_id>__<slug>`, not a user-friendly explanation. Do not display raw tags as if they were natural-language descriptions. Resolve the concept name from the course graph and use a generic label such as "Misconception detected" unless the frontend has a safe, explicit label mapping.

#### F. Needs-help concepts

Show concepts where either:
- `ConceptState.needs_help === true`, or
- the concept ID is present in the top-level `needs_help[]` list.

Offer a route back into the agent's normal learning flow. Do not invent a "get help" API endpoint if one is not in the live API reference.

#### G. Optional: attempts per mastered concept

Display `pace.attempts_per_mastered` as an efficiency/pace metric, for example "2.1 questions per mastered concept".

If there are zero mastered concepts, show `--` rather than `Infinity`, `NaN`, or zero. Do not describe this as time spent; the backend documentation says pace and time spent were dropped from the schemas because nothing used them.

---

## 2. Existing endpoints used by the Retention page

All paths below are relative to the configured backend base URL.

### Course metadata and display names

```http
GET /courses/{cid}
```

Use `concepts[].id`, `concepts[].name`, and prerequisites to map learner-state concept IDs to readable labels.

### Learner retention state

```http
GET /courses/{cid}/learners/{lid}/state
```

This is the primary Retention page endpoint. It returns concepts, misconceptions, `next_due`, `due`, `roadmap`, `needs_help`, `gaps`, `retrievability`, `pace`, and deadline information.

Call it:
- When opening the Retention page.
- After every submitted assessment round.
- After a clock advance in a demo/control panel.
- When returning to the page after a learning session.

### Ask the adaptive agent for the next step

```http
GET /courses/{cid}/learners/{lid}/next
```

Use this when the learner chooses to continue/catch up or when a page reload loses the current step. The backend chooses the next step. The frontend must render the returned `step.kind` and `step.concept_id`; it cannot force a specific overdue concept using this endpoint.

### Submit diagnostic, practice, or review answers

```http
POST /courses/{cid}/learners/{lid}/attempts
```

All these answer rounds use the same submission endpoint. The response includes `graded`, `correct_indices`, `explanations`, `mastery`, `new_confirmed_misconceptions`, `messages`, and `next`.

### Demo-only clock advance

```http
POST /courses/{cid}/learners/{lid}/advance
Content-Type: application/json

{"days": 1}
```

This moves the learner's **simulated clock** forward, starts a new session, and decides the next step for the new time. It is for a demo/control-panel scenario, not a normal "catch up" button and not a way to take a specific future review early.

After advancing, fetch `GET .../next` and refresh `GET .../state`.

---

## 3. The backend's mastery and forgetting model

### 3.1 Per-concept mastery

`p_mastery` is a probability from `0` to `1` representing the backend's estimate that a learner knows a concept.

The documented mastery threshold is:

```text
p_mastery >= 0.85  => mastered
p_mastery <  0.85  => not yet mastered
```

Frontend display conversion:

```js
const masteryPercent = Math.round(concept.p_mastery * 100);
const isMastered = concept.p_mastery >= 0.85;
```

Use the backend value. Do not calculate a replacement BKT score from right/wrong answers in React.

### 3.2 Overall mastery coverage

Recommended headline metric:

```text
masteryCoverage = pace.mastered / pace.total * 100
```

Example: if 7 of 10 concepts are mastered, mastery coverage is 70%.

This is a count of mastered concepts, not the mean of all `p_mastery` values. Keep the label explicit, such as **Concepts mastered** or **Mastery coverage**.

If the UI also wants the mean estimated mastery across concepts, that is a separate frontend-derived statistic:

```text
meanEstimatedMastery = average(concepts[].p_mastery) * 100
```

Only show it with a clear label such as **Average estimated mastery**. Do not call it quiz accuracy or retention accuracy. The API does not define this as an official course-level score, and a simple mean gives every concept equal weight.

### 3.3 Retrievability

The Backend Guide and API reference describe the agent's forgetting curve as:

```text
retrievability = 0.9 ^ (days_since_review / stability_days)
```

Interpretation:
- `stability_days` is the number of days until estimated recall falls to 90%.
- A review is due when retrievability reaches 0.9, which occurs at approximately `days_since_review = stability_days` under this curve.
- The live API returns `retrievability` already calculated. Prefer this returned value over frontend recomputation.

**Never divide by `stability_days` in the UI when it is zero or absent.** Never treat the API's `1.0` sentinel for never-mastered concepts as perfect memory.

### 3.4 Stability after reviews: documentation discrepancy

There is a difference between the two supplied documents:
- The live `API_REFERENCE.md` glossary says a passed review multiplies stability by **2.5**, while a lapse halves it, with a minimum of 1 day.
- The older Backend Guide describes stability update as `1 + 1.5 x score` after a correct review.

Because the live API reference is generated from a tested server run, treat returned `stability_days` and `due_at` as authoritative. **Do not implement either multiplier in the frontend.** Ask the backend teammate to confirm the current internal rule before documenting the exact multiplier in user-facing copy or duplicating it in tests.

### 3.5 Lapses

A lapse is a failed review of a concept that had been mastered. The API exposes the `lapses` count per concept. The Backend Guide says a lapse halves stability and resets mastery to 0.5; the live API reference confirms the stability reduction but the frontend should not assume a specific mastery reset value.

After a review submission:
1. Read the `/attempts` response.
2. Refresh `/state`.
3. Display the backend's new `p_mastery`, `stability_days`, `lapses`, `due_at`, and `retrievability`.
4. Do not manually change any of those values in the frontend.

---

## 4. How to calculate an individual assessment result

The `/attempts` response returns one `graded[]` item for each submitted answer. It does not itself provide a final percentage field.

The frontend can calculate the visible quiz result from the question set it displayed and the `graded[]` response.

### 4.1 Core counters

```js
const totalQuestions = questionsShown.length;
const answeredCount = result.graded.length;
const correctCount = result.graded.filter(item => item.correct).length;
const incorrectCount = answeredCount - correctCount;
const skippedCount = totalQuestions - answeredCount;
```

This assumes each displayed question is submitted at most once and skipped questions are not sent as answers. Keep the original displayed question list until the response is processed so skipped count can be calculated accurately.

### 4.2 Which percentage should be shown?

There are two valid but different calculations:

```text
Answered accuracy = correctCount / answeredCount * 100
Whole-quiz score  = correctCount / totalQuestions * 100
```

Recommended results display:
- Show **correct / total questions** as the headline score if skipped questions count as not correct. Example: 7 correct out of 10 total = 70%.
- Also show correct, incorrect, and skipped counts separately.
- Optionally show **accuracy on answered questions** separately. Example: 7 correct out of 9 answered = 77.8%.
- If `answeredCount === 0`, show "No answers submitted" and no answered-accuracy percentage.
- If `totalQuestions === 0`, show an empty/error state rather than divide by zero.

Never silently switch between the two percentage formulas across diagnostic, practice, and review result pages.

### 4.3 Per-concept results for the current quiz

Each question has a `concept_id`, and each graded answer returns a `concept_id`.

For the current round only, group the displayed questions and graded answers by `concept_id`:

```text
correct_for_concept = count(graded where concept_id matches and correct === true)
answered_for_concept = count(graded where concept_id matches)
shown_for_concept = count(displayed questions where concept_id matches)
```

Show a ratio like `1 / 2 correct` when more than one question was shown for a concept. If the diagnostic supplies only one question per concept, use simple labels such as **Correct**, **Needs strengthening**, or **Skipped** instead of implying that a single item is a statistically reliable topic percentage.

For the long-term Retention page, use `state.concepts[].p_mastery`, not the latest quiz's raw percentage.

### 4.4 Confidence insights

The backend accepts one optional `confidence` value for each submitted answer: `low`, `medium`, or `high`. The UI can label these as:

| UI label | API value |
|---|---|
| Not sure | `low` |
| Fairly sure | `medium` |
| Certain | `high` |

Confidence belongs to the learner's selected answer for the question. It is **one confidence value per question**, not a confidence value for every answer option. The question UI should let the learner choose an option and then choose how confident they are about that chosen answer. Confidence is optional; do not invent a confidence value when the learner leaves it blank.

For the current assessment result, calculate:

```js
const certainButWrong = graded.filter(
  answer => answer.confidence === "high" && !answer.correct
).length;

const unsureButRight = graded.filter(
  answer => answer.confidence === "low" && answer.correct
).length;

const fairlySureButWrong = graded.filter(
  answer => answer.confidence === "medium" && !answer.correct
).length;
```

Interpretation:
- **Certain, but wrong:** a high-confidence wrong answer is stronger evidence for a misconception in the backend. The guide says it adds 2 misconception-evidence points rather than 1.
- **Unsure, but right:** a low-confidence correct answer may be a guess. The guide describes using `p_guess = 0.5` for that update.
- **Fairly sure, but wrong:** show as a normal wrong answer with medium confidence; do not assign the stronger high-confidence evidence weight.

These insights can be shown on the result page for the assessment that just finished. The current state endpoint does not provide a full historical confidence-answer list, so do not present these counters as lifetime or all-time totals unless the frontend separately stores assessment history or the backend adds an event-history endpoint.

---

## 5. Different learning situations and what the UI should do

### Situation A: Brand-new course, before the diagnostic

Backend state may return a 404 saying the learner has not started the course.

Frontend behavior:
- Treat this as **not started**, not a fatal dashboard error.
- Wait until `GET /courses/{cid}` reports `ready`.
- Call `POST /courses/{cid}/learners/{lid}/start` once.
- Store the returned diagnostic question list in app state while the assessment is active.
- Do not call `/start` again on refresh without first checking whether the learner already exists; a second start returns 409.

Retention UI:
- Show an onboarding empty state: "Take your first assessment to see your mastery."
- Do not show fake mastery, fake retention, or a fabricated review history.

### Situation B: Initial diagnostic completed

The first `/attempts` call submits the diagnostic. The response includes grading, updated `mastery`, and `next`.

Important diagnostic behavior in the documentation:
- A concept answered correctly in the diagnostic can be placed at `p_mastery = 0.85`.
- Confidence affects the re-check timing for placed concepts: low confidence 1 day, medium 2 days, high 3 days.
- The API does not expose a separate `verified` boolean. A placed concept that later passes a review is not marked with a dedicated verified field.

Frontend behavior:
- Show the diagnostic score and topic-level snapshot from this diagnostic response.
- Show the backend's current mastery values.
- Do not label a concept "verified" merely because it is at 0.85.
- Explain that the agent will re-check placed concepts later.

### Situation C: A concept is below the mastery threshold

Condition:

```js
concept.p_mastery < 0.85
```

Display:
- Developing / Needs strengthening.
- The actual `p_mastery` percentage.
- Attempts and failed rounds.
- Any `needs_help` indicator.
- `due_at` only if it is present.

Do not call it overdue when `due_at` is null. An unmastered concept with no review date is not the same as a mastered concept whose scheduled review has passed.

### Situation D: A concept is mastered and its review is upcoming

Conditions:
- `p_mastery >= 0.85`.
- `due_at` exists and is in the future relative to the learner's clock.

Display:
- Mastered.
- Next review date.
- Stability days.
- Current retrievability from the API.

Do not claim that the concept will remain mastered forever. BKT mastery and the scheduler's forgetting/retrievability estimate are distinct values.

### Situation E: A review is due now or overdue

A scheduled `due_at`/`due` timestamp has passed relative to the learner's clock.

Display:
- Due now / Overdue label.
- Concept name.
- Scheduled date/time.
- Catch Up action if the feature is enabled.

Catch Up behavior with the current API:
1. Fetch state to refresh due concepts.
2. Call `GET .../next`.
3. Render the backend-selected step.
4. If `step.kind === "review"`, show its review questions.
5. Submit via `POST .../attempts`.
6. Refresh state and use the returned `next` step to continue.

Limitation: `GET .../next` asks the adaptive policy to choose the next step. It does not accept a concept ID to force one exact overdue item. Do not promise that clicking a particular overdue concept will open that exact review unless targeted-review backend support is added.

### Situation F: Review passed

The attempts response includes the graded answers and updated next step. The refreshed state contains updated mastery and schedule values.

Display:
- Review quiz result for that round.
- Updated `p_mastery`.
- Updated `stability_days` and `due_at`.
- Updated `retrievability`.
- Updated `lapses` count (normally unchanged by a successful review).

Do not calculate the next date by adding a guessed multiplier. Use the returned `due_at`.

### Situation G: Review failed / lapse

The Backend Guide describes a failed review as a lapse. The API exposes `lapses`, and the policy sends the learner to a lesson on that concept after a failed review.

Display:
- Review score and explanation.
- A calm "Let's strengthen this concept" message.
- The next lesson returned by the backend if `next.step.kind` is `lesson` or `fallback`.
- Updated mastery, stability, lapse count, and due date from refreshed state.

Do not overwrite mastery or stability locally. Do not assume every wrong answer is a lapse: the documented lapse is a failed review of a previously mastered concept.

### Situation H: Mastery is high but retrievability has fallen

Display the two metrics separately:
- Mastery: backend belief about whether the learner has learned the concept (`p_mastery`).
- Recall strength: estimated ability to retrieve it now (`retrievability`).

A concept may have a high historical mastery estimate while its recall estimate has faded. Use the backend's scheduling decision and due dates to guide the next action. Do not convert retrievability into a new mastery value in the frontend.

### Situation I: Learner needs help / repeated failures

Check:
- `ConceptState.needs_help`.
- Top-level `needs_help[]`.
- `failed_rounds`.
- `fallbacks`.
- `step.give_up_after` on the next step.

Display a support/revisit state and explain the relevant concept. If the returned step is a fallback, show the prerequisite concept being revisited. Do not invent a support-chat endpoint.

### Situation J: Misconception suspected, confirmed, or resolved

The API documentation defines:
- One evidence point makes a misconception suspected.
- Two evidence points confirm it.
- Two clean answers in a row resolve it.
- A high-confidence wrong answer adds 2 evidence points instead of 1.
- A misconception can come back.

Display the backend's `status`, `evidence`, and `clean_streak`. Do not recompute these counters in the frontend. Use friendly text labels and avoid exposing raw tag slugs as the main description.

### Situation K: Session ended

A learning session contains up to 15 answered questions. When the next step is `session_end`:
1. Show a session-complete state.
2. Call `POST .../sessions/new` when the learner chooses to continue.
3. Then call `GET .../next`.
4. Resume rendering the returned step.

Do not create new question IDs or repeat the previous round locally.

### Situation L: Agent reports done

When `step.kind === "done"`, show that all reachable concepts are currently mastered according to the agent. Do not say "you will never need to review again". The API documentation says to come back later for reviews; future review schedules may still matter.

### Situation M: No due reviews / empty course

If there is no `next_due` and `due` is empty:
- Show "Nothing due yet".
- If the learner has not started, show the first-assessment CTA.
- If the learner has started and has upcoming `due_at` values, show the earliest upcoming review.
- If no concepts have review dates, do not invent dates.

### Situation N: No mastered concepts yet

If `pace.mastered === 0` or `stability_days` is zero for the displayed concepts:
- Show mastery coverage as 0% if `pace.total > 0`.
- Show recall strength as "Not established" for concepts that have never been mastered.
- Show `attempts_per_mastered` as `--` if the value is absent or cannot be computed.
- Do not show an average recall score of 100% based on the API's never-mastered sentinel.

---

## 6. Time handling: real time vs simulated learner time

The backend docs say all `now`, `due`, and `retrievability` values use each learner's **simulated clock**. `POST .../advance` changes that clock for demos.

API datetimes are documented as naive UTC ISO strings without a trailing `Z`. When parsing in JavaScript, treat them as UTC, not local wall-clock time:

```js
function parseBackendUtc(value) {
  if (!value) return null;
  // API sends naive UTC strings; add Z only if no timezone is present.
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
```

Important simulated-clock caveat:
- In normal use with no demo clock advance, comparing the due timestamp to current UTC is expected to work.
- After `/advance`, the learner's simulated clock may differ from the browser's real clock. The `/advance` response includes `now`; use that returned simulated time as the reference for that demo session, or ask the backend teammate to include the current simulated `now` in `/state`.
- Do not silently compare simulated due dates against the browser's wall clock after clock advancement.

The most robust backend improvement would be adding a `now` field to the state response, so the Retention page can always calculate Due / Upcoming using the same clock as the engine.

---

## 7. What the current API cannot support as a historical analytics dashboard

The current `/state` response is a snapshot of current learner state. The current `/attempts` response describes the latest submitted round. The supplied API reference does **not** document a historical attempts/events endpoint.

Therefore, do not fabricate these charts or KPIs from the current API:

| Desired UI | Current limitation | What backend support is needed |
|---|---|---|
| Mastery trend over 7 / 30 days | State gives current `p_mastery`, not a timestamped history | Learner-state snapshots or mastery-change events with timestamps |
| Review history timeline | `last_reviewed_at` is only the latest schedule-change timestamp per concept | Review event history with outcome and timestamp |
| Daily activity / streak | No daily activity endpoint or event series documented | Timestamped learner activity events |
| Time spent learning | Time spent was dropped from the schemas | Session start/end or active-time events |
| Historical quiz score trend | `/attempts` returns the current round, not a result-history collection | Persisted assessment result records and a history endpoint |
| Exact total correct / wrong across all sessions | `ConceptState.attempts` is a question-attempt count, not a correct-answer total | Per-answer history or aggregate correct/incorrect counters |
| User-selectable review of a specific due concept | `GET .../next` lets the brain choose; no target concept parameter | Targeted review-start endpoint that serves and registers new question IDs |
| Take a future review early | No early-review route documented | Early review endpoint / policy override with defined schedule behavior |
| Retake the original diagnostic | `/start` is one-time and returns 409 when repeated | Explicit reset or new diagnostic-attempt flow |
| Calculated novice / beginner / intermediate / advanced level | `level` on course creation is self-assessed; no calculated level field | A defined backend classification policy and response field |

If these features are important, request them from the backend teammate instead of building a fake timeline from current snapshots.

---

## 8. Recommended calculation and display rules summary

| Metric | Calculation / source | Label / handling |
|---|---|---|
| Mastery coverage | `pace.mastered / pace.total * 100` | "Concepts mastered"; handle total 0 |
| Per-concept mastery | `p_mastery * 100` | "Mastery"; mastered at `>= 0.85` |
| Recall strength | `retrievability[concept_id]` | "Estimated recall"; never mastered is not 100% remembered |
| Due count | Count scheduled timestamps at/before learner's current clock | "Due now"; use simulated time correctly |
| Overdue count | Count scheduled timestamps before learner's current clock | "Overdue" |
| Quiz headline score | `correctCount / totalQuestions * 100` | Consistent whole-quiz score; skipped count shown separately |
| Answered accuracy | `correctCount / answeredCount * 100` | Optional separate statistic; guard answeredCount 0 |
| Skipped count | Questions shown minus submitted/graded questions | Use original displayed question set |
| Concept quiz breakdown | Group current round by `concept_id` | Single diagnostic question: show status, not a robust percentage |
| Misconception status | Backend `status` | Do not recompute evidence or clean streak |
| Attempts per mastered | `pace.attempts_per_mastered` | Show `--` if no mastered concepts |
| Review next date | `due_at` / `next_due` | Display backend date; do not calculate a new one |

---

## 9. Data refresh sequence for the frontend

### When opening the Retention page

1. Fetch `GET /courses/{cid}` for concept IDs and names.
2. Fetch `GET /courses/{cid}/learners/{lid}/state` for current mastery and schedule.
3. Join concept IDs to names.
4. Derive display-only counts and statuses using the rules above.

### After submitting any diagnostic / practice / review assessment

1. Submit answers to `POST .../attempts`.
2. Use the response's `graded[]` for the just-completed quiz result.
3. Use `correct_indices` and `explanations` for answer feedback.
4. Use `mastery` for the immediate updated mastery map if needed.
5. Use `next` to decide the next screen/step.
6. Refresh `GET .../state` before rendering the Retention page or sidebar.

Do not resubmit the same question IDs. The API documentation says served question IDs become invalid after they have been answered; resubmitting them returns 422.

### When Catch Up Now is clicked

1. Refresh the learner state.
2. If there are no due items, show an empty state.
3. Request `GET .../next`.
4. Render the actual returned step.
5. Only describe it as a review if `step.kind === "review"`.
6. Submit the returned question IDs through `/attempts`.
7. Refresh state and continue with the returned `next` step.

---

## 10. API safety and implementation notes

- Every request except `GET /health` requires `X-Master-Password` in the documented local API setup.
- Do not place a production master password in a public React bundle, localStorage, or GitHub Pages frontend. A static frontend cannot keep that secret. Use a backend proxy/auth design before public deployment.
- The API's `/start` endpoint is not idempotent. Check learner state / handle 409 instead of blindly calling it on every page load.
- `/attempts` is not idempotent. Do not automatically retry a submission after an ambiguous network failure without first resolving whether it was accepted.
- Handle 401, 404, 409, and 422 as distinct states; show human-readable messages instead of raw JSON errors.
- A lesson may be `null` if lesson generation failed. The API reference says call `GET .../next` again to retry in that situation.
- The API's `lesson.resources` array is documented as empty today. Do not show articles/videos as available unless another resource provider has actually been integrated.
- Course generation can remain `generating` for around 2–3 minutes in the documented run. Use an indeterminate loading state, poll as documented, and handle `failed`.

---

## 11. Small frontend helper functions (display-only)

```js
const MASTER_THRESHOLD = 0.85;

function getConceptStatus(concept) {
  return {
    mastery: concept.p_mastery >= MASTER_THRESHOLD ? "mastered" : "developing",
    needsHelp: Boolean(concept.needs_help),
  };
}

function getMasteryCoverage(pace) {
  if (!pace || !Number.isFinite(pace.total) || pace.total <= 0) return null;
  return Math.round((pace.mastered / pace.total) * 100);
}

function getAssessmentCounts(questionsShown, graded) {
  const total = questionsShown.length;
  const answered = graded.length;
  const correct = graded.filter((answer) => answer.correct).length;
  const incorrect = answered - correct;
  const skipped = Math.max(0, total - answered);

  return {
    total,
    answered,
    correct,
    incorrect,
    skipped,
    wholeQuizPercent: total > 0 ? Math.round((correct / total) * 100) : null,
    answeredAccuracyPercent: answered > 0 ? Math.round((correct / answered) * 100) : null,
  };
}

function parseBackendUtc(value) {
  if (!value) return null;
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
```

These helpers only format or summarize API data. They do not replace the backend's BKT, scheduler, policy, or misconception engine.

---

## 12. Build priority

### Implement now with the current backend

1. Mastery coverage card.
2. Concept mastery list with bars.
3. Recall-strength display using API retrievability, with the never-mastered caveat.
4. Upcoming / due / overdue review list.
5. Misconception status list.
6. Needs-help concept list.
7. Current assessment result breakdown.

### Ask the backend teammate before implementing

1. State response should ideally include current simulated `now`.
2. Historical assessment / review event endpoint.
3. Historical mastery snapshots for trend charts.
4. Targeted review-start endpoint for selecting one exact concept.
5. Early-review behavior and schedule policy.
6. Diagnostic retake/reset flow.
7. Confirm stability multiplier in the current code because the supplied guide and live API reference describe it differently.

**Final rule:** backend owns learning decisions and persistent learning state; frontend owns presentation, navigation, and clearly labelled display-only calculations.
