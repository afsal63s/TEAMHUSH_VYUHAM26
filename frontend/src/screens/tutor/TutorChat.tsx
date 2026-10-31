import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router'
import { api, ApiError, errorText, setCurrentCourse } from '../../api/client'
import { conceptsOf, dayDistance, hostOf, levelFromPct, levelName, mean, monthDay, nameMap, parseUtc } from '../../api/format'
import { refreshCourses, useAsync, useControlPanelSignal, useCourse, useCourses } from '../../api/hooks'
import type { MasteryOut, Resource, ResourcesResponse, StepOut } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { Ring } from '../../components/Ring'
import { ErrorBox, Loading } from '../../components/Status'
import { buildCourseLink, diagnosticLink, reviewLink } from '../../routes'
import { StepCard } from './StepCard'
// The right panel (.rail) styles are shared with Home.
import '../home/HomeFeed.css'
import './TutorChat.css'

const RESOURCES_POLL_MS = 5000
const LESSON_RETRY_MS = 1500
const LESSON_RETRIES = 4

// Links the learner opened, kept in the browser: opened = Done.
const OPENED_KEY = 'onlynerds.opened'
function readOpened(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(OPENED_KEY) ?? '[]') as string[])
  } catch {
    return new Set()
  }
}
function markOpened(url: string) {
  const s = readOpened()
  s.add(url)
  try {
    localStorage.setItem(OPENED_KEY, JSON.stringify([...s]))
  } catch {
    // Storage blocked: Done marks last until reload.
  }
  return s
}

type StepState =
  | { kind: 'loading' }
  | { kind: 'step'; data: StepOut }
  | { kind: 'not-started' }
  | { kind: 'error'; message: string }

/** GET .../next; a lesson that came back empty is asked for again. */
async function fetchStep(courseId: string): Promise<StepState> {
  try {
    let s = await api.next(courseId)
    for (let i = 0; i < LESSON_RETRIES && (s.step.kind === 'lesson' || s.step.kind === 'fallback') && !s.lesson; i++) {
      await new Promise((r) => setTimeout(r, LESSON_RETRY_MS))
      s = await api.next(courseId)
    }
    return { kind: 'step', data: s }
  } catch (e) {
    // 409: diagnostic not answered yet; 404: learner not started.
    if (e instanceof ApiError && (e.status === 409 || /not started/i.test(String(e.detail)))) return { kind: 'not-started' }
    return { kind: 'error', message: errorText(e) }
  }
}

// Remount per course, so switching courses starts from a clean loading state.
export function TutorChat() {
  const { chatId = '' } = useParams()
  return <CoursePage key={chatId} courseId={chatId} />
}

