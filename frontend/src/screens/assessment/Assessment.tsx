import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router'
import { api, ApiError, errorText, setCurrentCourse } from '../../api/client'
import { levelFromPct, nameMap } from '../../api/format'
import { refreshCourses, useControlPanelSignal, useCourse } from '../../api/hooks'
import type { AttemptResultOut, QuestionPublic, StartOut } from '../../api/types'
import logo from '../../assets/logo.png'
import { AnswerReview } from '../../components/AnswerReview'
import { Icon } from '../../components/Icon'
import { CONFIDENCE_VALUES, confidenceIndex, nextConfidence } from '../../components/confidence'
import { QuestionOptions } from '../../components/QuestionOptions'
import { Ring } from '../../components/Ring'
import { ErrorBox, Loading, MessagesBanner } from '../../components/Status'
import { buildCourseLink, chatLink, diagnosticLink } from '../../routes'
import './Assessment.css'

const SKIPPED = -1

// POST .../start is not idempotent (a second call returns 409), so dedupe it and keep the questions
// in the browser: after a reload mid-diagnostic, start answers 409 and nothing else serves them again.
const startCalls = new Map<string, Promise<StartOut>>()
const diagKey = (cid: string) => `onlynerds.diagnostic.${cid}`
function savedDiagnostic(cid: string): QuestionPublic[] | null {
  try {
    const raw = localStorage.getItem(diagKey(cid))
    return raw ? (JSON.parse(raw) as QuestionPublic[]) : null
  } catch {
    return null
  }
}
function saveDiagnostic(cid: string, qs: QuestionPublic[] | null) {
  try {
    if (qs) localStorage.setItem(diagKey(cid), JSON.stringify(qs))
    else localStorage.removeItem(diagKey(cid))
  } catch {
    // Storage blocked: a reload mid-diagnostic will need "Start over".
  }
}
function startOnce(cid: string) {
  let p = startCalls.get(cid)
  if (!p) {
    p = api.start(cid)
    p.then((r) => saveDiagnostic(cid, r.questions)).catch(() => startCalls.delete(cid))
    startCalls.set(cid, p)
  }
  return p
}

type Load =
  | { kind: 'loading' }
  | { kind: 'ready'; questions: QuestionPublic[]; reviewConcept?: string | null }
  | { kind: 'error'; message: string }
  | { kind: 'redirect'; to: string }

