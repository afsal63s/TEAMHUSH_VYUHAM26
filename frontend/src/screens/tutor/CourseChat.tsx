import { Link } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { Ring } from '../../components/Ring'
import type { BuiltCourse } from '../../data/courseStore'
import { diagnosticLink } from '../../routes'
import '../home/HomeFeed.css'
import './TutorChat.css'

type ConceptStatus = 'now' | 'next'
const statusLabel: Record<ConceptStatus, string> = { now: 'In progress', next: 'Up next' }

// A course built in this browser, shown in the Tutor chat layout with its concepts as the content.
export function CourseChat({ course }: { course: BuiltCourse }) {
  const assessLink = diagnosticLink(course.topic, course.level, course.id)
  const names = new Map(course.concepts.map((c) => [c.id, c.name]))
  const status = (i: number): ConceptStatus => (course.assessed && i === 0 ? 'now' : 'next')

  const recheck = new Date(new Date(course.createdAt).getTime() + 24 * 60 * 60 * 1000)
  const recheckWhat = `Re-check: ${course.concepts
    .slice(0, 2)
    .map((c) => c.name.toLowerCase())
    .join(' and ')}`

  return (
    <AppShell activeChatId={course.id}>
      <main className="tutor">
        <header className="tutor__header">
          <Link to="/" className="icon-btn" aria-label="Back to Home">
            <Icon name="back" strokeWidth={2} />
          </Link>
          <div className="tutor__heading">
            <h1>{course.topic}</h1>
            <div>{course.level} · Your course</div>
          </div>
          <button className="icon-btn" type="button" aria-label="More options">
            <Icon name="more" size={20} />
          </button>
        </header>

        <div className="tutor__body">
          {!course.assessed && (
            <section className="tutor__curated" aria-labelledby="first">
              <div className="tutor__curated-icon" aria-hidden="true">
                <Icon name="quiz" size={24} strokeWidth={1.8} />
              </div>
              <div className="tutor__curated-text">
                <div className="tutor__kicker">First step</div>
                <h2 id="first">Take the short assessment</h2>
                <div>
                  {course.concepts.length} questions, one per concept, so I can skip what you already know.
                </div>
              </div>
              <Link to={assessLink} className="btn btn-primary">
                Start the assessment
              </Link>
            </section>
          )}

          <section className={course.assessed ? 'tutor__curated' : 'tutor__curated tutor__curated--quiet'}>
            <div className="tutor__curated-icon" aria-hidden="true">
              <Icon name="book" size={24} strokeWidth={1.8} />
            </div>
            <div className="tutor__curated-text">
              <div className="tutor__kicker">Your course</div>
              <h2>{course.topic}</h2>
              <div>
                {course.concepts.length} concepts ·{' '}
                {course.assessed ? `assessment score ${course.score ?? 0}%` : 'assessment not taken yet'}
              </div>
            </div>
            {course.assessed && (
              <a href="#" className="btn btn-primary">
                Continue learning
              </a>
            )}
          </section>

          {course.concepts.map((c, i) => {
            const s = status(i)
            const after = c.prerequisites.map((p) => names.get(p)).filter(Boolean)
            return (
              <article key={c.id} className="card material">
                <span className={`material__n material__n--${s}`}>{i + 1}</span>
                <div className="material__icon" aria-hidden="true">
                  <Icon name="book" strokeWidth={1.8} />
                </div>
                <div className="material__text">
                  <div className="material__title">{c.name}</div>
                  <div className="material__meta">
                    Concept {i + 1} · {after.length ? `Builds on ${after.join(', ').toLowerCase()}` : 'Starting point'}
                  </div>
                </div>
                <span className={`status status--${s}`}>{statusLabel[s]}</span>
                {course.assessed && (
                  <a href="#" className="btn btn-soft">
                    Open
                  </a>
                )}
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
          {course.assessed ? (
            <div className="tutor__mastery-head">
              <Ring pct={course.score ?? 0} size={84} stroke={8} label={`${course.score ?? 0} percent on the assessment`}>
                <span className="tutor__mastery-pct">{course.score ?? 0}%</span>
              </Ring>
              <div>
                <div className="tutor__mastery-level">{course.level}</div>
                <div className="tutor__mastery-topic">Assessment score</div>
                <div className="tutor__mastery-topic">{course.topic}</div>
              </div>
            </div>
          ) : (
            <div className="rail__empty">
              <Ring pct={null} size={72} stroke={7}>
                <span className="rail__empty-ring">--</span>
              </Ring>
              <div className="rail__empty-title">No mastery data yet</div>
              <div className="rail__empty-text">Take the assessment to see where you stand.</div>
            </div>
          )}
        </section>

        {course.assessed && (
          <section className="card rail__card tutor__next" aria-labelledby="nd">
            <h2 id="nd" className="label">
              Next assessment due
            </h2>
            <div className="tutor__next-row">
              <div className="tutor__cal" aria-hidden="true">
                <div className="tutor__cal-month">
                  {recheck.toLocaleDateString(undefined, { month: 'short' }).toUpperCase()}
                </div>
                <div className="tutor__cal-day">{recheck.getDate()}</div>
              </div>
              <div className="tutor__next-text">
                <div className="tutor__next-when">Tomorrow</div>
                <div className="tutor__next-what">{recheckWhat}</div>
              </div>
            </div>
          </section>
        )}
      </aside>
    </AppShell>
  )
}
