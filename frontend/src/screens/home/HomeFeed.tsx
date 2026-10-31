import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { api } from '../../api/client'
import { dayDistance } from '../../api/format'
import { useAsync, useControlPanelSignal, useCourses } from '../../api/hooks'
import type { DueItem } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { LevelSelect } from '../../components/LevelSelect'
import { ErrorBox, Loading } from '../../components/Status'
import { user, type LevelKey } from '../../data/placeholder'
import { buildLink, reviewLink } from '../../routes'
import { postStatus, type PostStatus } from './courseStatus'
import { FeedPostCard } from './FeedPostCard'
import { HomeEmpty } from './HomeEmpty'
import './HomeFeed.css'

type Tab = 'all' | PostStatus

const tabs: { key: Tab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'progress', label: 'In progress' },
  { key: 'review', label: 'Reviewing' },
  { key: 'done', label: 'Completed' },
]

export function HomeFeed() {
  const [tab, setTab] = useState<Tab>('all')
  const { courses, error, loading, reload } = useCourses()
  const due = useAsync(() => api.due(), [])
  useControlPanelSignal(() => {
    void reload()
    due.reload()
  })

  if (courses && courses.length === 0) return <HomeEmpty />
  const posts = (courses ?? []).filter((c) => tab === 'all' || (c.status === 'ready' && c.started && postStatus(c) === tab))

  return (
    <AppShell active="home">
      <main className="feed">
        <header className="feed__header">
          <h1 className="feed__title">Home</h1>
          <div role="tablist" aria-label="Filter courses" className="feed__tabs">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={tab === t.key}
                className={`feed__tab${tab === t.key ? ' feed__tab--active' : ''}`}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </header>

        <div className="feed__body">
          <Composer />
          {loading && <Loading label="Loading your courses…" />}
          {error && <ErrorBox message={`Could not load your courses: ${error}`} onRetry={() => void reload()} />}
          {courses && posts.length === 0 && <p className="feed__none">No courses in this tab yet.</p>}
          {posts.map((c) => (
            <FeedPostCard key={c.course_id} course={c} />
          ))}
        </div>
      </main>

      <RightPanel due={due.data} loading={due.loading} error={due.error} onRetry={due.reload} />
    </AppShell>
  )
}

// Topic + level; ASK builds the course straight away, the same as the New chat screen.
export function Composer() {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [level, setLevel] = useState<LevelKey>('intermediate')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!topic.trim()) return
    navigate(buildLink(topic.trim(), level))
  }

  return (
    <form className="card composer" aria-label="Start a new chat" onSubmit={handleSubmit}>
      <div className="composer__row">
        <div className="av" style={{ width: 48, height: 48, fontSize: 15 }} aria-hidden="true">
          {user.initials}
        </div>
        <label htmlFor="ask" className="sr-only">
          What do you want to learn?
        </label>
        <input
          id="ask"
          type="text"
          className="composer__input"
          placeholder="What do you want to learn today?"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
      </div>

      <div className="composer__actions">
        <LevelSelect value={level} onChange={setLevel} />
        <button className="btn btn-primary composer__ask" type="submit" disabled={!topic.trim()}>
          ASK
        </button>
      </div>
    </form>
  )
}

export function SearchBox() {
  return (
    <div className="rail__search">
      <Icon name="search" size={18} strokeWidth={2} color="var(--icon-muted)" />
      <label htmlFor="search" className="sr-only">
        Search
      </label>
      <input id="search" type="search" placeholder="Search topics, chats, courses..." />
    </div>
  )
}

/** "Due today", "Due tomorrow", "Due in 3 days". */
const dueLabel = (at: string) => {
  const d = dayDistance(at)
  return d.startsWith('In ') ? `Due in ${d.slice(3)}` : `Due ${d.toLowerCase()}`
}
const lateLabel = (days: number) =>
  days < 1 ? 'Due now' : `${Math.floor(days)} day${Math.floor(days) === 1 ? '' : 's'} overdue`

// "Due for review" and "Overdue" from GET /due (soonest first, across courses).
function RightPanel({
  due,
  loading,
  error,
  onRetry,
}: {
  due: DueItem[] | undefined
  loading: boolean
  error: string | null
  onRetry: () => void
}) {
  const overdue = (due ?? []).filter((d) => (d.overdue_days ?? 0) > 0)
  const upcoming = (due ?? []).filter((d) => !((d.overdue_days ?? 0) > 0)).slice(0, 5)

  return (
    <aside className="rail">
      <SearchBox />

      <section className="card rail__card" aria-labelledby="rev">
        <div className="rail__card-head">
          <h2 id="rev" className="label">
            Due for review
          </h2>
          <Link to="/retention" className="rail__see-all">
            See all
          </Link>
        </div>
        {loading && !due && <Loading compact />}
        {error && <ErrorBox message={error} onRetry={onRetry} />}
        {due && upcoming.length === 0 && <p className="rail__note">Nothing scheduled yet.</p>}
        {upcoming.map((r) => (
          <Link key={`${r.course_id}:${r.concept_id}`} to={reviewLink(r.course_id)} className="row-link rail__row">
            <div className="av" style={{ width: 40, height: 40 }} aria-hidden="true">
              <Icon name="clock" size={18} strokeWidth={1.8} />
            </div>
            <div className="rail__row-text">
              <div className="rail__row-title">{r.concept_name}</div>
              <div className="rail__row-sub">
                {dueLabel(r.due_at)} · {r.topic}
              </div>
            </div>
            <Icon name="chevronRight" size={18} strokeWidth={2} color="var(--icon-muted)" />
          </Link>
        ))}
      </section>

      {overdue.length > 0 && (
        <section className="card rail__card rail__card--warn" aria-labelledby="od">
          <div className="rail__card-head">
            <h2 id="od" className="label rail__warn-title">
              Overdue
            </h2>
            <span className="rail__count">{overdue.length} missed</span>
          </div>
          <p className="rail__note">Recall fades fast. Catch these up to protect your retention.</p>
          {overdue.map((o) => (
            <Link key={`${o.course_id}:${o.concept_id}`} to={reviewLink(o.course_id)} className="row-link rail__row">
              <div className="av rail__warn-av" style={{ width: 40, height: 40 }} aria-hidden="true">
                <Icon name="alert" size={18} strokeWidth={1.8} />
              </div>
              <div className="rail__row-text">
                <div className="rail__row-title">{o.concept_name}</div>
                <div className="rail__row-sub rail__row-sub--warn">
                  {lateLabel(o.overdue_days ?? 0)} · {o.topic}
                </div>
              </div>
              <Icon name="chevronRight" size={18} strokeWidth={2} color="var(--icon-muted)" />
            </Link>
          ))}
          <Link to={reviewLink(overdue[0].course_id)} className="btn btn-soft rail__catch-up">
            Catch up now
          </Link>
        </section>
      )}
    </aside>
  )
}