// The diagnostic (POST .../start) or a spaced review (mode=review: GET .../next), one question per screen,
// then results built only from the POST .../attempts response.
export function Assessment() {
  const [params] = useSearchParams()
  const isReview = params.get('mode') === 'review'
  const courseId = params.get('course') ?? ''
  const course = useCourse(courseId || undefined)
  const name = nameMap(course.data)

  const [load, setLoad] = useState<Load>({ kind: 'loading' })
  const [q, setQ] = useState(0)
  const [picks, setPicks] = useState<Record<string, number>>({})
  const [conf, setConf] = useState<Record<string, number | undefined>>({})
  const [result, setResult] = useState<AttemptResultOut | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const submitted = useRef(false)

  const resetAnswers = () => {
    setQ(0)
    setPicks({})
    setConf({})
    setSubmitError(null)
  }

  // Load the questions.
  useEffect(() => {
    if (!courseId) return
    setCurrentCourse(courseId)
    let live = true
    const done = (l: Load) => {
      if (live) setLoad(l)
    }

    if (isReview) {
      api.next(courseId).then(
        (s) =>
          s.step.kind === 'review' && s.questions?.length
            ? done({ kind: 'ready', questions: s.questions, reviewConcept: s.step.concept_id })
            : done({ kind: 'redirect', to: chatLink(courseId) }),
        (e) =>
          e instanceof ApiError && e.status === 409
            ? done({ kind: 'redirect', to: diagnosticLink(courseId) })
            : done({ kind: 'error', message: errorText(e) }),
      )
    } else {
      startOnce(courseId).then(
        (r) => done({ kind: 'ready', questions: r.questions }),
        (e) => {
          if (e instanceof ApiError && e.status === 409) {
            if (/generating|not ready/i.test(String(e.detail))) {
              done({ kind: 'redirect', to: buildCourseLink(courseId) })
              return
            }
            // Already started: finish the saved diagnostic, or go to the course page.
            const saved = savedDiagnostic(courseId)
            done(saved ? { kind: 'ready', questions: saved } : { kind: 'redirect', to: chatLink(courseId) })
            return
          }
          done({ kind: 'error', message: errorText(e) })
        },
      )
    }
    return () => {
      live = false
    }
  }, [courseId, isReview, attempt])

  // The control panel moved the clock or started a session: served questions are stale.
  const onSignal = useCallback(() => {
    if (submitted.current) return
    if (isReview) {
      resetAnswers()
      setNotice('The clock moved, so here are fresh questions.')
      setLoad({ kind: 'loading' })
      setAttempt((a) => a + 1)
    } else {
      setNotice('The clock moved in the control panel. If submitting fails, start the assessment over.')
    }
  }, [isReview])
  useControlPanelSignal(onSignal)

  if (!courseId) return <Navigate to="/" replace />
  if (load.kind === 'redirect') return <Navigate to={load.to} replace />

  const questions = load.kind === 'ready' ? load.questions : []
  const answeredCount = Object.values(picks).filter((p) => p !== SKIPPED).length
  const topic = course.data?.topic ?? 'Your course'

  function pick(qid: string, option: number, confidence?: number) {
    setPicks((p) => ({ ...p, [qid]: option }))
    setConf((c) => ({ ...c, [qid]: nextConfidence(picks[qid], c[qid], option, confidence) }))
  }

  function skip(qid: string) {
    setPicks((p) => ({ ...p, [qid]: SKIPPED }))
    setConf((c) => ({ ...c, [qid]: undefined }))
    if (q < questions.length - 1) setQ(q + 1)
  }

  // Skipped questions are left out; the backend reports them in `skipped`.
  async function submit() {
    if (submitting || answeredCount === 0) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const answers = questions
        .filter((x) => picks[x.id] !== undefined && picks[x.id] !== SKIPPED)
        .map((x) => {
          const c = conf[x.id]
          return {
            question_id: x.id,
            chosen_index: picks[x.id],
            ...(c !== undefined && { confidence: CONFIDENCE_VALUES[c] }),
          }
        })
      const r = await api.submitAttempts(courseId, answers)
      submitted.current = true
      if (!isReview) saveDiagnostic(courseId, null)
      setResult(r)
      void refreshCourses()
      window.scrollTo(0, 0)
    } catch (e) {
      setSubmitError(
        e instanceof ApiError && e.status === 422
          ? 'These questions are no longer valid (the clock may have moved).'
          : errorText(e),
      )
    } finally {
      setSubmitting(false)
    }
  }

  // Diagnostic questions went stale: POST .../reset, then .../start again.
  async function startOver() {
    setLoad({ kind: 'loading' })
    try {
      await api.reset(courseId)
      startCalls.delete(courseId)
      saveDiagnostic(courseId, null)
      resetAnswers()
      setNotice(null)
      setAttempt((a) => a + 1)
    } catch (e) {
      setLoad({ kind: 'error', message: errorText(e) })
    }
  }

  const reloadReview = () => {
    resetAnswers()
    setLoad({ kind: 'loading' })
    setAttempt((a) => a + 1)
  }

  return (
    <div className="assess">
      <header className="assess__bar">
        <div className="assess__bar-inner">
          <Link to="/" aria-label="OnlyNerds home" className="assess__logo">
            <img src={logo} alt="OnlyNerds" />
          </Link>
          <div className="assess__heading">
            <div className="assess__heading-title">
              {topic} {isReview ? 'review' : 'assessment'}
            </div>
            <div className="assess__heading-sub">
              {isReview
                ? load.kind === 'ready' && load.reviewConcept
                  ? `Time to review: ${name(load.reviewConcept)}`
                  : 'Spaced review'
                : 'Diagnostic · one question per concept'}
            </div>
          </div>
          <Link to={chatLink(courseId)} className="icon-btn" aria-label={isReview ? 'Exit review' : 'Exit assessment'}>
            <Icon name="close" strokeWidth={2} />
          </Link>
        </div>
      </header>

      <main className="assess__main">
        {notice && !result && <p className="assess__notice">{notice}</p>}

        {load.kind === 'loading' && <Loading label={isReview ? 'Getting your review…' : 'Loading your assessment…'} />}
        {load.kind === 'error' && <ErrorBox message={load.message} onRetry={() => setAttempt((a) => a + 1)} />}

        {load.kind === 'ready' && !result && questions.length > 0 && (
          <Question
            index={q}
            question={questions[q]}
            total={questions.length}
            topicLabel={name(questions[q].concept_id)}
            picked={picks[questions[q].id]}
            confidence={conf[questions[q].id]}
            answeredCount={answeredCount}
            submitting={submitting}
            onPick={(o, c) => pick(questions[q].id, o, c)}
            onBack={() => setQ(Math.max(0, q - 1))}
            onNext={() => setQ(Math.min(questions.length - 1, q + 1))}
            onSkip={() => skip(questions[q].id)}
            onSubmit={submit}
          />
        )}

        {submitError && !result && (
          <ErrorBox message={submitError} onRetry={isReview ? reloadReview : undefined}>
            {!isReview && (
              <button type="button" className="btn btn-soft status-box__btn" onClick={startOver}>
                Start over
              </button>
            )}
          </ErrorBox>
        )}

        {result && (
          <Results
            isReview={isReview}
            courseId={courseId}
            questions={questions}
            picks={picks}
            conf={conf}
            result={result}
            name={name}
          />
        )}
      </main>
    </div>
  )
}

