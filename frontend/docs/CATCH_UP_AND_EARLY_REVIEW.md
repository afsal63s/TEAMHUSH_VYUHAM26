# OnlyNerds: Catch Up Now & Take It Early

**Document type:** Feature and API integration notes  
**Status:** Catch Up Now can use the existing adaptive flow; targeted reviews and early assessments need backend support.  
**Audience:** Frontend and backend developers

---

## 1. Purpose

This document describes two dashboard actions:

- **Catch Up Now:** Help a learner complete reviews that are already due or overdue.
- **Take It Early:** Let a learner start a scheduled review before its due date.

The current backend already has a scheduled-review system and an adaptive `next` step. However, it does not currently expose an endpoint that lets the frontend request a review for one specific concept. It also does not document a dedicated early-review endpoint.

Do not treat any proposed route in this document as implemented until the backend is updated and its OpenAPI schema/API reference confirms it.

## 2. Existing backend capabilities

The current API reference documents these relevant routes:

| Endpoint | Purpose |
|---|---|
| `GET /courses/{cid}/learners/{lid}/state` | Returns learner progress and review schedule information. |
| `GET /courses/{cid}/learners/{lid}/next` | Returns the adaptive engine's currently selected next step, including its questions. |
| `POST /courses/{cid}/learners/{lid}/attempts` | Submits served questions, grades answers, updates mastery/review scheduling, and returns the next step. |
| `POST /courses/{cid}/learners/{lid}/advance` | Moves the learner's simulated clock forward by a positive number of days and decides the next step for that simulated time. |
| `POST /courses/{cid}/learners/{lid}/sessions/new` | Starts a new learning session after a `session_end` step. |

### Useful fields

The learner `state` response includes:

- `due`: a mapping of `concept_id` to its scheduled review timestamp. The API reference notes that timestamps in the past are due now.
- `next_due`: the earliest scheduled review timestamp, or `null` when nothing is scheduled.
- `concepts[]`: per-concept information including `p_mastery`, `due_at`, `stability_days`, `lapses`, and `needs_help`.
- `retrievability`: concept ID to current recall probability.

The course response from `GET /courses/{cid}` includes concept IDs and names. Use those IDs to match scheduled reviews to display names.

### Existing `next` response

`GET .../next` returns a `StepOut` containing:

- `step.kind`: one of `lesson`, `review`, `fallback`, `session_end`, or `done`.
- `step.concept_id`: the concept the engine selected, when applicable.
- `reason`: why the engine selected this step.
- `lesson`: lesson content for lesson/fallback steps; normally `null` for review and terminal steps.
- `questions`: questions to show for the selected step. The current API reference documents two questions for a review step and three for a lesson step.

**Important:** `GET .../next` asks the adaptive engine to choose the next step. It does not accept a `concept_id` and does not guarantee that the selected step will be a review of the exact concept the learner clicked.

### Existing answer submission

Submit answers through:

```http
POST /courses/{cid}/learners/{lid}/attempts
```

The request contains an `answers` array. Each answer includes:

- `question_id`: an ID returned by the backend for a question served to this learner.
- `chosen_index`: the selected option's zero-based index.
- `confidence`: optional `low`, `medium`, or `high`.

Only questions served to that learner are accepted. Answer IDs are single-use: resubmitting the same question IDs can return `422`. The response includes grading, updated mastery, messages, and a `next` step.

---

## 3. Feature A: Catch Up Now

### What the user expects

The learner sees overdue concepts in the dashboard and clicks **Catch Up Now**. The app opens a review experience, submits answers to the existing attempts endpoint, and continues according to the adaptive engine's response.

### What can be implemented with the current API

The frontend can:

1. Fetch learner state using `GET .../state`.
2. Read the `due` schedule and identify reviews that are due according to the learner's clock.
3. Resolve concept IDs to readable names using the course's `concepts` list.
4. When the user clicks **Catch Up Now**, call `GET .../next`.
5. Render the returned step based on `step.kind` rather than assuming it is always a review.
6. If it is a `review`, display its questions and submit the answers using `POST .../attempts`.
7. Use the `next` object returned by the attempts response to continue. Fetch `GET .../next` again only when needed, such as after a page reload or when the client no longer has the current step.
8. Refresh learner state after each completed attempt so the dashboard reflects updated mastery and due dates.

### Important limitation

The frontend cannot guarantee that the agent will review a particular overdue concept selected by the learner. The existing `GET .../next` endpoint has no concept selector. It follows the adaptive engine's decision.

For the first version, label the action **Catch Up Now** and explain that the agent will choose the next recommended review. If the returned step is a lesson, fallback, `session_end`, or `done`, render the appropriate state instead of forcing it into a review screen.

### Suggested frontend flow

```text
Dashboard loads
    |
    v
GET .../state
    |
    v
Display due/overdue review cards
    |
    v
Learner clicks "Catch Up Now"
    |
    v
GET .../next
    |
    v
Inspect step.kind
    |
    +--> review: show review questions
    |
    +--> lesson/fallback: show the returned learning step
    |
    +--> session_end: offer the new-session action
    |
    +--> done: show the completed state
    |
    v
POST .../attempts
    |
    v
Use response.next and refresh GET .../state
```

### Due-date handling notes

