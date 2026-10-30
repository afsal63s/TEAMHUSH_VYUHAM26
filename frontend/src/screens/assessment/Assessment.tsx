import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import logo from '../../assets/logo.png'
import { AnswerReview } from '../../components/AnswerReview'
import { Icon } from '../../components/Icon'
import { Ring } from '../../components/Ring'
import { updateCourse } from '../../data/courseStore'
import { assessment, previousChats } from '../../data/placeholder'
import './Assessment.css'

const LETTERS = ['A', 'B', 'C', 'D']
const CONFIDENCE = ['Not sure', 'Fairly sure', 'Certain'] as const
const SKIPPED = -1

// The diagnostic (new topic) or a spaced review (mode=review): questions one at a time, then results.
export function Assessment() {
  const [params] = useSearchParams()
  const isReview = params.get('mode') === 'review'
  const topic = params.get('topic') ?? assessment.title
  const level = params.get('level') ?? assessment.level
  // Set when the diagnostic belongs to a course built on the Build screen.
  const courseId = params.get('course') ?? undefined
  const questions = assessment.questions

  const [q, setQ] = useState(0)
  const [picks, setPicks] = useState<(number | undefined)[]>([])
  const [conf, setConf] = useState<(number | undefined)[]>([])
  const [done, setDone] = useState(false)

  const exitTo = courseId ? `/chat/${courseId}` : isReview ? '/' : '/new'

  function pick(option: number, confidence?: number) {
    const sameOption = picks[q] === option
    setPicks((p) => Object.assign([...p], { [q]: option }))
    setConf((c) => {
      let next: number | undefined
      if (confidence === undefined) {
        // Picking a different answer clears the confidence given for the old one.
        next = sameOption ? c[q] : undefined
      } else {
        // Confidence is optional: clicking the chosen level again unchecks it.
        next = sameOption && c[q] === confidence ? undefined : confidence
      }
      return Object.assign([...c], { [q]: next })
    })
  }

  function advance() {
    if (q < questions.length - 1) setQ(q + 1)
    else setDone(true)
  }

  function skip() {
    setPicks((p) => Object.assign([...p], { [q]: SKIPPED }))
    setConf((c) => Object.assign([...c], { [q]: undefined }))
    advance()
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
            <div className="assess__heading-sub">{isReview ? 'Spaced review' : `${level} level`}</div>
          </div>
          <Link to={exitTo} className="icon-btn" aria-label={isReview ? 'Exit review' : 'Exit assessment'}>
            <Icon name="close" strokeWidth={2} />
          </Link>
        </div>
      </header>

      <main className="assess__main">
        {done ? (
          <Results
            topic={topic}
            isReview={isReview}
            picks={picks}
            conf={conf}
            courseId={courseId}
          />
        ) : (
          <Question
            index={q}
            picked={picks[q]}
            confidence={conf[q]}
            onPick={pick}
            onBack={() => setQ(Math.max(0, q - 1))}
            onNext={advance}
            onSkip={skip}
            showConfidence={isReview}
          />
        )}
      </main>
    </div>
  )
}

