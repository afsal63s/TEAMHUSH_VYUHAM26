import { useState } from 'react'
import './AnswerReview.css'

const LETTERS = ['A', 'B', 'C', 'D']
const CONFIDENCE = ['Not sure', 'Fairly sure', 'Certain']

export interface ReviewedAnswer {
  topic: string
  text: string
  options: string[]
  correct: number
  /** Index picked, or undefined when skipped. */
  picked: number | undefined
  /** 0 = not sure, 1 = fairly sure, 2 = certain; undefined when not given. */
  confidence: number | undefined
}

type Filter = 'all' | 'wrong' | 'skipped'

// Question-by-question feedback after grading: what was picked and the right answer.
export function AnswerReview({ answers }: { answers: ReviewedAnswer[] }) {
  const [filter, setFilter] = useState<Filter>('all')
  const isSkipped = (a: ReviewedAnswer) => a.picked === undefined
  const isWrong = (a: ReviewedAnswer) => !isSkipped(a) && a.picked !== a.correct
  const counts = {
    all: answers.length,
    wrong: answers.filter(isWrong).length,
    skipped: answers.filter(isSkipped).length,
  }
  const shown = answers
    .map((a, i) => ({ a, n: i + 1 }))
    .filter(({ a }) => filter === 'all' || (filter === 'wrong' ? isWrong(a) : isSkipped(a)))

  return (
    <section className="card review" aria-labelledby="qbq">
      <div className="review__head">
        <h2 id="qbq" className="label review__title">
          Question by question
        </h2>
        <div role="tablist" aria-label="Filter questions" className="review__filters">
          {(['all', 'wrong', 'skipped'] as const).map((f) => (
            <button
              key={f}
              type="button"
              role="tab"
              aria-selected={filter === f}
              className={`review__filter${filter === f ? ' review__filter--on' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : f === 'wrong' ? 'Wrong' : 'Skipped'} {counts[f]}
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 && (
        <p className="review__empty">{filter === 'wrong' ? 'Nothing wrong. Nice.' : 'Nothing skipped.'}</p>
      )}

      <ol className="review__list">
        {shown.map(({ a, n }) => {
          const skipped = isSkipped(a)
          const right = !skipped && a.picked === a.correct
          const verdict = skipped ? 'skipped' : right ? 'right' : 'wrong'
          const callout =
            !skipped && a.confidence === 2 && !right
              ? { tone: 'warn', text: 'Certain, but wrong. This is likely a misconception, worth a second look.' }
              : !skipped && a.confidence === 0 && right
                ? { tone: 'good', text: 'Unsure, but right. You know more than you think here.' }
                : null

          return (
            <li key={n} className={`rq rq--${verdict}`}>
              <div className="rq__head">
                <span className="rq__n">Q{n}</span>
                <span className="rq__topic">{a.topic}</span>
                <span className="rq__spacer" />
                {a.confidence !== undefined && !skipped && (
                  <span className="rq__conf">{CONFIDENCE[a.confidence]}</span>
                )}
                <span className={`rq__verdict rq__verdict--${verdict}`}>
                  {skipped ? 'Skipped' : right ? 'Correct' : 'Wrong'}
                </span>
              </div>
              <p className="rq__text">{a.text}</p>

              <ul className="rq__options">
                {a.options.map((opt, i) => {
                  const isCorrect = i === a.correct
                  const isPicked = i === a.picked
                  const state = isPicked ? (isCorrect ? 'right' : 'wrong') : isCorrect ? 'answer' : 'plain'
                  return (
                    <li key={i} className={`rq__opt rq__opt--${state}`}>
                      <span className="rq__letter" aria-hidden="true">
                        {state === 'right' || state === 'answer' ? '✓' : state === 'wrong' ? '✕' : LETTERS[i]}
                      </span>
                      <span className="rq__opt-text">{opt}</span>
                      {isPicked && <span className="rq__tag">Your answer</span>}
                      {isCorrect && !isPicked && <span className="rq__tag rq__tag--answer">Correct answer</span>}
                    </li>
                  )
                })}
              </ul>

              {callout && <div className={`rq__callout rq__callout--${callout.tone}`}>{callout.text}</div>}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