function CoursePage({ courseId }: { courseId: string }) {
  const course = useCourse(courseId)
  const name = nameMap(course.data)
  const { courses } = useCourses()
  const summary = courses?.find((c) => c.course_id === courseId)

  const [step, setStep] = useState<StepState>({ kind: 'loading' })
  // Fallback "now" until GET .../state returns the learner's simulated now.
  const [mountedAt] = useState(() => new Date())
  const stepCard = useRef<HTMLDivElement>(null)

  useEffect(() => setCurrentCourse(courseId), [courseId])

  useEffect(() => {
    let live = true
    void fetchStep(courseId).then((st) => live && setStep(st))
    return () => {
      live = false
    }
  }, [courseId])

  const loadNext = useCallback(async () => {
    setStep({ kind: 'loading' })
    setStep(await fetchStep(courseId))
  }, [courseId])

  const state = useAsync<MasteryOut | null>(
    () =>
      api.state(courseId).catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }),
    [courseId],
  )

  // GET .../resources, polled every 5 s while any concept is still pending.
  const [resources, setResources] = useState<ResourcesResponse | null>(null)
  const [resourcesError, setResourcesError] = useState<string | null>(null)
  const [resTick, setResTick] = useState(0)
  useEffect(() => {
    let live = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const poll = () =>
      api.resources(courseId).then(
        (r) => {
          if (!live) return
          setResources(r)
          setResourcesError(null)
          if (Object.values(r).some((c) => c.status === 'pending')) timer = setTimeout(poll, RESOURCES_POLL_MS)
        },
        (e) => {
          if (!live) return
          if (e instanceof ApiError && e.status === 404) setResources({})
          else setResourcesError(errorText(e))
        },
      )
    void poll()
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [courseId, resTick])

  const afterAnswer = () => {
    state.reload()
    setResTick((t) => t + 1)
    void refreshCourses()
  }

  // Control panel jumped the clock / started a session / reset: drop unsent answers and re-ask.
  useControlPanelSignal(() => {
    void loadNext()
    state.reload()
    setResTick((t) => t + 1)
  })

  const [opened, setOpened] = useState(readOpened)

  if (course.data?.status === 'generating') return <Navigate to={buildCourseLink(courseId)} replace />

  const s = state.data ?? null
  const concepts = conceptsOf(course.data)
  const now = parseUtc(s?.now) ?? mountedAt
  const dueEntries = Object.entries(s?.due ?? {}).map(([id, at]) => ({ id, at: parseUtc(at) }))
  const dueNow = dueEntries.some((d) => d.at && d.at <= now)
  const nextDue = parseUtc(s?.next_due)
  const nextDueNames = nextDue
    ? dueEntries.filter((d) => d.at && d.at.toDateString() === nextDue.toDateString()).map((d) => name(d.id))
    : []

  const masteries = (s?.concepts ?? []).map((c) => c.p_mastery ?? 0)
  const avgMastery = mean(masteries)
  const hist = s?.history ?? []
  const delta = hist.length >= 2 ? hist[hist.length - 1].avg_mastery - hist[hist.length - 2].avg_mastery : null

  const materials = flattenResources(resources, s?.roadmap ?? concepts.map((c) => c.id), name)
  const pending = Object.entries(resources ?? {}).filter(([, r]) => r.status === 'pending').map(([id]) => name(id))
  const doneCount = materials.filter((m) => opened.has(m.url)).length

  const continueLearning = () => {
    stepCard.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    if (step.kind !== 'step') void loadNext()
  }

  return (
    <AppShell activeChatId={courseId}>
      <main className="tutor">
        <header className="tutor__header">
          <Link to="/" className="icon-btn" aria-label="Back to Home">
            <Icon name="back" strokeWidth={2} />
          </Link>
          <div className="tutor__heading">
            <h1>{course.data?.topic ?? summary?.topic ?? 'Your course'}</h1>
            <div>{summary ? `${levelName(summary.level)} · Your course` : 'Your course'}</div>
          </div>
        </header>

        <div className="tutor__body">
          {course.error && <ErrorBox message={course.error} onRetry={course.reload} />}

          {dueNow && step.kind === 'step' && step.data.step.kind !== 'review' && (
            <section className="tutor__due" aria-labelledby="due">
              <div className="tutor__due-icon" aria-hidden="true">
                <Icon name="clock" strokeWidth={1.8} />
              </div>
              <div className="tutor__due-text">
                <div className="tutor__due-kicker">Review due now</div>
                <h2 id="due">Time for a quick recall check</h2>
                <div>A few questions, about 5 minutes.</div>
              </div>
              <Link to={reviewLink(courseId)} className="btn btn-primary">
                Take the quiz
              </Link>
            </section>
          )}

          <div ref={stepCard} className="tutor__step">
            {step.kind === 'loading' && <Loading label="Getting your next step… (a new lesson can take 5 to 10 seconds)" />}
            {step.kind === 'error' && <ErrorBox message={step.message} onRetry={() => void loadNext()} />}
            {step.kind === 'not-started' && (
              <section className="tutor__curated" aria-labelledby="first">
                <div className="tutor__curated-icon" aria-hidden="true">
                  <Icon name="quiz" size={24} strokeWidth={1.8} />
                </div>
                <div className="tutor__curated-text">
                  <div className="tutor__kicker">First step</div>
                  <h2 id="first">Take the short assessment</h2>
                  <div>One question per concept, so I can skip what you already know.</div>
                </div>
                <Link to={diagnosticLink(courseId)} className="btn btn-primary">
                  Start the assessment
                </Link>
              </section>
            )}
            {step.kind === 'step' && (
              <StepCard
                key={`${step.data.step.kind}:${step.data.step.concept_id}:${(step.data.questions ?? []).map((x) => x.id).join(',')}`}
                courseId={courseId}
                step={step.data}
                name={name}
                nextDue={s?.next_due}
                onAnswered={afterAnswer}
                onContinue={(next) => {
                  setStep({ kind: 'step', data: next })
                  stepCard.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }}
                onKeepGoing={async () => {
                  await api.newSession(courseId)
                  await loadNext()
                  state.reload()
                }}
              />
            )}
          </div>

          <section className="tutor__curated tutor__curated--quiet">
            <div className="tutor__curated-icon" aria-hidden="true">
              <Icon name="book" size={24} strokeWidth={1.8} />
            </div>
            <div className="tutor__curated-text">
              <div className="tutor__kicker">Curated for you</div>
              <h2>Learning materials</h2>
              <div>
                {materials.length
                  ? `${materials.length} materials · ${doneCount} of ${materials.length} opened`
                  : pending.length
                    ? 'Finding materials…'
                    : 'Materials appear here for the concepts you still need to learn.'}
              </div>
            </div>
            <button type="button" className="btn btn-primary" onClick={continueLearning}>
              Continue learning
            </button>
          </section>

          {resourcesError && <ErrorBox message={`Could not load materials: ${resourcesError}`} onRetry={() => setResTick((t) => t + 1)} />}
          {!resources && !resourcesError && <Loading label="Loading materials…" compact />}
          {pending.length > 0 && <Loading label={`Finding materials for ${pending.join(', ')}…`} compact />}

          {materials.map((m, i) => {
            const done = opened.has(m.url)
            return (
              <article key={m.url} className="card material">
                <span className={`material__n material__n--${done ? 'done' : 'next'}`}>{i + 1}</span>
                <div className="material__icon" aria-hidden="true">
                  <Icon name={m.kind === 'video' ? 'play' : 'article'} strokeWidth={1.8} />
                </div>
                <div className="material__text">
                  <div className="material__title">{m.title}</div>
                  <div className="material__meta">
                    {m.kind === 'video' ? 'Video' : 'Article'} · {hostOf(m.url)} · {m.concept}
                  </div>
                </div>
                <span className={`status status--${done ? 'done' : 'next'}`}>{done ? 'Done' : 'Up next'}</span>
                <a
                  href={m.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-soft"
                  onClick={() => setOpened(markOpened(m.url))}
                >
                  Open
                </a>
              </article>
            )
          })}
        </div>
      </main>

      <aside className="rail">
        <section className="card rail__card tutor__mastery" aria-labelledby="ms">
          <h2 id="ms" className="label">
            Mastery level
          </h2>
          {state.loading && !s && <Loading compact />}
          {state.error && <ErrorBox message={state.error} onRetry={state.reload} />}
          {!state.loading && !state.error && (!s || avgMastery === null) && (
            <div className="rail__empty">
              <Ring pct={null} size={72} stroke={7}>
                <span className="rail__empty-ring">--</span>
              </Ring>
              <div className="rail__empty-title">No mastery data yet</div>
              <div className="rail__empty-text">Take the assessment to see where you stand.</div>
            </div>
          )}
          {s && avgMastery !== null && (
            <>
              <div className="tutor__mastery-head">
                <Ring pct={Math.round(avgMastery * 100)} size={84} stroke={8} label={`${Math.round(avgMastery * 100)} percent mastery`}>
                  <span className="tutor__mastery-pct">{Math.round(avgMastery * 100)}%</span>
                </Ring>
                <div>
                  <div className="tutor__mastery-level">{levelFromPct(avgMastery * 100)}</div>
                  {delta !== null && Math.round(delta * 100) !== 0 && (
                    <div className={delta > 0 ? 'tutor__mastery-delta' : 'tutor__mastery-delta tutor__mastery-delta--down'}>
                      {delta > 0 ? '+' : '−'}
                      {Math.abs(Math.round(delta * 100))} pts since last check
                    </div>
                  )}
                  <div className="tutor__mastery-topic">{course.data?.topic}</div>
                </div>
              </div>
              <div className="tutor__divider" />
              <div className="tutor__topics">
                {s.concepts.map((c) => {
                  const p = Math.round((c.p_mastery ?? 0) * 100)
                  return (
                    <div key={c.concept_id}>
                      <div className="tutor__topic-row">
                        <span>{name(c.concept_id)}</span>
                        <span className="tutor__topic-pct">{p}%</span>
                      </div>
                      <div className="tutor__topic-track">
                        <div
                          className="tutor__topic-fill"
                          style={{ width: `${p}%`, background: p < 50 ? '#D97706' : 'var(--primary)' }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </section>

        {nextDue && (
          <section className={`card rail__card tutor__next${dueNow ? ' tutor__next--due' : ''}`} aria-labelledby="nd">
            <h2 id="nd" className="label">
              Next assessment due
            </h2>
            <div className="tutor__next-row">
              <div className="tutor__cal" aria-hidden="true">
                <div className="tutor__cal-month">{monthDay(nextDue).month}</div>
                <div className="tutor__cal-day">{monthDay(nextDue).day}</div>
              </div>
              <div className="tutor__next-text">
                <div className="tutor__next-when">{dueNow ? 'Due now' : dayDistance(s?.next_due, now)}</div>
                {nextDueNames.length > 0 && <div className="tutor__next-what">Re-check: {nextDueNames.join(', ')}</div>}
              </div>
            </div>
            {dueNow && (
              <Link to={reviewLink(courseId)} className="btn btn-primary tutor__next-btn">
                Take the quiz
              </Link>
            )}
          </section>
        )}
      </aside>
    </AppShell>
  )
}

interface Material extends Resource {
  concept: string
}

/** Every ready resource, in roadmap order, once each. */
function flattenResources(
  res: ResourcesResponse | null,
  order: string[],
  name: (id: string) => string,
): Material[] {
  if (!res) return []
  const ids = [...order.filter((id) => id in res), ...Object.keys(res).filter((id) => !order.includes(id))]
  const seen = new Set<string>()
  const out: Material[] = []
  for (const id of ids) {
    for (const r of res[id]?.resources ?? []) {
      if (seen.has(r.url)) continue
      seen.add(r.url)
      out.push({ ...r, concept: name(id) })
    }
  }
  return out
}
