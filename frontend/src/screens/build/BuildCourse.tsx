import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import mark from '../../assets/mark.png'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { addCourse, findCourse, mockConcepts, newCourseId, type BuiltCourse } from '../../data/courseStore'
import { levels } from '../../data/placeholder'
import { buildLink, diagnosticLink } from '../../routes'
import './BuildCourse.css'

type Phase = 'building' | 'ready' | 'failed'

const STEPS = [
  'Mapping the concepts',
  'Linking prerequisites',
  'Writing questions',
  'Checking the answers',
]

// Simulated timings; the real build takes 1 to 3 minutes.
const STEP_MS = 1500
const BUILD_MS = STEP_MS * STEPS.length

// Course generation after New chat: Building, then Ready (concepts + start) or Failed (try again).
// A topic and level built before opens as Ready straight away (the backend reuses courses the same way).
// `?simulate=fail` previews the failed state.
export function BuildCourse() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const topic = (params.get('topic') ?? '').trim()
  const levelKey = params.get('level') ?? 'intermediate'
  const level = levels.find((l) => l.key === levelKey) ?? levels[2]
  const simulateFail = params.get('simulate') === 'fail'

  const [reused] = useState(() => findCourse(topic, level.name))
  const [phase, setPhase] = useState<Phase>(reused ? 'ready' : 'building')
  const [step, setStep] = useState(0)
  const [course, setCourse] = useState<BuiltCourse | null>(reused ?? null)
  const [attempt, setAttempt] = useState(0)
  const created = useRef<string | null>(null)

  useEffect(() => {
    if (!topic || reused) return
    const tick = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), STEP_MS)
    const finish = setTimeout(() => {
      clearInterval(tick)
      if (simulateFail && attempt === 0) {
        setPhase('failed')
        return
      }
      // Guard against creating the course twice (React StrictMode runs effects twice in dev).
      const key = `${topic}|${level.name}|${attempt}`
      if (created.current === key) return
      created.current = key
      const next: BuiltCourse = {
        id: newCourseId(),
        topic,
        level: level.name,
        concepts: mockConcepts(topic),
        createdAt: new Date().toISOString(),
        assessed: false,
      }
      addCourse(next)
      setCourse(next)
      setPhase('ready')
    }, BUILD_MS)
    return () => {
      clearInterval(tick)
      clearTimeout(finish)
    }
  }, [topic, level.name, simulateFail, attempt, reused])

  if (!topic) return <Navigate to="/new" replace />

  return (
    <AppShell activeChatId={course?.id}>
      <main className="build">
        <header className="build__header">
          <Link to="/new" className="icon-btn" aria-label="Back to new chat">
            <Icon name="back" strokeWidth={2} />
          </Link>
          <div className="build__heading">
            <h1>{topic}</h1>
            <div>{level.name} level · New course</div>
          </div>
        </header>

        <div className="build__body">
          {phase === 'building' && (
            <section className="card build__card" aria-live="polite" aria-busy="true">
              <div className="build__anim" aria-hidden="true">
                <span className="build__ring" />
                <img src={mark} alt="" />
              </div>
              <h2>Building your course</h2>
              <p className="build__message">{STEPS[step]}…</p>
              <ol className="build__steps" aria-label="Progress">
                {STEPS.map((s, i) => (
                  <li
                    key={s}
                    className={i < step ? 'build__step build__step--done' : i === step ? 'build__step build__step--now' : 'build__step'}
                  >
                    <span className="build__step-dot" aria-hidden="true" />
                    {s}
                  </li>
                ))}
              </ol>
              <p className="build__hint">
                <Icon name="clock" size={16} strokeWidth={1.8} />
                This usually takes 1 to 3 minutes.
              </p>
            </section>
          )}

          {phase === 'ready' && course && (
            <section className="card build__card build__card--ready" aria-live="polite">
              <div className="build__ready-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 12.5 4.5 4.5L19 7.5" />
                </svg>
              </div>
              <h2>Your course is ready</h2>
              <p className="build__message">
                {course.concepts.length} concepts, in the order you'll learn them.
                {course.assessed
                  ? ' You already took the assessment for this one.'
                  : ' A short assessment comes first, one question per concept, so I can skip what you already know.'}
              </p>
              <ol className="build__concepts">
                {course.concepts.map((c, i) => (
                  <li key={c.id} className="build__concept" style={{ animationDelay: `${i * 60}ms` }}>
                    <span className="build__concept-n">{i + 1}</span>
                    {c.name}
                  </li>
                ))}
              </ol>
              {course.assessed ? (
                <Link to={`/chat/${course.id}`} className="btn btn-primary build__cta">
                  Open my course
                </Link>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary build__cta"
                  onClick={() => navigate(diagnosticLink(course.topic, course.level, course.id))}
                >
                  Start the assessment
                </button>
              )}
            </section>
          )}

          {phase === 'failed' && (
            <section className="card build__card build__card--failed" role="alert">
              <div className="build__fail-icon" aria-hidden="true">
                <Icon name="alert" size={28} strokeWidth={1.8} />
              </div>
              <h2>Something went wrong building this course</h2>
              <p className="build__message">It wasn't anything you did. Trying again usually works.</p>
              <div className="build__actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    // Drop the preview flag so the retry succeeds.
                    if (simulateFail) navigate(buildLink(topic, level.key), { replace: true })
                    setPhase('building')
                    setStep(0)
                    setAttempt((a) => a + 1)
                  }}
                >
                  Try again
                </button>
                <Link to={`/new?topic=${encodeURIComponent(topic)}&level=${level.key}`} className="btn btn-soft">
                  Change topic
                </Link>
              </div>
            </section>
          )}
        </div>
      </main>
    </AppShell>
  )
}
