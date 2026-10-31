import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { api, errorText } from '../../api/client'
import { conceptsOf, levelName } from '../../api/format'
import { refreshCourses, useCourses } from '../../api/hooks'
import type { CreateCourseIn, CreateCourseOut } from '../../api/types'
import mark from '../../assets/mark.png'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { ErrorBox, Loading } from '../../components/Status'
import { chatLink, diagnosticLink } from '../../routes'
import './BuildCourse.css'

const POLL_MS = 2000
type LevelKey = NonNullable<CreateCourseIn['level']>

// POST /courses is deduped while in flight (StrictMode runs effects twice in dev).
const creating = new Map<string, Promise<CreateCourseOut>>()
function createOnce(body: CreateCourseIn) {
  const key = `${body.prompt}|${body.level}`
  let p = creating.get(key)
  if (!p) {
    p = api.createCourse(body).finally(() => creating.delete(key))
    creating.set(key, p)
  }
  return p
}

const watchUrl = (id: string, topic: string, level: string) =>
  `/build?course=${encodeURIComponent(id)}&topic=${encodeURIComponent(topic)}&level=${encodeURIComponent(level)}`

// New chat -> POST /courses, then poll GET /courses/{id} every 2 s: Building, Ready or Failed.
// The URL switches to ?course=<id> after creating, so a reload keeps polling instead of re-posting.
export function BuildCourse() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const courseId = params.get('course')
  const topicParam = (params.get('topic') ?? '').trim()
  const levelParam = (params.get('level') ?? 'intermediate') as LevelKey

  const { courses } = useCourses()
  const summary = courses?.find((c) => c.course_id === courseId)
  const [course, setCourse] = useState<CreateCourseOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const started = useRef(0)

  // 1. No course yet: create it, then move to ?course=<id>.
  useEffect(() => {
    if (courseId || !topicParam) return
    let live = true
    createOnce({ prompt: topicParam, level: levelParam }).then(
      (c) => {
        if (!live) return
        void refreshCourses()
        navigate(watchUrl(c.course_id, topicParam, levelParam), { replace: true })
      },
      (e) => live && setError(errorText(e)),
    )
    return () => {
      live = false
    }
  }, [courseId, topicParam, levelParam, navigate])

  // 2. Poll while generating; stop on ready, failed or unmount.
  useEffect(() => {
    if (!courseId) return
    let live = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const poll = () =>
      api.getCourse(courseId).then(
        (c) => {
          if (!live) return
          setCourse(c)
          setError(null)
          if (c.status === 'generating') timer = setTimeout(poll, POLL_MS)
          else void refreshCourses()
        },
        (e) => {
          if (!live) return
          setError(errorText(e))
          timer = setTimeout(poll, POLL_MS * 2)
        },
      )
    void poll()
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [courseId])

  const generating = !course || course.status === 'generating'
  useEffect(() => {
    if (!generating) return
    if (!started.current) started.current = Date.now()
    const t = setInterval(() => setElapsed(Math.round((Date.now() - started.current) / 1000)), 1000)
    return () => clearInterval(t)
  }, [generating])

  if (!courseId && !topicParam) return <Navigate to="/new" replace />

  const topic = course?.topic || summary?.topic || topicParam
  const level = (summary?.level ?? levelParam) as LevelKey
  const concepts = conceptsOf(course)

  // Failed: POST /courses again for the same topic and level.
  async function tryAgain() {
    if (retrying) return
    setRetrying(true)
    setError(null)
    try {
      const c = await api.createCourse({ prompt: topic, level })
      started.current = Date.now()
      setCourse(c)
      void refreshCourses()
      navigate(watchUrl(c.course_id, topic, level), { replace: true })
    } catch (e) {
      setError(errorText(e))
    } finally {
      setRetrying(false)
    }
  }

  return (
    <AppShell activeChatId={courseId ?? undefined}>
      <main className="build">
        <header className="build__header">
          <Link to="/new" className="icon-btn" aria-label="Back to new chat">
            <Icon name="back" strokeWidth={2} />
          </Link>
          <div className="build__heading">
            <h1>{topic}</h1>
            <div>{levelName(level)} level · New course</div>
          </div>
        </header>

        <div className="build__body">
          {error && !course && <ErrorBox message={`Could not start building: ${error}`} onRetry={tryAgain} />}
          {error && course && <Loading label={`Connection problem, retrying… (${error})`} compact />}
          {!error && !course && <Loading label={courseId ? 'Loading your course…' : 'Sending your topic…'} />}

          {course && generating && (
            <section className="card build__card" aria-live="polite" aria-busy="true">
              <div className="build__anim" aria-hidden="true">
                <span className="build__ring" />
                <img src={mark} alt="" />
              </div>
              <h2>Building your course</h2>
              <p className="build__message">Mapping the concepts and writing questions…</p>
              <p className="build__hint">
                <Icon name="clock" size={16} strokeWidth={1.8} />
                This usually takes 1 to 3 minutes.
                {elapsed > 0 && ` ${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')} so far.`}
              </p>
            </section>
          )}

          {course?.status === 'ready' && (
            <section className="card build__card build__card--ready" aria-live="polite">
              <div className="build__ready-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 12.5 4.5 4.5L19 7.5" />
                </svg>
              </div>
              <h2>Your course is ready</h2>
              <p className="build__message">
                {concepts.length} concepts, in the order you'll learn them.
                {summary?.started
                  ? ' You already took the assessment for this one.'
                  : ' A short assessment comes first, one question per concept, so I can skip what you already know.'}
              </p>
              <ol className="build__concepts">
                {concepts.map((c, i) => (
                  <li key={c.id} className="build__concept" style={{ animationDelay: `${i * 60}ms` }}>
                    <span className="build__concept-n">{i + 1}</span>
                    {c.name}
                  </li>
                ))}
              </ol>
              {summary?.started ? (
                <Link to={chatLink(course.course_id)} className="btn btn-primary build__cta">
                  Open my course
                </Link>
              ) : (
                <Link to={diagnosticLink(course.course_id)} className="btn btn-primary build__cta">
                  Start the assessment
                </Link>
              )}
            </section>
          )}

          {course?.status === 'failed' && (
            <section className="card build__card build__card--failed" role="alert">
              <div className="build__fail-icon" aria-hidden="true">
                <Icon name="alert" size={28} strokeWidth={1.8} />
              </div>
              <h2>Something went wrong building this course</h2>
              <p className="build__message">It wasn't anything you did. Trying again usually works.</p>
              <div className="build__actions">
                <button type="button" className="btn btn-primary" onClick={tryAgain} disabled={retrying}>
                  {retrying ? 'Trying again…' : 'Try again'}
                </button>
                <Link to={`/new?topic=${encodeURIComponent(topic)}&level=${level}`} className="btn btn-soft">
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
