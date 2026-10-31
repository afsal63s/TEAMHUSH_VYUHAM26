import { Link } from 'react-router'
import { ago, dayDistance, levelName, pct } from '../../api/format'
import type { CourseSummary } from '../../api/types'
import mark from '../../assets/mark.png'
import { Icon } from '../../components/Icon'
import { buildCourseLink, chatLink, diagnosticLink, reviewLink } from '../../routes'
import { postStatus } from './courseStatus'
import { Cover, type CoverKind } from './Covers'

const COVERS: CoverKind[] = ['nn', 'matrix', 'code', 'attention']
/** A stable cover picked from the topic name. */
const coverFor = (topic: string) => COVERS[[...topic].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7) % COVERS.length]

function badge(c: CourseSummary): { label: string; className: string } {
  if (c.status === 'generating') return { label: 'Building', className: 'badge badge--progress' }
  if (c.status === 'failed') return { label: 'Build failed', className: 'badge badge--review' }
  if (!c.started) return { label: 'Not started', className: 'badge badge--progress' }
  const s = postStatus(c)
  if (s === 'review') return { label: 'Review due', className: 'badge badge--review' }
  if (s === 'done') return { label: 'Completed', className: 'badge badge--done' }
  return { label: 'In progress', className: 'badge badge--progress' }
}

function primaryAction(c: CourseSummary): { label: string; to: string } {
  if (c.status === 'generating') return { label: 'See progress', to: buildCourseLink(c.course_id) }
  if (c.status === 'failed') return { label: 'Try again', to: buildCourseLink(c.course_id) }
  if (!c.started) return { label: 'Take the assessment', to: diagnosticLink(c.course_id) }
  if ((c.overdue_count ?? 0) > 0) return { label: 'Start review', to: reviewLink(c.course_id) }
  if (postStatus(c) === 'done') return { label: 'Revisit course', to: chatLink(c.course_id) }
  return { label: 'Continue learning', to: chatLink(c.course_id) }
}

function cardText(c: CourseSummary): string {
  if (c.status === 'generating') return 'Building your course: mapping the concepts and writing questions.'
  if (c.status === 'failed') return 'Something went wrong building this course. Trying again usually works.'
  if (!c.started) return `Ready: ${c.concept_count ?? 0} concepts. A short assessment comes first, so I can skip what you already know.`
  const parts = [`${c.mastered ?? 0} of ${c.concept_count ?? 0} concepts mastered.`]
  if (c.overdue_count) parts.push(`${c.overdue_count} review${c.overdue_count === 1 ? '' : 's'} due now.`)
  if (c.needs_help_count) parts.push(`${c.needs_help_count} flagged for help.`)
  return parts.join(' ')
}

// One Home card per course from GET /courses.
export function FeedPostCard({ course: c }: { course: CourseSummary }) {
  const b = badge(c)
  const action = primaryAction(c)
  const open = c.status === 'ready' ? chatLink(c.course_id) : buildCourseLink(c.course_id)
  const total = c.concept_count ?? 0
  const mastered = c.mastered ?? 0

  return (
    <article className="card post">
      <header className="post__header">
        <div className="av post__agent" aria-hidden="true">
          <img src={mark} alt="" />
        </div>
        <div className="post__byline">
          <div className="post__author">
            OnlyNerds Agent
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="11" fill="#0770C9" />
              <path
                d="m7 12.5 3.2 3.2L17 9"
                fill="none"
                stroke="#FFFFFF"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="post__meta">
            {levelName(c.level)} · {ago(c.last_activity_at ?? c.created_at)}
          </div>
        </div>
        <span className={b.className}>{b.label}</span>
      </header>

      <div className="post__text">{cardText(c)}</div>

      <Link to={open} className="post__cover" aria-label={`Open ${c.topic}`}>
        <Cover kind={coverFor(c.topic)} />
        {total > 0 && (
          <div className="post__pills">
            <span className="pill">
              <Icon name="book" size={14} strokeWidth={2} />
              {total} concepts
            </span>
          </div>
        )}
      </Link>

      <div className="post__summary">
        <div className="post__summary-main">
          <h2 className="post__title">{c.topic}</h2>
          {total > 0 && (
            <div className="post__segments" aria-hidden="true">
              {Array.from({ length: total }, (_, i) => (
                <span key={i} className={i < mastered ? 'seg seg--done' : 'seg'} />
              ))}
            </div>
          )}
          <div className="post__stats">
            <span>
              {mastered} of {total} done
            </span>
            <span>
              Retention: <strong>{c.started ? pct(c.avg_retrievability) : '—'}</strong>
            </span>
            <span>
              Next review: <strong>{c.next_due_at ? dayDistance(c.next_due_at) : '—'}</strong>
            </span>
          </div>
        </div>
        <Link to={action.to} className="btn btn-soft">
          {action.label}
        </Link>
      </div>

      {c.started && (
        <footer className="post__footer">
          <Link to={reviewLink(c.course_id)} className="icon-btn" aria-label="Quiz me on this course">
            <Icon name="quiz" />
            Quiz
          </Link>
          <Link to={chatLink(c.course_id)} className="icon-btn" aria-label="Open the tutor page">
            <Icon name="chat" />
            Tutor
          </Link>
        </footer>
      )}
    </article>
  )
}
