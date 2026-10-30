# OnlyNerds frontend: current state (mock data only)

Snapshot of `frontend/` as of 2026-10-31. The frontend is **not connected to the backend**: every screen runs on
mock data. All paths below are relative to `frontend/`.

---

## 1. Stack and run

| Item | Value | Source |
|---|---|---|
| Framework | React 19.3.1, react-dom 19.3.1 (installed versions) | `package.json`, `node_modules/react/package.json` |
| Build tool | Vite 8.3.5 with `@vitejs/plugin-react` 6.1.2 | `package.json`, `vite.config.ts` |
| Router | `react-router` 8.4.0 (`BrowserRouter`, `Routes`, `Route`, `Link`, `Navigate`, hooks) | `package.json`, `src/App.tsx` |
| Language | TypeScript 7.0.2 (no `strict` flag set; `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly` are on) | `tsconfig.app.json` |
| Styling | Plain CSS files imported per component (global, BEM-like class names), design tokens as CSS variables in `src/index.css`; a few inline `style` props. Inter font from Google Fonts. | `src/index.css`, `index.html`, `src/**/*.css` |
| UI / chart libraries | None. Icons are inline SVG (`src/components/Icon.tsx`); charts and rings are hand-written SVG (`src/components/Ring.tsx`, `src/screens/retention/Retention.tsx`, `src/screens/home/Covers.tsx`). | — |
| Linter | oxlint (1.90.0 installed) | `package.json`, `.oxlintrc.json` |
| Package manager | npm (`package-lock.json` present) | `package-lock.json` |
| Dev server | Pinned to `http://localhost:3000`, `strictPort: true` (fails instead of switching port) | `vite.config.ts` |
| Env | `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`), used only by the unused API client | `.env.example`, `src/api/client.ts` |

Commands (run in `frontend/`):

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # tsc -b && vite build
npm run lint       # oxlint
```

---

## 2. Routes

Defined in `src/App.tsx`. Link builders are in `src/routes.ts`.

| Path | Component file | Screen | Clickable with mock data today |
|---|---|---|---|
| `/` | `src/screens/home/HomeFeed.tsx` | Home feed | Yes |
| `/?empty` | `src/screens/home/HomeEmpty.tsx` (rendered by `HomeFeed` when `?empty` is in the URL) | Home empty | Yes (only via the `?empty` flag) |
| `/new` (`?topic=`, `?level=`) | `src/screens/newchat/NewChat.tsx` | New chat (topic + level) | Yes |
| `/build?topic=&level=` (`&simulate=fail`) | `src/screens/build/BuildCourse.tsx` | Course building: Building / Ready / Failed | Yes (simulated ~6 s) |
| `/assessment?topic=&level=` (`&course=`) | `src/screens/assessment/Assessment.tsx` | Assessment (diagnostic), then Assessment results in the same component | Yes |
| `/assessment?mode=review&topic=` | `src/screens/assessment/Assessment.tsx` | Review / quiz (same component, review wording, confidence shown) | Yes |
| `/chat/:chatId` | `src/screens/tutor/TutorChat.tsx` → `PlaceholderChat` (same file) or `src/screens/tutor/CourseChat.tsx` | Course page / TutorChat | Yes |
| `/retention` | `src/screens/retention/Retention.tsx` | Retention | Yes |
| `*` | `<Navigate to="/" replace />` in `src/App.tsx` | Fallback to Home | Yes |
| (none) | `src/screens/login/Login.tsx` | Log in / sign up | **No route.** Not imported anywhere (`src/App.tsx` only mentions it in a comment). |

Notes:
- `/chat` with no id is not a route; it falls to `*` and redirects to `/` (`src/App.tsx`).
- `/chat/<unknown id>` silently shows the first placeholder chat (`findChat` fallback, `src/data/placeholder.ts:103`).
- `/assessment` ignores `topic` when choosing questions: every topic and every review uses the same 8 questions (`src/screens/assessment/Assessment.tsx:23`).

---

## 3. Mock data

Two files hold data: `src/data/placeholder.ts` (static mock content) and `src/data/courseStore.ts` (courses created in
the browser, persisted to `localStorage`). `src/api/types.ts` is a byte-identical copy of `docs/types.ts` (checked
with `diff`) and `src/api/client.ts` is a typed fetch client for the backend; **neither is imported by any screen**.

### 3a. `src/data/placeholder.ts`

| Export | Type / shape | Imported by |
|---|---|---|
| `PostStatus` | `type PostStatus = 'progress' \| 'review' \| 'done'` | `src/screens/home/FeedPostCard.tsx`, `src/screens/home/HomeFeed.tsx` |
| `CoverKind` | `type CoverKind = 'nn' \| 'matrix' \| 'code' \| 'attention'` | `src/screens/home/Covers.tsx` |
| `FeedPost` | interface, see below | `src/screens/home/FeedPostCard.tsx` |
| `user` | `{ name: string; initials: string }` = `{ name: 'Alex Rivera', initials: 'AR' }` | `src/components/AppShell.tsx`, `src/screens/home/HomeFeed.tsx` |
| `Chat` | interface, see below | (type only, used inside the file) |
| `previousChats` | `Chat[]`, 6 items | `src/components/AppShell.tsx`, `src/screens/assessment/Assessment.tsx` |
| `findChat` | `(id: string \| undefined) => Chat`; returns the chat with that id, **or `previousChats[0]` if not found** (line 103) | `src/screens/tutor/TutorChat.tsx` |
| `feedPosts` | `FeedPost[]`, 4 items | `src/screens/home/HomeFeed.tsx` |
| `dueReviews` | `{ title: string; due: string }[]`, 4 items | `src/screens/home/HomeFeed.tsx` |
| `overdueReviews` | `{ title: string; late: string }[]`, 3 items | `src/screens/home/HomeFeed.tsx` |
| `AssessmentQuestion` | interface, see below | (type only) |
| `assessment` | `{ title: string; level: string; questions: AssessmentQuestion[]; materialCount: number }`, 8 questions | `src/screens/assessment/Assessment.tsx` |
| `levels` | readonly tuple of `{ key; name; bars; desc }`, 4 items (`as const`) | `src/components/LevelSelect.tsx`, `src/screens/newchat/NewChat.tsx`, `src/screens/build/BuildCourse.tsx` |
| `LevelKey` | `'novice' \| 'beginner' \| 'intermediate' \| 'advanced'` (derived from `levels`) | `src/components/LevelSelect.tsx`, `src/screens/newchat/NewChat.tsx`, `src/screens/home/HomeFeed.tsx` |
| `MaterialStatus` | `type MaterialStatus = 'done' \| 'now' \| 'next'` | `src/screens/tutor/TutorChat.tsx` |
| `materials` | `{ title: string; kind: 'Article' \| 'Video'; source: string; time: string; status: MaterialStatus }[]`, 4 items | `src/screens/tutor/TutorChat.tsx` |
| `tutorMastery` | `{ pct: number; level: string; delta: string; topics: { name: string; pct: number }[] }` | `src/screens/tutor/TutorChat.tsx` |
| `retention` | large object, see below | `src/screens/retention/Retention.tsx` |

```ts
// src/data/placeholder.ts
export interface FeedPost {
  id: string
  chatId: string          // links the card to /chat/:chatId
  status: PostStatus
  topic: string
  time: string            // display text, e.g. '12 min ago'
  text: string
  title: string
  chapters: string        // display text, e.g. '4 chapters'
  duration: string        // display text, e.g. '38 min'
  totalSegments: number
  doneSegments: number
  progress: string        // display text, e.g. '1 of 4 done'
  retention: string       // display text, e.g. '72%' or '—'
  next: string            // display text, e.g. 'Tomorrow'
  cta: string             // button label, e.g. 'Continue chapter 2'
  chats: string           // count shown as text, e.g. '3'
  cover: CoverKind
}