function Question({
  index,
  picked,
  confidence,
  onPick,
  onBack,
  onNext,
  onSkip,
  showConfidence,
}: {
  index: number
  picked: number | undefined
  confidence: number | undefined
  onPick: (option: number, confidence?: number) => void
  onBack: () => void
  onNext: () => void
  onSkip: () => void
  /** Confidence is asked on reviews only, not on the first (diagnostic) assessment. */
  showConfidence: boolean
}) {
  const questions = assessment.questions
  const cur = questions[index]
  // A skipped question counts as answered, so Back then Next works past it.
  const answered = picked !== undefined
  const pct = Math.round(((index + (answered ? 1 : 0)) / questions.length) * 100)
  const last = index === questions.length - 1

  return (
    <>
      <div className="assess__progress">
        <div className="assess__progress-row">
          <span className="assess__qlabel">
            Question {index + 1} of {questions.length}
          </span>
          <span className="assess__qtopic">Topic: {cur.topic}</span>
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
          {cur.text}
        </h1>
        <div role="group" aria-label="Answer choices" className="assess__options">
          {cur.options.map((text, i) => {
            const on = picked === i
            return (
              <div key={i} className={`opt${on ? ' opt--on' : ''}`}>
                <button type="button" className="opt__main" aria-pressed={on} onClick={() => onPick(i)}>
                  <span className="opt__letter">{LETTERS[i]}</span>
                  <span className="opt__text">{text}</span>
                </button>
                {showConfidence && (
                  <div role="group" aria-label="How sure are you? (optional)" className="opt__conf">
                    {CONFIDENCE.map((label, ci) => {
                      const cOn = on && confidence === ci
                      return (
                        <button
                          key={label}
                          type="button"
                          className={`opt__conf-btn${cOn ? ' opt__conf-btn--on' : ''}`}
                          aria-pressed={cOn}
                          onClick={() => onPick(i, ci)}
                        >
                          {label}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <button type="button" className="assess__skip" onClick={onSkip}>
          I'm not sure, skip this one
        </button>
      </section>

      <div className="assess__nav">
        <button
          className="btn btn-ghost"
          type="button"
          onClick={onBack}
          style={{ visibility: index === 0 ? 'hidden' : 'visible' }}
        >
          Back
        </button>
        <button className="btn btn-primary" type="button" onClick={onNext} disabled={!answered}>
          {last ? 'See my results' : 'Next'}
        </button>
      </div>
      <p className="assess__hint">
        {showConfidence ? 'Confidence is optional. Skipping a question is fine too.' : 'Skipping a question is fine.'}
      </p>
    </>
  )
}

function Results({
  topic,
  isReview,
  picks,
  conf,
  courseId,
}: {
  topic: string
  isReview: boolean
  picks: (number | undefined)[]
  conf: (number | undefined)[]
  courseId?: string
}) {
  const questions = assessment.questions
  const total = questions.length
  const results = questions.map((x, i) => ({
    topic: x.topic,
    ok: picks[i] === x.correct,
    skipped: picks[i] === SKIPPED || picks[i] === undefined,
    conf: conf[i],
  }))
  const score = results.filter((r) => r.ok).length
  const skipCount = results.filter((r) => r.skipped).length
  const wrongCount = total - score - skipCount
  const pct = Math.round((score / total) * 100)
  const levelName = pct >= 85 ? 'Advanced' : pct >= 65 ? 'Intermediate' : pct >= 40 ? 'Beginner' : 'Novice'

  const byTopic = new Map<string, { ok: number; n: number }>()
  for (const r of results) {
    const t = byTopic.get(r.topic) ?? { ok: 0, n: 0 }
    t.n++
    if (r.ok) t.ok++
    byTopic.set(r.topic, t)
  }
  const topicRows = [...byTopic].map(([name, t]) => {
    const f = t.ok / t.n
    const state = f >= 0.75 ? 'solid' : f >= 0.5 ? 'mid' : 'weak'
    return { name, fraction: `${t.ok} of ${t.n} correct`, width: Math.max(6, Math.round(f * 100)), state }
  })
  const weakCount = topicRows.filter((t) => t.state !== 'solid').length
  const certainWrong = results.filter((r) => !r.ok && !r.skipped && r.conf === 2).length
  const unsureRight = results.filter((r) => r.ok && r.conf === 0).length
  const hasConf = results.some((r) => r.conf !== undefined)
  const chat = previousChats.find((c) => c.topic === topic || c.title === topic) ?? previousChats[0]
  const materialsLink = courseId ? `/chat/${courseId}` : `/chat/${chat.id}`

  // A built course records its diagnostic, so its chat stops asking for the assessment.
  useEffect(() => {
    if (courseId) updateCourse(courseId, { assessed: true, score: pct })
  }, [courseId, pct])

  const summary =
    weakCount === 0
      ? 'You are solid across every topic. Nice work.'
      : `${weakCount} ${weakCount === 1 ? 'topic is' : 'topics are'} worth strengthening. I gathered material for exactly that.`

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
            Your level: {levelName}
          </h1>
          <p className="results__summary">{summary}</p>
        </div>
      </section>

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
        answers={questions.map((x, i) => ({
          ...x,
          picked: picks[i] === SKIPPED ? undefined : picks[i],
          confidence: conf[i],
        }))}
      />

      <section className="card results__topics" aria-labelledby="tp">
        <h2 id="tp" className="label results__section-title">
          Results by topic
        </h2>
        {topicRows.map((t) => (
          <div key={t.name} className="results__topic">
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

      <section className="results__scheduled">
        <Icon name="calendar" color="#0659A3" strokeWidth={1.8} />
        <div className="results__scheduled-text">
          <strong>Re-assessment scheduled.</strong> After you finish the material, I'll re-check these topics
          after 1, 3 and 7 days to measure what you actually retain.
        </div>
      </section>

      <section className="card results__ready" aria-labelledby="ready">
        <div className="results__ready-head">
          <div className="results__ready-icon" aria-hidden="true">
            <Icon name="book" size={24} strokeWidth={1.8} />
          </div>
          <div className="results__ready-text">
            <h2 id="ready">Your learning materials are ready</h2>
            <div>{assessment.materialCount} articles, videos and notes picked for your weak spots.</div>
          </div>
        </div>
        <Link to={materialsLink} className="btn btn-primary results__open">
          Open my learning materials
        </Link>
      </section>
    </>
  )
}
