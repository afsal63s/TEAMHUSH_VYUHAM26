# OnlyNerds

An adaptive tutor that learns how you learn: it finds what you already know, spots the specific mistakes you
make, teaches to those mistakes, and brings ideas back right before you would forget them.

- **Demo:** https://onlynerds-frontend.vercel.app/
- **Demo video:** https://drive.google.com/file/d/1anBcibbKdrnpEPouV94bqIvSuDiwzX9C/view?usp=sharing

---

## 1. Problem statement

**AF-05 · Adaptive Learning and Competency Assessment Agent**

**Problem context:** Learners have different levels of prior knowledge, learning pace, and conceptual gaps. Fixed
learning materials and uniform assessments may fail to address individual needs or demonstrate lasting mastery.

**Challenge description:** Develop a learning agent that tracks performance, identifies likely misconceptions,
adapts explanations and exercises, and schedules revision based on learner progress. Evaluate whether its
interventions improve mastery and retention rather than measuring success only through short-term quiz scores.

### How OnlyNerds answers each part

| The challenge asks for | OnlyNerds |
|---|---|
| Different prior knowledge | A diagnostic places you first; concepts you already know are not taught again |
| Different learning pace | Mastery is tracked per concept; you move on when *you* have it, not after a fixed number of lessons |
| Tracks performance | Every answer updates a mastery probability per concept (Bayesian Knowledge Tracing) |
| Identifies likely misconceptions | Every wrong option is labelled with the misunderstanding it reveals; repeated ones are confirmed |
| Adapts explanations and exercises | Lessons target confirmed misconceptions, switch style when one fails, and step back to a prerequisite when stuck |
| Schedules revision | A forgetting model sets each concept's review date; passed reviews push the next one further out |
| Evaluates mastery and retention, not just quiz scores | Simulated learners are tested on held-out questions immediately and again at 7 and 30 days, against a fixed course |

## 2. OnlyNerds: our solution

You type a topic and a level (for example "Python for beginners"). OnlyNerds:

1. **Builds the course for you:** a map of small concepts and which ones depend on which, quiz questions for
   each, and a list of the common misunderstandings people have about each concept.
2. **Places you with a short diagnostic,** so concepts you already know are not taught again.
3. **Decides every next step for you:** a lesson aimed at *your* mistakes, a quick review of something you are
   about to forget, a step back to a missing basic when you are stuck, or "that's enough for today".
4. **Finds outside material:** a research agent searches articles and videos for each concept and the lessons
   are written from those sources.
5. **Shows your progress:** mastery per concept, the misconceptions it found and when you fixed them, what is
   due for review, and how well you remember things after a week or more.

The key rule: **code decides, the AI writes.** The AI writes the course content and lessons. Every teaching
decision is made by plain, deterministic rules that can be tested and explained ("you are seeing this review
because you last saw this concept 9 days ago and your recall has dropped to 72%").

## 3. Core logic, in plain words

**Concepts and prerequisites.** A topic is split into small ideas, like "variables", "loops", "functions".
Some need others first: you can't learn loops before variables. A concept is *unlocked* once its prerequisites
are mastered.

**Questions that reveal *why* you are wrong.** Every wrong option in a question is labelled with the
misunderstanding it represents. Picking it tells OnlyNerds not just that you are wrong, but how. If the same
misunderstanding shows up twice, it is confirmed and the next lesson tackles it head on.

**Mastery is a probability.** For each concept OnlyNerds keeps an estimate of how likely it is that you know it
(Bayesian Knowledge Tracing). A right answer pushes it up, a wrong one pulls it down, and a lucky guess counts
for less when you said you weren't sure. At 85% the concept counts as mastered.

**Forgetting is modelled.** Each mastered concept has a "memory strength" in days. Your chance of recalling it
fades over time. When it drops to 90%, a review is due. Pass the review and the memory gets 2.5 times stronger,
so the next review is further away. Fail it and the memory weakens, and the concept is retaught.

**The decision, every step, in this order:**

1. **Relearn** anything you had mastered but have since failed.
2. **Review** anything due, the most faded first.
3. **Teach** the weakest unlocked concept, aimed at your confirmed misconceptions, in a style not tried before
   if the last one didn't work.
4. **Step back** to a prerequisite if you failed the same concept 3 rounds in a row. If that doesn't help, flag
   the concept as "needs help" instead of looping forever.
5. **Stop** after 15 questions in a session, or when everything is mastered and nothing is due.

**The agents.**

| Agent | Job | Uses AI? |
|---|---|---|
| Curriculum Architect | Builds the concept map and misconception list from your topic | Yes |
| Question Smith | Writes the questions and labels each wrong option | Yes |
| Tutor | Writes each lesson for the step chosen | Yes |
| Scout | Searches articles and videos per concept | Yes |
| Judge | Checks every generated piece (no loops in the map, every option labelled, lesson quality) and sends it back if it fails | No |
| Assessor | Grades answers and updates mastery and misconceptions | No |
| Memory Keeper | Tracks forgetting and schedules reviews | No |
| Orchestrator | Picks the next step using the rules above | No |

**Does it work?** We ran 100 simulated learners per setup on two Python courses, with the same number of
questions each, and tested them on held-out questions right after and at 7 and 30 days. The adaptive version
remembered about 2.5 points more than a fixed course at both 7 and 30 days, but scored about 3 points lower
on the test right after, because it spends part of the time on reviews and skips what the diagnostic says you
know. These are simulated learners, so the result depends on the simulator's assumptions; details in
`backend/scripts/evaluate.py`.

## 4. Installation guide

### Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js and npm
- MongoDB running on `localhost:27017` (local install or `docker run -d -p 27017:27017 mongo`)
- An Anthropic API key
- Optional: a Tavily API key and a YouTube Data API key for the research agent

### 1. Clone

```bash
git clone https://github.com/afsal63s/TEAMHUSH_VYUHAM26.git
cd TEAMHUSH_VYUHAM26
```

### 2. Backend

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic key (required) |
| `MASTER_PASSWORD` | Any password; the app asks for it at login. Leave empty only for local testing |
| `MONGO_URI`, `MONGO_DB` | Defaults: `mongodb://localhost:27017`, `onlynerd` |
| `MAX_SPEND_USD` | Spend cap for AI calls per server run (default 2.00) |
| `TAVILY_API_KEY`, `YOUTUBE_API_KEY` | Optional; without them research is skipped |

Never commit `.env` or share your keys. `.env` is already gitignored.

Install and start:

```bash
uv sync
uv run uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000` (interactive docs at `http://127.0.0.1:8000/docs`).

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` and log in with your `MASTER_PASSWORD`. The frontend must run on port 3000,
because that is the only origin the backend allows. If the backend is not at `http://127.0.0.1:8000`, copy
`frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL`.

### Quick start on Windows

After the one-time setup above (MongoDB running, `backend/.env` filled in), double-click `start.bat` in the repo
root. It installs the frontend packages on first run, opens the backend and the frontend in two windows, and opens
`http://localhost:3000` in your browser. Close the two windows to stop.

### 4. Check it (optional)

```bash
cd backend
uv run pytest -q                    # tests, no network or API key needed
uv run python scripts/evaluate.py   # offline evaluation, writes results/eval.md
```

### More

- API reference with examples: `backend/docs/API_REFERENCE.md`
- Frontend notes: `frontend/README.md`
