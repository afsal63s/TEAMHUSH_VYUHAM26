import type { ReactNode } from 'react'
import { Icon } from './Icon'
import './Status.css'

/** Spinner card shown while a request is in flight. */
export function Loading({ label = 'Loading…', compact = false }: { label?: string; compact?: boolean }) {
  return (
    <div className={compact ? 'status-box status-box--compact' : 'card status-box'} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

/** Short error with an optional retry. */
export function ErrorBox({ message, onRetry, children }: { message: string; onRetry?: () => void; children?: ReactNode }) {
  return (
    <div className="card status-box status-box--error" role="alert">
      <Icon name="alert" size={20} strokeWidth={1.8} />
      <span className="status-box__text">{message}</span>
      {children}
      {onRetry && (
        <button type="button" className="btn btn-soft status-box__btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

/** The backend's `messages`, one line each, shown exactly as they come. */
export function MessagesBanner({ messages }: { messages: string[] | undefined }) {
  if (!messages?.length) return null
  return (
    <section className="messages" aria-label="Messages" aria-live="polite">
      {messages.map((m, i) => (
        <p key={i} className="messages__line">
          {m}
        </p>
      ))}
    </section>
  )
}