export interface Chat {
  id: string
  title: string
  meta: string            // e.g. 'Now · Neural Networks'
  topic: string
  level: string           // level name, e.g. 'Intermediate'
  courseTitle: string
  reviewDue: boolean      // true shows the "Take the quiz" banner
  nextCheck: { month: string; day: string; when: string; what: string }
}

export interface AssessmentQuestion {
  topic: string
  text: string
  options: string[]       // 4 options
  correct: number         // 0-based index of the right option
}
```

Example objects (lists shortened to two items):

```ts
previousChats[0] = {
  id: 'backprop', title: 'Backpropagation diagnostic', meta: 'Now · Neural Networks',
  topic: 'Neural Networks', level: 'Intermediate', courseTitle: 'Backpropagation, from the chain rule up',
  reviewDue: false,
  nextCheck: { month: 'NOV', day: '3', when: 'In 3 days', what: 'Re-check: chain rule and vanishing gradients' },
}

assessment = {
  title: 'Backpropagation', level: 'Intermediate', materialCount: 6,
  questions: [
    { topic: 'Chain rule', text: 'A 3-layer network has loss L. What does ∂L/∂W₁ depend on?',
      options: ['Only the activations of layer 1', 'The gradient of layer 1’s output alone',
                'Every downstream layer’s local gradient, multiplied together', 'Only the final loss value'],
      correct: 2 },
    { topic: 'Computational graphs', text: 'Why do we keep activations from the forward pass?', options: [/* 4 */], correct: 1 },
    // … 8 total
  ],
}

levels[0] = { key: 'novice', name: 'Novice', bars: 1, desc: 'Brand new to this topic. Start from first principles.' }

materials[0] = { title: 'Derivatives of composed functions', kind: 'Article', source: 'Web', time: '6 min', status: 'done' }

