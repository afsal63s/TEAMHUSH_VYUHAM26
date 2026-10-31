import { useState } from 'react'
import { Link } from 'react-router'
import { api, errorText } from '../../api/client'
import { dayDistance, hostOf } from '../../api/format'
import type { AttemptResultOut, StepOut } from '../../api/types'
import { AnswerReview } from '../../components/AnswerReview'
import { Icon } from '../../components/Icon'
import { CONFIDENCE_VALUES, confidenceIndex, nextConfidence } from '../../components/confidence'
import { QuestionOptions } from '../../components/QuestionOptions'
import { ErrorBox, MessagesBanner } from '../../components/Status'
import { reviewLink } from '../../routes'

type Name = (id: string | null | undefined) => string

// What GET .../next (or the `next` of POST .../attempts) says to show. The frontend never decides.
export function StepCard({
  courseId,
  step,
  name,
  nextDue,
  onAnswered,
  onContinue,
  onKeepGoing,
}: {
  courseId: string
  step: StepOut
  name: Name
  nextDue: string | null | undefined
  /** After POST .../attempts: refresh state and lists. */
  onAnswered: () => void
  /** Show the step the attempts response returned. */
  onContinue: (next: StepOut) => void
  /** session_end: POST .../sessions/new, then GET .../next. */
  onKeepGoing: () => Promise<void>
}) {
  const kind = step.step.kind

  if (kind === 'lesson' || kind === 'fallback')
    return <LessonCard courseId={courseId} step={step} name={name} onAnswered={onAnswered} onContinue={onContinue} />

  if (kind === 'review')
    return (
      <section className="card step" aria-labelledby="step-title">
        <div className="step__kicker">Time to review</div>
        <h2 id="step-title" className="step__title">
          {name(step.step.concept_id)}
        </h2>
        {step.reason && <p className="step__why">Why this? {step.reason}</p>}
        <p className="step__text">Two quick questions to check it stuck.</p>
        <Link to={reviewLink(courseId)} className="btn btn-primary step__cta">
          Start the review
        </Link>
      </section>
    )

  if (kind === 'session_end') return <SessionEndCard reason={step.reason} onKeepGoing={onKeepGoing} />

  return (
    <section className="card step step--done" aria-labelledby="step-title">
      <div className="step__icon step__icon--ok" aria-hidden="true">
        ✓
      </div>
      <h2 id="step-title" className="step__title">
        You've covered everything
      </h2>
      <p className="step__text">Reviews will come back as you start to forget.</p>
      {nextDue && <p className="step__why">Next review: {dayDistance(nextDue)}</p>}
    </section>
  )
}

function SessionEndCard({ reason, onKeepGoing }: { reason?: string; onKeepGoing: () => Promise<void> }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  return (
    <section className="card step step--done" aria-labelledby="step-title">
      <div className="step__icon" aria-hidden="true">
        <Icon name="clock" size={24} strokeWidth={1.8} />
      </div>
      <h2 id="step-title" className="step__title">
        Great session. Come back tomorrow.
      </h2>
      {reason && <p className="step__why">{reason}</p>}
      {error && <ErrorBox message={error} />}
      <button
        type="button"
        className="btn btn-primary step__cta"
        disabled={busy}
        onClick={async () => {
          setBusy(true)
          setError(null)
          try {
            await onKeepGoing()
          } catch (e) {
            setError(errorText(e))
            setBusy(false)
          }
        }}
      >
        {busy ? 'Starting…' : 'Keep going'}
      </button>
    </section>
  )
}

function LessonCard({
  courseId,
  step,
  name,
  onAnswered,
  onContinue,
}: {
  courseId: string
  step: StepOut
  name: Name
  onAnswered: () => void
  onContinue: (next: StepOut) => void
}) {
  const questions = step.questions ?? []
  const [picks, setPicks] = useState<Record<string, number>>({})
  const [conf, setConf] = useState<Record<string, number | undefined>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AttemptResultOut | null>(null)
  const isFallback = step.step.kind === 'fallback'
  const resources = step.lesson?.resources ?? []
  const answered = questions.filter((x) => picks[x.id] !== undefined).length

  async function check() {
    if (busy || answered === 0) return
    setBusy(true)
    setError(null)
    try {
      const r = await api.submitAttempts(
        courseId,
        questions
          .filter((x) => picks[x.id] !== undefined)
          .map((x) => {
            const c = conf[x.id]
            return { question_id: x.id, chosen_index: picks[x.id], ...(c !== undefined && { confidence: CONFIDENCE_VALUES[c] }) }
          }),
      )
      setResult(r)
      onAnswered()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const graded = new Map(result?.graded.map((g) => [g.question_id, g]))

  return (
    <section className="card step" aria-labelledby="step-title">
      {isFallback && <div className="step__banner">Let's go back to a building block first</div>}
      <div className="step__kicker">{isFallback ? 'Building block' : 'Lesson'}</div>
      <h2 id="step-title" className="step__title">
        {name(step.step.concept_id)}
      </h2>
      {isFallback && step.step.target_concept && (
        <p className="step__sub">This helps with {name(step.step.target_concept)}.</p>
      )}
      {step.reason && <p className="step__why">Why this? {step.reason}</p>}
      {step.step.give_up_after && (
        <p className="step__note">Last try on this one for now. Take your time; it's fine to find it hard.</p>
      )}
      {step.lesson?.explanation && <div className="step__lesson">{step.lesson.explanation}</div>}
      {resources.length > 0 && (
        <ul className="step__links">
          {resources.map((r) => (
            <li key={r.url}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                <Icon name={r.kind === 'video' ? 'play' : 'article'} size={16} strokeWidth={1.8} />
                <span className="step__link-text">
                  {r.title} <span className="step__host">{hostOf(r.url)}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}

      {!result && questions.length > 0 && (
        <div className="step__questions">
          {questions.map((x, i) => (
            <div key={x.id} className="step__q">
              <div className="step__q-n">
                Question {i + 1} of {questions.length}
              </div>
              <p className="step__q-text">{x.prompt}</p>
              <QuestionOptions
                options={x.options}
                picked={picks[x.id]}
                confidence={conf[x.id]}
                disabled={busy}
                onPick={(o, c) => {
                  setPicks((p) => ({ ...p, [x.id]: o }))
                  setConf((cc) => ({ ...cc, [x.id]: nextConfidence(picks[x.id], cc[x.id], o, c) }))
                }}
              />
            </div>
          ))}
          {error && <ErrorBox message={error} />}
          <button type="button" className="btn btn-primary step__cta" onClick={check} disabled={busy || answered === 0}>
            {busy ? 'Checking…' : 'Check answers'}
          </button>
          <p className="step__hint">
            {answered === 0 ? 'Answer at least one question.' : `${answered} of ${questions.length} answered. Unanswered ones are skipped.`}
          </p>
        </div>
      )}

      {result && (
        <div className="step__result">
          <MessagesBanner messages={result.messages} />
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
          <button type="button" className="btn btn-primary step__cta" onClick={() => onContinue(result.next)}>
            Continue
          </button>
        </div>
      )}
    </section>
  )
}