function Question({
  index,
  question,
  total,
  topicLabel,
  picked,
  confidence,
  answeredCount,
  submitting,
  onPick,
  onBack,
  onNext,
  onSkip,
  onSubmit,
}: {
  index: number
  question: QuestionPublic
  total: number
  topicLabel: string
  picked: number | undefined
  confidence: number | undefined
  answeredCount: number
  submitting: boolean
  onPick: (option: number, confidence?: number) => void
  onBack: () => void
  onNext: () => void
  onSkip: () => void
  onSubmit: () => void
}) {
  // A skipped question counts as answered, so Back then Next works past it.
  const answered = picked !== undefined
  const pct = Math.round(((index + (answered ? 1 : 0)) / total) * 100)
  const last = index === total - 1

  return (
    <>
      <div className="assess__progress">
        <div className="assess__progress-row">
          <span className="assess__qlabel">
            Question {index + 1} of {total}
          </span>
          <span className="assess__qtopic">Topic: {topicLabel}</span>
        </div>
        <div
          className="assess__track"
          role="progressbar"
          aria-label="Assessment progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
        >
          <div className="assess__fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <section className="card assess__card" aria-labelledby="qt">
        <h1 id="qt" className="assess__question">
          {question.prompt}
        </h1>
        <QuestionOptions
          options={question.options}
          picked={picked === SKIPPED ? undefined : picked}
          confidence={confidence}
          onPick={onPick}
          disabled={submitting}
        />
        <button type="button" className="assess__skip" onClick={onSkip} disabled={submitting}>
          I'm not sure, skip this one
        </button>
      </section>

      <div className="assess__nav">
        <button
          className="btn btn-ghost"
          type="button"
          onClick={onBack}
          disabled={submitting}
          style={{ visibility: index === 0 ? 'hidden' : 'visible' }}
        >
          Back
        </button>
        {last ? (
          <button
            className="btn btn-primary"
            type="button"
            onClick={onSubmit}
            disabled={!answered || answeredCount === 0 || submitting}
          >
            {submitting ? 'Checking…' : 'See my results'}
          </button>
        ) : (
          <button className="btn btn-primary" type="button" onClick={onNext} disabled={!answered}>
            Next
          </button>
        )}
      </div>
      <p className="assess__hint">
        {last && answered && answeredCount === 0
          ? 'Answer at least one question to see your results.'
          : 'Confidence is optional. Skipping a question is fine too.'}
      </p>
    </>
  )
}

