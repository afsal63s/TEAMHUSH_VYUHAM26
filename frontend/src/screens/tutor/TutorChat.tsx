import { Link, useParams } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { Ring } from '../../components/Ring'
import { useBuiltCourse } from '../../data/courseStore'
import { findChat, materials, tutorMastery, type MaterialStatus } from '../../data/placeholder'
import { reviewLink } from '../../routes'
import { CourseChat } from './CourseChat'
// The right panel (.rail) styles are shared with Home.
import '../home/HomeFeed.css'
import './TutorChat.css'

const statusLabel: Record<MaterialStatus, string> = { done: 'Done', now: 'In progress', next: 'Up next' }

export function TutorChat() {
  const { chatId } = useParams()
  const built = useBuiltCourse(chatId)
  if (built) return <CourseChat course={built} />
  return <PlaceholderChat chatId={chatId} />
}

function PlaceholderChat({ chatId }: { chatId: string | undefined }) {
  const chat = findChat(chatId)
  const doneCount = materials.filter((m) => m.status === 'done').length

  return (
    <AppShell activeChatId={chat.id}>
      <main className="tutor">
        <header className="tutor__header">
          <Link to="/" className="icon-btn" aria-label="Back to Home">
            <Icon name="back" strokeWidth={2} />
          </Link>
          <div className="tutor__heading">
            <h1>{chat.title}</h1>
            <div>
              {chat.topic} · {chat.level} · Learning materials
            </div>
          </div>
          <button className="icon-btn" type="button" aria-label="More options">
            <Icon name="more" size={20} />
          </button>
        </header>

        <div className="tutor__body">
          {chat.reviewDue && (
            <section className="tutor__due" aria-labelledby="due">
              <div className="tutor__due-icon" aria-hidden="true">
                <Icon name="clock" strokeWidth={1.8} />
              </div>
              <div className="tutor__due-text">
                <div className="tutor__due-kicker">Review due now</div>
                <h2 id="due">Time for a quick recall check</h2>
                <div>{chat.nextCheck.what}. A few questions, about 5 minutes.</div>
              </div>
              <Link to={reviewLink(chat.topic)} className="btn btn-primary">
                Take the quiz
              </Link>
            </section>
          )}

          <section className="tutor__curated">
            <div className="tutor__curated-icon" aria-hidden="true">
              <Icon name="book" size={24} strokeWidth={1.8} />
            </div>
            <div className="tutor__curated-text">
              <div className="tutor__kicker">Curated for you</div>
              <h2>{chat.courseTitle}</h2>
              <div>
                {materials.length} materials · about 38 min · {doneCount} of {materials.length} done
              </div>
            </div>
            <a href="#" className="btn btn-primary">
              Continue learning
            </a>
          </section>

          {materials.map((m, i) => (
            <article key={m.title} className="card material">
              <span className={`material__n material__n--${m.status}`}>{i + 1}</span>
              <div className="material__icon" aria-hidden="true">
                <Icon name={m.kind === 'Video' ? 'play' : 'article'} strokeWidth={1.8} />
              </div>
              <div className="material__text">
                <div className="material__title">{m.title}</div>
                <div className="material__meta">
                  {m.kind} · {m.source} · {m.time}
                </div>
              </div>
              <span className={`status status--${m.status}`}>{statusLabel[m.status]}</span>
              <a href="#" className="btn btn-soft">
                Open
              </a>
            </article>
          ))}
        </div>
      </main>

      <aside className="rail">
        <section className="card rail__card tutor__mastery" aria-labelledby="ms">
          <h2 id="ms" className="label">
            Mastery level
          </h2>
          <div className="tutor__mastery-head">
            <Ring pct={tutorMastery.pct} size={84} stroke={8} label={`${tutorMastery.pct} percent mastery`}>
              <span className="tutor__mastery-pct">{tutorMastery.pct}%</span>
            </Ring>
            <div>
              <div className="tutor__mastery-level">{tutorMastery.level}</div>
              <div className="tutor__mastery-delta">{tutorMastery.delta}</div>
              <div className="tutor__mastery-topic">{chat.topic}</div>
            </div>
          </div>
          <div className="tutor__divider" />
          <div className="tutor__topics">
            {tutorMastery.topics.map((t) => (
              <div key={t.name}>
                <div className="tutor__topic-row">
                  <span>{t.name}</span>
                  <span className="tutor__topic-pct">{t.pct}%</span>
                </div>
                <div className="tutor__topic-track">
                  <div
                    className="tutor__topic-fill"
                    style={{ width: `${t.pct}%`, background: t.pct < 50 ? '#D97706' : 'var(--primary)' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="card rail__card" aria-labelledby="cl">
          <div className="rail__card-head">
            <h2 id="cl" className="label">
              Currently learning
            </h2>
            <span className="tutor__curated-by">Curated by your agent</span>
          </div>
          {materials.map((m) => (
            <a key={m.title} href="#" className="row-link rail__row">
              <div className="av" style={{ width: 40, height: 40, borderRadius: 12 }} aria-hidden="true">
                <Icon name={m.kind === 'Video' ? 'play' : 'article'} size={18} strokeWidth={1.8} />
              </div>
              <div className="rail__row-text">
                <div className="rail__row-title">{m.title}</div>
                <div className="rail__row-sub">
                  {m.kind} · {m.time}
                </div>
              </div>
              <span className={`status status--sm status--${m.status}`}>{statusLabel[m.status]}</span>
            </a>
          ))}
        </section>

        <section
          className={`card rail__card tutor__next${chat.reviewDue ? ' tutor__next--due' : ''}`}
          aria-labelledby="nd"
        >
          <h2 id="nd" className="label">
            Next assessment due
          </h2>
          <div className="tutor__next-row">
            <div className="tutor__cal" aria-hidden="true">
              <div className="tutor__cal-month">{chat.nextCheck.month}</div>
              <div className="tutor__cal-day">{chat.nextCheck.day}</div>
            </div>
            <div className="tutor__next-text">
              <div className="tutor__next-when">{chat.nextCheck.when}</div>
              <div className="tutor__next-what">{chat.nextCheck.what}</div>
            </div>
          </div>
          {chat.reviewDue && (
            <Link to={reviewLink(chat.topic)} className="btn btn-primary tutor__next-btn">
              Take the quiz
            </Link>
          )}
        </section>
      </aside>
    </AppShell>
  )
}