tutorMastery = { pct: 64, level: 'Intermediate', delta: '+9 pts since last check',
                 topics: [{ name: 'Chain rule', pct: 42 }, { name: 'Vanishing gradients', pct: 58 } /* 4 total */] }

retention = {
  kpis: [{ icon: 'R', label: 'Retention rate', value: '81%', delta: '+6 pts', good: true, sub: 'Recall after 7+ days' } /* 4 */],
  masteryPct: 68, masteryLevel: 'Intermediate', masteryDelta: '+4 pts this month',
  masteryNote: '96 concepts tracked across 3 courses',
  levels: [{ name: 'Mastered', n: 38, color: '#0A4C8A' }, { name: 'Solid', n: 31, color: '#0770C9' } /* 4 */],
  concepts: [{ name: 'Backpropagation', course: 'Neural Networks', pct: 42, strength: 48 } /* 9 */],
  memory: { strong: 38, fading: 41, atRisk: 17, curveConcept: 'Gradient descent' },
  overdue: [{ name: 'Matrix multiplication', late: '2 days overdue · Linear Algebra' } /* 3 */],
  upcoming: [{ day: 'Today', name: 'Gradient descent', meta: '5 min · Neural Networks' } /* 4 */],
  attention: [{ name: 'Backpropagation', course: 'Neural Networks', chatId: 'backprop',
                reasons: [{ text: 'Strength 48%', warn: true }, { text: 'Recurring misconception', warn: false }] } /* 4 */],
  misconceptions: { active: 5, resolvedThisMonth: 3,
    items: [{ concept: 'Backpropagation', chatId: 'backprop', recurring: true,
              title: 'Treating each layer’s gradient as local', detail: '…', seen: 'Seen 4 times in 3 sessions' } /* 3 */] },
}
```

Most mock fields are **pre-formatted display strings** (`time`, `chapters`, `progress`, `retention`, `due`, `late`,
`meta`, `kpis[].value`, `kpis[].delta`), not raw numbers or dates.

### 3b. `src/data/courseStore.ts`

Browser-side store for courses created on the Build screen. State lives in a module variable and is mirrored to
`localStorage` key `onlynerds.courses`.

```ts
export interface CourseConcept { id: string; name: string; prerequisites: string[] }

