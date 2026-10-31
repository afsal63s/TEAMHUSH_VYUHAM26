import { CONFIDENCE_LABELS } from './confidence'
import './QuestionOptions.css'

const LETTERS = ['A', 'B', 'C', 'D']

// The four answer options of one question, each with an optional "how sure are you?" picker.
export function QuestionOptions({
  options,
  picked,
  confidence,
  onPick,
  disabled = false,
}: {
  options: string[]
  picked: number | undefined
  confidence: number | undefined
  /** `confidence` is set when a confidence button was clicked (clicking the chosen one again clears it). */
  onPick: (option: number, confidence?: number) => void
  disabled?: boolean
}) {
  return (
    <div role="group" aria-label="Answer choices" className="assess__options">
      {options.map((text, i) => {
        const on = picked === i
        return (
          <div key={i} className={`opt${on ? ' opt--on' : ''}`}>
            <button type="button" className="opt__main" aria-pressed={on} onClick={() => onPick(i)} disabled={disabled}>
              <span className="opt__letter">{LETTERS[i]}</span>
              <span className="opt__text">{text}</span>
            </button>
            <div role="group" aria-label="How sure are you? (optional)" className="opt__conf">
              {CONFIDENCE_LABELS.map((label, ci) => {
                const cOn = on && confidence === ci
                return (
                  <button
                    key={label}
                    type="button"
                    className={`opt__conf-btn${cOn ? ' opt__conf-btn--on' : ''}`}
                    aria-pressed={cOn}
                    onClick={() => onPick(i, ci)}
                    disabled={disabled}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
