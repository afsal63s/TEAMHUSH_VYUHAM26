# API reference check

Generated 2026-10-31 04:08. Routes from `app.openapi()`.

| Route | Called successfully | Calls | Median latency (s) | Max latency (s) | Statuses seen | LLM calls in the request |
|---|---|---|---|---|---|---|
| `GET /auth/check` | yes | 2 | 0.000 | 0.000 | 200, 401 | 0 |
| `GET /courses` | yes | 1 | 0.000 | 0.000 | 200 | 0 |
| `POST /courses` | yes | 5 | 0.016 | 0.031 | 200, 401, 422 | background |
| `GET /due` | yes | 1 | 0.000 | 0.000 | 200 | 0 |
| `GET /courses/{cid}` | yes | 3 | 0.008 | 0.016 | 200, 404 | background |
| `POST /courses/{cid}/learners/{lid}/start` | yes | 8 | 0.015 | 0.063 | 200, 409 | 0 |
| `POST /courses/{cid}/learners/{lid}/attempts` | yes | 18 | 0.015 | 0.125 | 200, 409, 422 | 0 |
| `GET /courses/{cid}/learners/{lid}/state` | yes | 7 | 0.000 | 0.016 | 200, 404 | 0 |
| `POST /courses/{cid}/learners/{lid}/advance` | yes | 3 | 0.000 | 0.000 | 200, 422 | 0 |
| `POST /courses/{cid}/learners/{lid}/sessions/new` | yes | 2 | 0.016 | 0.016 | 200 | 0 |
| `GET /courses/{cid}/learners/{lid}/next` | yes | 15 | 0.000 | 0.016 | 200, 409 | 0 |
| `GET /courses/{cid}/learners/{lid}/resources` | yes | 3 | 0.015 | 0.016 | 200 | background |
| `POST /courses/{cid}/learners/{lid}/reset` | yes | 2 | 0.000 | 0.000 | 200, 404 | 0 |
| `GET /health` | yes | 1 | 0.016 | 0.016 | 200 | 0 |
| `GET /eval/results` | no (404 expected: no results file yet) | 1 | - | - | 404 | 0 |

LLM calls in the request count lesson generation (role `strong`) only. Course generation and research run in the background; 0 research (role `cheap`) calls were logged during this run.

Planned routes probed:

- `POST .../learners/{lid}/virtual/start` -> 404
- `POST .../learners/{lid}/virtual/pause` -> 404
- `POST .../learners/{lid}/virtual/resume` -> 404
- `POST .../learners/{lid}/virtual/stop` -> 404
- `POST .../learners/{lid}/virtual/speed` -> 404
- `GET .../learners/{lid}/virtual/status` -> 404
- `GET .../learners/{lid}/virtual/events?after=0` -> 404