export interface BuiltCourse {
  id: string              // 'course-' + Date.now().toString(36)
  topic: string
  level: string           // level NAME, e.g. 'Intermediate' (not the key)
  concepts: CourseConcept[]
  createdAt: string       // ISO string with 'Z'
  assessed: boolean       // diagnostic taken
  score?: number          // diagnostic percent, set after results
}
```

| Export | Signature | Used by |
|---|---|---|
| `useBuiltCourses` | `() => BuiltCourse[]` (newest first; `useSyncExternalStore`) | `src/components/AppShell.tsx` |
| `useBuiltCourse` | `(id: string \| undefined) => BuiltCourse \| undefined` | `src/screens/tutor/TutorChat.tsx` |
| `findCourse` | `(topic: string, level: string) => BuiltCourse \| undefined`; topic compared trimmed, lower-cased, whitespace-collapsed; level by name | `src/screens/build/BuildCourse.tsx` |
| `addCourse` | `(course: BuiltCourse) => void` (prepends, replaces same id) | `src/screens/build/BuildCourse.tsx` |
| `updateCourse` | `(id: string, patch: Partial<BuiltCourse>) => void` | `src/screens/assessment/Assessment.tsx` |
| `mockConcepts` | `(topic: string) => CourseConcept[]`; always 8 generic names (`'What <topic> is'`, `'Core terms and ideas'`, …), ids `c1`…`c8`, each with the previous one as its only prerequisite | `src/screens/build/BuildCourse.tsx` |
| `newCourseId` | `() => string` | `src/screens/build/BuildCourse.tsx` |
| `whenLabel` | `(iso: string) => string`: `'Now'` (< 60 min), `'Today'`, or a short date | `src/components/AppShell.tsx` |

### 3c. Data defined inside components (not in a data file)

| Data | File |
|---|---|
| Home filter tabs (All / In progress / Reviewing / Completed) | `src/screens/home/HomeFeed.tsx:21` |
| Feed status badge labels | `src/screens/home/FeedPostCard.tsx:8` |
| Feed cover drawings (4 SVGs keyed by `CoverKind`) | `src/screens/home/Covers.tsx` |
| Empty-home suggestion chips and "How it works" steps | `src/screens/home/HomeEmpty.tsx:8`, `:10` |
| Build steps text and timings (`STEP_MS = 1500`, 4 steps) | `src/screens/build/BuildCourse.tsx:13-22` |
| Answer letters and confidence labels | `src/screens/assessment/Assessment.tsx:11-12`, `src/components/AnswerReview.tsx:4-5` |
| Level thresholds for "Your level" (≥85 Advanced, ≥65 Intermediate, ≥40 Beginner, else Novice) | `src/screens/assessment/Assessment.tsx:238` |
| Topic state thresholds (≥75 % Solid, ≥50 % Developing, else To strengthen) | `src/screens/assessment/Assessment.tsx:249` |
| Forgetting-curve inputs (`reviewsAt = [0, 3, 8, 16]`, `strengths = [6, 10, 14, 18]`, `today = 24`) | `src/screens/retention/Retention.tsx:275-277` |
| Memory label thresholds (≥80 Strong, ≥60 Fading, else At risk) and mastery bar colours | `src/screens/retention/Retention.tsx:136`, `:149` |
| Login brand bullet points | `src/screens/login/Login.tsx` |

---

## 4. How mock data reaches the screens

- **Imported directly** in each screen and in `AppShell` from `src/data/placeholder.ts` (see the "Imported by"
  column in 3a). There is no context provider and no data-fetching layer.
- **Props:** `FeedPostCard` gets one `FeedPost` from `HomeFeed`; `CourseChat` gets a `BuiltCourse` from `TutorChat`;
  `Assessment` passes picks/confidence down to its internal `Question` and `Results` components and builds the
  `answers` prop for `AnswerReview`.
- **Store:** `src/data/courseStore.ts` is the only shared store (module state + `useSyncExternalStore` +
  `localStorage`).
- **URL:** topic, level, review mode and course id travel as query parameters (`src/routes.ts`).
- **Nothing is loaded asynchronously.** No screen has a loading state driven by data; the only waiting is the
  simulated timer on the Build screen.
- **No single swap point.** Mock data is imported separately in 10 files
  (`src/components/AppShell.tsx`, `src/components/LevelSelect.tsx`, `src/screens/home/HomeFeed.tsx`,
  `src/screens/home/FeedPostCard.tsx`, `src/screens/home/Covers.tsx`, `src/screens/newchat/NewChat.tsx`,
  `src/screens/build/BuildCourse.tsx`, `src/screens/assessment/Assessment.tsx`, `src/screens/tutor/TutorChat.tsx`,
  `src/screens/retention/Retention.tsx`; `FeedPostCard.tsx` and `Covers.tsx` import types only).
  `src/api/client.ts` exposes `api.createCourse`, `getCourse`, `start`, `submitAttempts`, `next`, `state`,
  `advance`, `newSession`, `health`, but nothing calls it.

---

## 5. Per screen: what is shown and where it comes from

### Shared left navigation (`src/components/AppShell.tsx`), on every screen except Assessment

| Shown | Source |
|---|---|
| Logo | `src/assets/logo.png`; links to `/` |
| Home / My courses / Retention | hard-coded `navItems` (line 11) |
| NEW CHAT | hard-coded; links to `/new` |
| Previous chats list | built courses (`useBuiltCourses()`: `topic`, `whenLabel(createdAt)`, `level` or "Assessment pending") then `previousChats` (`title`, `meta`) |
| Settings, profile name, initials | Settings hard-coded; `user.name`, `user.initials` |

| Button | Goes to |
|---|---|
| Logo, Home | `/` |
| My courses | `/chat/<first chat id>` (newest built course, else `backprop`), line 38 |
| Retention | `/retention` |
| NEW CHAT | `/new` |
| Each previous chat | `/chat/<id>` |
| Settings, profile | `href="#"` (nothing) |

### Home (`src/screens/home/HomeFeed.tsx`, `src/screens/home/FeedPostCard.tsx`)

| Shown | Source |
|---|---|
| "Home", tab labels | hard-coded in JSX / `tabs` const |
| Composer avatar | `user.initials` |
| Composer placeholder, "ASK" | hard-coded in JSX |
| Level chip | `levels[].name` via `LevelSelect` (default `'intermediate'`) |
| Card author "OnlyNerds Agent" + check | hard-coded in JSX |
| Card byline | `post.topic · post.time` |
| Status badge | `post.status` → label map in `FeedPostCard.tsx:8` |
| Card text, title | `post.text`, `post.title` |
| Cover drawing | `post.cover` → `Covers.tsx` |
| Pills | `post.chapters`, `post.duration` |
| Progress segments | `post.totalSegments`, `post.doneSegments` |
| Stats line | `post.progress`, `post.retention`, `post.next` ("Retention:", "Next review:" hard-coded) |
| CTA label | `post.cta` |
| Chat count | `post.chats` |
| Search box | hard-coded placeholder, no behaviour |
| Due for review rows | `dueReviews[].title`, `.due` |
| Overdue count, rows | `overdueReviews.length`, `overdueReviews[].title`, `.late` |
| Overdue note text | hard-coded in JSX |

| Button | Goes to |
|---|---|
| Filter tabs | client-side filter on `post.status` |
| Level chip | opens dropdown (`LevelSelect`) |
| ASK (disabled until a topic is typed) | `/build?topic=<text>&level=<key>` |
| Card cover, chat-count icon | `/chat/<post.chatId>` |
| Card CTA | `reviewLink(post.topic)` if `status === 'review'`, else `/chat/<post.chatId>` |
| Quiz (card footer) | `/assessment?mode=review&topic=<post.topic>` |
| Review, Save, Share, "⋯" (card) | nothing (`type="button"`, no handler) |
| See all | `/retention` |
| Each due / overdue row | `/assessment?mode=review&topic=<row title>` |
| Catch up now | `/assessment?mode=review&topic=Overdue%20reviews` |

### Home empty (`src/screens/home/HomeEmpty.tsx`), shown at `/?empty`

| Shown | Source |
|---|---|
| Composer | same `Composer` as Home |
| "No courses yet", body text, illustration | hard-coded in JSX |
| Suggestion chips | `emptyPrompts` (line 8) |
| "How it works" steps | `steps` (line 10) |
| "Nothing due yet", "No mastery data", ring `--` | hard-coded in JSX |

| Button | Goes to |
|---|---|
| ASK | `/build?topic=…&level=…` |
| Start your first chat, Take an assessment | `/new` |
| Suggestion chip | `/new?topic=<chip>` |

### New chat (`src/screens/newchat/NewChat.tsx`)

| Shown | Source |
|---|---|
| Heading, sub-text, placeholder | hard-coded in JSX |
| Topic prefill | `?topic=` |
| Level buttons, bars, description | `levels[]` (`name`, `bars`, `desc`); initial from `?level=` else `'intermediate'` |

| Button | Goes to |
|---|---|
| ✕ | `/` |
| Send arrow (disabled until a topic is typed; Enter also submits) | `/build?topic=<text>&level=<key>` |
| Level buttons | set level in component state |

### Build course (`src/screens/build/BuildCourse.tsx`)

| Shown | Source |
|---|---|
| Header title, sub | `?topic=`; level name from `levels` by `?level=` + " level · New course" |
| Building: title, step message, step list, time hint | hard-coded `STEPS` and JSX ("This usually takes 1 to 3 minutes.") |
| Ready: concept count and list | `course.concepts` (from `mockConcepts(topic)` or an existing course via `findCourse`) |
| Ready: message variant | `course.assessed` |
| Failed: title and text | hard-coded in JSX |

| Button | Goes to |
|---|---|
| ← | `/new` |
| Start the assessment (not yet assessed) | `/assessment?topic=…&level=<name>&course=<id>` |
| Open my course (already assessed) | `/chat/<id>` |
| Try again | restarts the timer; drops `simulate=fail` from the URL |
| Change topic | `/new?topic=…&level=<key>` |

### Assessment, question view (`src/screens/assessment/Assessment.tsx`, `Question`)

| Shown | Source |
|---|---|
| Header title | `?topic=` (default `assessment.title`) + " assessment" or " review" |
| Header sub | `` `${?level} level` `` (default `assessment.level`), or "Spaced review" in review mode |
| "Question n of N", topic, progress bar | index, `assessment.questions.length`, `questions[i].topic` |
| Question text, options | `questions[i].text`, `questions[i].options` |
| Confidence buttons | hard-coded labels; **only when `mode=review`** (line 97) |
| Skip link, hint text | hard-coded in JSX |

| Button | Effect |
|---|---|
| Logo | `/` |
| ✕ | `/chat/<course>` if `?course=`, else `/` in review mode, else `/new` (line 30) |
| Option | records the pick |
| Confidence (review only) | records confidence; clicking the selected one again clears it |
| I'm not sure, skip this one | records a skip and moves on |
| Back (hidden on Q1) | previous question |
| Next / See my results (disabled until answered or skipped) | next question / results view |

### Assessment results (`src/screens/assessment/Assessment.tsx`, `Results`; `src/components/AnswerReview.tsx`)

| Shown | Source |
|---|---|
| Score ring %, "n of N" | computed: correct count / `questions.length` |
| "Assessment complete" / "Review complete" | `mode` |
| "Your level: …" | computed from the % (line 238) |
| Summary line | computed count of non-Solid topics |
| Totals: Correct / To strengthen / Skipped | computed |
| Question by question (filter All / Wrong / Skipped) | `questions[]` + picks + confidence: picked option red/green, correct option green, confidence chip, Correct/Wrong/Skipped label, "Certain, but wrong" / "Unsure, but right" callouts |
| Results by topic | computed per `questions[].topic` |
| Confidence check box | computed; shown only if any confidence was given (so review mode only) |
| "Re-assessment scheduled…" | hard-coded in JSX |
| "Your learning materials are ready", count | hard-coded title; `assessment.materialCount` |

| Button | Goes to |
|---|---|
| Open my learning materials | `/chat/<course>` if `?course=`, else the `previousChats` entry whose `topic` or `title` equals `?topic=`, else `/chat/backprop` (lines 256-257) |
| Filter tabs | client-side filter |

### Course page, placeholder chats (`src/screens/tutor/TutorChat.tsx`, `PlaceholderChat`)

Used when `:chatId` is not a built course.

| Shown | Source |
|---|---|
| Header title, sub | `chat.title`; `` `${chat.topic} · ${chat.level} · Learning materials` `` |
| Review-due banner (only if `chat.reviewDue`) | hard-coded heading; `chat.nextCheck.what` |
| Curated card | `chat.courseTitle`; `materials.length`; "about 38 min" **hard-coded**; done count from `materials[].status` |
| Material cards | `materials[]`: `title`, `kind`, `source`, `time`, `status` (label map line 13) |
| Mastery ring, level, delta | `tutorMastery.pct`, `.level`, `.delta`; topic line `chat.topic` |
| Topic bars | `tutorMastery.topics[]` (amber when `pct < 50`) |
| Currently learning rows | `materials[]` |
| Next assessment card | `chat.nextCheck.month`, `.day`, `.when`, `.what`; amber style when `chat.reviewDue` |

The same `materials` and `tutorMastery` are shown for **every** placeholder chat.

| Button | Goes to |
|---|---|
| ← | `/` |
| Take the quiz (banner and card; only when `reviewDue`) | `/assessment?mode=review&topic=<chat.topic>` |
| Continue learning, each Open, each Currently-learning row | `href="#"` (nothing) |
| "⋯" | nothing |

### Course page, built courses (`src/screens/tutor/CourseChat.tsx`)

Used when `:chatId` matches a `BuiltCourse`.

| Shown | Source |
|---|---|
| Header title, sub | `course.topic`; `` `${course.level} · Your course` `` |
| "Take the short assessment" card (only if `!assessed`) | hard-coded text; `course.concepts.length` |
| Course card | `course.topic`, `course.concepts.length`, `course.score` or "assessment not taken yet" |
| Concept cards | `course.concepts[]`: `name`; prerequisites resolved to names ("Builds on …" / "Starting point"); status: first concept "In progress" when assessed, all others "Up next" |
| Mastery panel | `course.score` (ring) when assessed, else empty state |
| Next assessment card (only when assessed) | date = `createdAt` + 1 day; text built from the first two concept names |

| Button | Goes to |
|---|---|
| ← | `/` |
| Start the assessment | `/assessment?topic=…&level=…&course=<id>` |
| Continue learning, each Open (assessed only) | `href="#"` (nothing) |
| "⋯" | nothing |

### Retention (`src/screens/retention/Retention.tsx`)

| Shown | Source |
|---|---|
| Title, sub-text | hard-coded in JSX |
| KPI cards | `retention.kpis[]` (`icon`, `label`, `value`, `delta`, `good`, `sub`) |
| Mastery overview ring, level, delta, note | `retention.masteryPct`, `.masteryLevel`, `.masteryDelta`, `.masteryNote` |
| Stacked bar + legend | `retention.levels[]` |
| Memory strength counts | `retention.memory.strong`, `.fading`, `.atRisk` |
| Forgetting curve | title from `retention.memory.curveConcept`; curve and "Strength is now N %" computed from hard-coded inputs (lines 275-277) |
| Concept progress table (course filter tabs) | `retention.concepts[]` (`name`, `course`, `pct`, `strength`); tabs derived from distinct `course` values |
| Reviews: Overdue count and rows | `retention.overdue.length`, `retention.overdue[]` |
| Reviews: Upcoming rows | `retention.upcoming[]` (first row styled as "today") |
| Needs attention | `retention.attention[]` (rank = list position) |
| Misconception insights | `retention.misconceptions.active`, `.resolvedThisMonth`, `.items[]` (`recurring` → "Recurring"/"Improving") |

| Button | Goes to |
|---|---|
| Start review | `/assessment?mode=review&topic=Due%20reviews` |
| Course filter tabs | client-side filter |
| Overdue "Review" | `/assessment?mode=review&topic=<name>` |
| Strengthen | `/chat/<attention.chatId>` |
| See the fix | `/chat/<misconception.chatId>` |

### Log in (`src/screens/login/Login.tsx`), not routed

| Shown | Source |
|---|---|
| Heading, sub-text, CTA label | `mode` prop (`'login'` default or `'signup'`) |
| Fields: Full name (signup only), Email, Password with Show/Hide | component state |
| Brand panel and 4 points | hard-coded in the file |

| Button | Goes to |
|---|---|
| Logo | `href="/"` |
| LOG IN / CREATE ACCOUNT | calls optional `onSubmit({ name, email, password })` prop; nothing passes it |
| Terms of Service, Privacy Policy | `href="#"` |

---

## 6. User actions and where state is kept

| Screen | User can | Kept in |
|---|---|---|
| Home | pick a filter tab; type a topic; pick a level; press ASK | component state (`HomeFeed`, `Composer`, `LevelSelect` open/closed); then URL |
| Home empty | same composer; click a chip | component state; URL |
| New chat | type a topic; pick a level; send | component state, initialised from URL `?topic`, `?level`; then URL |
| Build course | wait; start assessment; try again; change topic | component state (`phase`, `step`, `attempt`); new course saved to `courseStore` (→ `localStorage`) |
| Assessment | pick an option; pick/clear confidence (review only); skip; back; next; see results | component state (`q`, `picks[]`, `conf[]`, `done`) in `Assessment`; on results, `updateCourse(id, { assessed: true, score })` when `?course=` is set |
| Results | filter the answer review | component state in `AnswerReview` |
| Course page | open materials / concepts (no effect); take the quiz | nothing stored |
| Retention | pick a course filter | component state |
| Log in | type name/email/password; show/hide password | component state (not routed) |

Persistence across a reload:
- **Persists:** built courses (`localStorage['onlynerds.courses']`, `src/data/courseStore.ts:24`), including
  `assessed` and `score`. URL query parameters (topic, level, mode, course).
- **Lost:** assessment progress (answers, confidence, current question), Home tab, level dropdown choice on Home,
  Retention filter, Build screen phase (a reload of `/build` either rebuilds or, if the topic+level already exists,
  shows Ready at once via `findCourse`).
- `src/api/client.ts` also defines `localStorage['onlynerds.password']` helpers, but they are unused.

---

## 7. The quiz / assessment flow as built

All in `src/screens/assessment/Assessment.tsx`.

- **Questions:** always `assessment.questions` (8 fixed questions from `src/data/placeholder.ts`), regardless of
  topic, level or mode. One question per screen.
- **Answer:** `picks[q] = optionIndex`. **Skip:** `picks[q] = -1` (`SKIPPED`), confidence cleared, then advance.
- **Confidence:** `conf[q] = 0 | 1 | 2` (Not sure / Fairly sure / Certain). Shown only when `mode=review`
  (line 97). Choosing a different option clears it; clicking the selected confidence again clears it (lines 32-46).
- **Back:** works (`setQ(q - 1)`); earlier answers are kept. **Next** is disabled until the question is answered
  or skipped; a skipped question counts as answered.
- **Submit:** "See my results" on the last question sets `done = true`. Nothing is sent anywhere. If `?course=` is
  present, `updateCourse(courseId, { assessed: true, score: pct })` runs in an effect (lines 260-262).
- **Results numbers** (lines 226-257): correct = `picks[i] === questions[i].correct`; skipped = `-1` or unset;
  wrong = total − correct − skipped; % = correct / total; level and topic states from fixed thresholds;
  "Certain, but wrong" = wrong with confidence 2; "Unsure, but right" = right with confidence 0.
- **Per-question review:** `AnswerReview` receives each question plus `picked` (undefined when skipped) and
  `confidence`.
- **Review / quiz route** reuses the same component with `?mode=review`: same questions; differences are the
  header wording, "Review complete", confidence shown, ✕ goes to `/`.
- **Lesson text plus practice questions together:** **no screen does this.** The course pages list materials or
  concepts only; their Open / Continue buttons are `href="#"`.

---

## 8. Shared components

| Component | File | Props / purpose |
|---|---|---|
| `AppShell` | `src/components/AppShell.tsx` | `{ active?: 'home' \| 'courses' \| 'retention'; activeChatId?: string; children }`: left nav + page frame |
| `Icon` | `src/components/Icon.tsx` | `{ name: IconName; size?: number = 22; strokeWidth?: number = 1.7; color?: string }`: 27 inline SVG icons |
| `Ring` | `src/components/Ring.tsx` | `{ pct: number \| null; size: number; stroke: number; label?: string; children? }`: circular progress, centred children |
| `LevelSelect` | `src/components/LevelSelect.tsx` | `{ value: LevelKey; onChange(level) }`: "Level: X" chip with a 4-option menu |
| `AnswerReview` | `src/components/AnswerReview.tsx` | `{ answers: ReviewedAnswer[] }` where `ReviewedAnswer = { topic: string; text: string; options: string[]; correct: number; picked: number \| undefined; confidence: number \| undefined }`: per-question feedback with filters |
| `FeedPostCard` | `src/screens/home/FeedPostCard.tsx` | `{ post: FeedPost }`: one Home feed card |
| `Cover` | `src/screens/home/Covers.tsx` | `{ kind: CoverKind }`: decorative course cover |
| `Composer`, `SearchBox` | `src/screens/home/HomeFeed.tsx` | no props: Home input box; search input (no behaviour) |
| `Question`, `Results` | `src/screens/assessment/Assessment.tsx` (file-local) | question view and results view; not exported |
| `PlaceholderChat` | `src/screens/tutor/TutorChat.tsx` (file-local) | `{ chatId }`: course page for placeholder chats |
| `CourseChat` | `src/screens/tutor/CourseChat.tsx` | `{ course: BuiltCourse }`: course page for built courses |
| `ForgettingCurve` | `src/screens/retention/Retention.tsx` (file-local) | `{ concept: string }`: SVG curve from hard-coded inputs |
| Cards / buttons | `src/index.css` | CSS classes only (`.card`, `.btn`, `.btn-primary`, `.btn-soft`, `.chip`, `.icon-btn`, `.row-link`, `.av`, `.label`); no React components |

---

## 9. Not built yet

**Missing screens**
- Lesson screen (lesson text + practice questions + "Check answers" inline feedback): not present
  (see section 7).
- Material / article / video viewer: Open buttons are `href="#"` (`src/screens/tutor/TutorChat.tsx`,
  `src/screens/tutor/CourseChat.tsx`).
- My courses list: the nav item opens the newest chat instead (`src/components/AppShell.tsx:37-38`).
- Settings and Profile: `href="#"` (`src/components/AppShell.tsx`).
- Session end ("Come back tomorrow") and Done ("Everything covered") states from `docs/FRONTEND_FLOW.md`: not
  present.
- Control panel (clock advance, new session): not present.
- Log in is built but not routed (`src/screens/login/Login.tsx`, `src/App.tsx`).

**Missing states**
- Loading: none tied to data (no data is fetched). Only the Build screen has a simulated "Building" state.
- Error: only the Build screen's simulated Failed state (`?simulate=fail`). No error UI elsewhere; unknown
  `/chat/:id` falls back to the first chat instead of an error (`src/data/placeholder.ts:103`).
- Empty: Home empty is reachable only with `?empty` (`src/screens/home/HomeFeed.tsx:32`); empty mastery panels in
  `src/screens/home/HomeEmpty.tsx` and `src/screens/tutor/CourseChat.tsx`; the answer-review filter shows "Nothing
  wrong. Nice." / "Nothing skipped." (`src/components/AnswerReview.tsx`). Retention, Home feed lists and course
  pages have no empty states.

**Buttons that do nothing**

| Button | File |
|---|---|
| Card "Review", "Save", "Share", "⋯" | `src/screens/home/FeedPostCard.tsx:44-46`, `:97-107` |
| Search input (no handler) | `src/screens/home/HomeFeed.tsx:119` |
| Settings, profile (`href="#"`) | `src/components/AppShell.tsx:83`, `:87` |
| Continue learning, Open, Currently-learning rows (`href="#"`), "⋯" | `src/screens/tutor/TutorChat.tsx:72`, `:90`, `:140`, `:39` |
| Continue learning, Open (`href="#"`), "⋯" | `src/screens/tutor/CourseChat.tsx:73`, `:96`, `:36` |
| Terms of Service, Privacy Policy (`href="#"`) | `src/screens/login/Login.tsx:107-108` |
| LOG IN / CREATE ACCOUNT (no `onSubmit` passed) | `src/screens/login/Login.tsx` |

**TODO / FIXME:** none. `grep -rn 'TODO\|FIXME\|XXX\|HACK' src` returns no matches.

**Unclear / worth confirming with the frontend owner**
- `Retention` "Start review" passes the literal topic `'Due reviews'`, and "Catch up now" passes
  `'Overdue reviews'`; they are labels, not concept ids (`src/screens/retention/Retention.tsx:24`,
  `src/screens/home/HomeFeed.tsx:172`).
- Built-course `level` stores the level **name** ("Beginner"), while URLs carry the level **key** (`beginner`)
  on `/new` and `/build` but the **name** on `/assessment` (`src/routes.ts`, `src/data/courseStore.ts:15`).

---

## 10. `src/` file tree (two levels)

```text
src/
├── App.tsx
├── main.tsx
├── index.css
├── routes.ts
├── api/
│   ├── client.ts          (unused)
│   └── types.ts           (copy of docs/types.ts, unused)
├── assets/
│   ├── logo.png
│   └── mark.png
├── components/
│   ├── AnswerReview.tsx / .css
│   ├── AppShell.tsx / .css
│   ├── Icon.tsx
│   ├── LevelSelect.tsx / .css
│   └── Ring.tsx
├── data/
│   ├── courseStore.ts
│   └── placeholder.ts
└── screens/
    ├── assessment/        Assessment.tsx, Assessment.css
    ├── build/             BuildCourse.tsx, BuildCourse.css
    ├── home/              HomeFeed.tsx, HomeFeed.css, HomeEmpty.tsx, FeedPostCard.tsx, Covers.tsx
    ├── login/             Login.tsx, Login.css
    ├── newchat/           NewChat.tsx, NewChat.css
    ├── retention/         Retention.tsx, Retention.css
    └── tutor/             TutorChat.tsx, TutorChat.css, CourseChat.tsx
```