function Results({
  isReview,
  courseId,
  questions,
  picks,
  conf,
  result,
  name,
}: {
  isReview: boolean
  courseId: string
  questions: QuestionPublic[]
  picks: Record<string, number>
  conf: Record<string, number | undefined>
  result: AttemptResultOut
  name: (id: string) => string
}) {
  const graded = new Map(result.graded.map((g) => [g.question_id, g]))
  const total = questions.length
  const score = result.graded.filter((g) => g.correct).length
  const wrongCount = result.graded.length - score
  const skipCount = questions.filter((x) => !graded.has(x.id)).length
  const pct = total ? Math.round((score / total) * 100) : 0

  const byConcept = new Map<string, { ok: number; n: number }>()
  for (const g of result.graded) {
    const t = byConcept.get(g.concept_id) ?? { ok: 0, n: 0 }
    t.n++
    if (g.correct) t.ok++
    byConcept.set(g.concept_id, t)
  }
  const topicRows = [...byConcept].map(([id, t]) => {
    const f = t.ok / t.n
    const state = f >= 0.75 ? 'solid' : f >= 0.5 ? 'mid' : 'weak'
    return { id, name: name(id), fraction: `${t.ok} of ${t.n} correct`, width: Math.max(6, Math.round(f * 100)), state }
  })
  const certainWrong = result.graded.filter((g) => !g.correct && g.confidence === 'high').length
  const unsureRight = result.graded.filter((g) => g.correct && g.confidence === 'low').length
  const hasConf = result.graded.some((g) => g.confidence)

  return (
    <>
      <section className="card results__hero" aria-labelledby="hero">
        <Ring pct={pct} size={128} stroke={12} label={`${pct}% correct`}>
          <span className="results__pct">{pct}%</span>
          <span className="results__of">
            {score} of {total}
          </span>
        </Ring>
        <div className="results__hero-text">
          <div className="label results__done">{isReview ? 'Review complete' : 'Assessment complete'}</div>
          <h1 id="hero" className="results__level">
            Your level: {levelFromPct(pct)}
          </h1>
        </div>
      </section>

      <MessagesBanner messages={result.messages} />

      <section aria-label="Totals" className="results__totals">
        <div className="card results__total">
          <div className="results__total-n">{score}</div>
          <div className="results__total-label">Correct</div>
        </div>
        <div className="card results__total">
          <div className="results__total-n">{wrongCount}</div>
          <div className="results__total-label">To strengthen</div>
        </div>
        <div className="card results__total">
          <div className="results__total-n">{skipCount}</div>
          <div className="results__total-label">Skipped</div>
        </div>
      </section>

      <AnswerReview
        answers={questions.map((x) => {
          const g = graded.get(x.id)
          return {
            topic: name(x.concept_id),
            text: x.prompt,
            options: x.options,
            correct: result.correct_indices[x.id],
            graded: g?.correct,
            picked: g ? picks[x.id] : undefined,
            confidence: g ? (confidenceIndex(g.confidence) ?? conf[x.id]) : undefined,
          }
        })}
      />

      {topicRows.length > 0 && (
        <section className="card results__topics" aria-labelledby="tp">
          <h2 id="tp" className="label results__section-title">
            Results by topic
          </h2>
          {topicRows.map((t) => (
            <div key={t.id} className="results__topic">
              <div className="results__topic-name">
                <div className="results__topic-title">{t.name}</div>
                <div className="results__topic-sub">{t.fraction}</div>
              </div>
              <div className="results__bar">
                <div className={`results__bar-fill results__bar-fill--${t.state}`} style={{ width: `${t.width}%` }} />
              </div>
              <span className={`results__tag results__tag--${t.state}`}>
                {t.state === 'solid' ? 'Solid' : t.state === 'mid' ? 'Developing' : 'To strengthen'}
              </span>
            </div>
          ))}
        </section>
      )}

      {hasConf && (
        <section className="card results__conf" aria-labelledby="cf">
          <h2 id="cf" className="label results__section-title">
            Confidence check
          </h2>
          <div className="results__conf-grid">
            <div className="results__conf-box">
              <div className="results__conf-n">{certainWrong}</div>
              <div className="results__conf-title">Certain, but wrong</div>
              <div className="results__conf-sub">Worth a second look. These are likely misconceptions.</div>
            </div>
            <div className="results__conf-box">
              <div className="results__conf-n">{unsureRight}</div>
              <div className="results__conf-title">Unsure, but right</div>
              <div className="results__conf-sub">You know more than you think here.</div>
            </div>
          </div>
        </section>
      )}

      <section className="card results__ready" aria-labelledby="ready">
        <div className="results__ready-head">
          <div className="results__ready-icon" aria-hidden="true">
            <Icon name="book" size={24} strokeWidth={1.8} />
          </div>
          <div className="results__ready-text">
            <h2 id="ready">{isReview ? 'Back to your course' : 'Your learning materials are ready'}</h2>
            <div>Your next step is waiting on the course page.</div>
          </div>
        </div>
        <Link to={chatLink(courseId)} className="btn btn-primary results__open">
          {isReview ? 'Continue' : 'Open my learning materials'}
        </Link>
      </section>
    </>
  )
}