- Do not assume every entry in `due` is overdue. It maps concepts to scheduled timestamps, which may include future reviews.
- Determine whether a review is due by comparing its timestamp with the learner's current clock.
- The API reference says learner state is calculated at the learner's simulated time. The `state` response fields documented here do not include a dedicated `now` property. If the demo uses a non-zero simulated clock offset, ask the backend developer how the frontend should obtain the authoritative learner time before doing client-side due/overdue comparisons.
- API datetimes are documented as naive UTC ISO strings. For browser date parsing, append `Z` when interpreting these values as UTC, unless the backend changes the serialization contract.
- An `advance` response includes `now` and `due_now`, but `advance` changes the simulated clock. Do not call it just to discover the current time or to implement a normal catch-up action.

---

## 4. Feature B: Take It Early

### What the user expects

The dashboard shows a future assessment, for example:

> Next assessment due in 3 days  
> Re-check: Chain rule and vanishing gradients  
> Take it early

Clicking **Take It Early** should start an assessment now, without waiting for the scheduled date and without pretending that the learner's clock has moved forward.

### Current API limitation

The current API reference does not document a route that:

- accepts a specific concept or set of concepts to review;
- starts a review before its scheduled due date; or
- guarantees that the adaptive engine returns that requested concept.

`POST .../advance` is **not** an early-review endpoint. It moves the learner's simulated clock forward by a positive number of days, starts a new session, and decides the next step at that future time. It is documented for demo/control-panel use. Do not wire **Take It Early** to `/advance`.

### Backend support to discuss

A targeted-review capability is needed. One possible API design is shown below. This is a proposal only, not an existing route or contract.

**Illustrative proposal:**

```http
POST /courses/{cid}/learners/{lid}/reviews/{concept_id}/start
```

Possible behavior:

1. Validate that the course, learner, and concept exist.
2. Determine whether the requested review is overdue or scheduled for a future date.
3. Permit an early start only when the request is explicitly allowed by backend rules.
4. Generate or retrieve review questions for that concept.
5. Register the returned question IDs as served to this learner so the existing `/attempts` endpoint accepts them.
6. Return a review step using the agreed response schema.
7. Do not change the simulated clock merely because the learner chose to review early.
8. Define how an early pass or failure changes `due_at`, stability, retrievability, and lapse counters.

The backend team should decide whether this route accepts one concept at a time or a list of concept IDs for a combined assessment. The current normal review flow is documented as two questions for one concept; a multi-concept early assessment would need an explicit question-count and response contract.

### Suggested UI behavior until backend support exists

- Keep the **Take It Early** button disabled, or show a clear message such as "Early assessments are not available yet".
- Do not call `/advance` as a workaround.
- Do not create local or fake questions.
- Once the backend route exists and is verified, connect the button to that route and submit the returned question IDs through the existing `/attempts` endpoint.

---

## 5. Recommended implementation scope

| Capability | Current status | Frontend action |
|---|---|---|
| Display concept review schedule | Supported by `GET .../state` | Implement now. |
| Display concepts that are due | Supported by `state.due`, subject to correct learner-clock comparison | Implement with the time-handling caveat above. |
| Start the agent-selected next step | Supported by `GET .../next` | Implement now. |
| Complete a returned review | Supported by `POST .../attempts` | Implement now. |
| Guarantee review of a clicked concept | Not supported by a documented route | Requires backend work. |
| Start a future assessment early | Not supported by a documented route | Requires backend work. |
| Move simulated time forward for a demo | Supported by `POST .../advance` | Keep separate from normal catch-up and early-review UX. |

### Recommended order

1. Implement the dashboard schedule cards using real state data.
2. Implement **Catch Up Now** using the agent-selected `GET .../next` flow.
3. Handle all possible `step.kind` values and show clear empty/terminal states.
4. Ask the backend developer to design and implement targeted review/early assessment support.
5. Add **Take It Early** integration only after the new backend route is implemented, documented, and tested.

---

## 6. Rules for frontend implementation

- Treat the live OpenAPI schema and verified API reference as the source of truth.
- Do not invent endpoints, response fields, or question IDs.
- Do not use `/advance` to implement **Catch Up Now** or **Take It Early**.
- Always render the step the backend actually returns.
- Submit only question IDs served to the current learner and do not submit them twice.
- Use the `next` step returned by `/attempts` when available.
- Refresh learner state after attempts so mastery and review schedule stay current.
- Do not expose `MASTER_PASSWORD` or other backend secrets in public frontend JavaScript. A static frontend must not contain a production master password; use an appropriate server-side authentication/proxy design before public deployment.
- Keep all backend changes out of the frontend task. Backend route additions must be handled and verified by the backend owner.

---

## 7. Questions for the backend developer

Before implementing targeted review, agree on these details:

1. Should the user be able to start a review for one selected concept, or several concepts together?
2. Should an early review be allowed for any scheduled concept, or only concepts above a mastery threshold?
3. How many questions should an early assessment contain?
4. Should passing an early review reschedule the next review from the actual attempt time?
5. How should a failed early review affect mastery, stability, and lapse counters?
6. How should the frontend obtain the learner's authoritative current time when the simulated clock offset is non-zero?
7. Should a targeted review return the existing `StepOut` shape so the frontend can reuse its review renderer and `/attempts` submission flow?

---

## 8. Source of truth

This note is based on the OnlyNerds API reference and verified route documentation dated **2026-10-30**. The following statements are documented API behavior:

- `state.due` maps concept IDs to scheduled review timestamps; past timestamps are due now.
- `GET .../next` returns the adaptive engine's selected step and questions.
- A review step currently contains two questions for one concept.
- `POST .../attempts` accepts only questions served to that learner and returns the next step.
- `POST .../advance` moves the learner's simulated clock forward and is intended for demo/control-panel use.

The targeted-review route and early-assessment behavior in Section 4 are proposed future backend work, not current API functionality.
