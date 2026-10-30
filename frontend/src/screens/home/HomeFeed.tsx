import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { LevelSelect } from '../../components/LevelSelect'
import {
  dueReviews,
  feedPosts,
  overdueReviews,
  user,
  type LevelKey,
  type PostStatus,
} from '../../data/placeholder'
import { buildLink, reviewLink } from '../../routes'
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
  const [params] = useSearchParams()
  // `?empty` previews the no-courses state until real data decides it.
  const allPosts = params.has('empty') ? [] : feedPosts
  const posts = allPosts.filter((p) => tab === 'all' || p.status === tab)

  if (allPosts.length === 0) return <HomeEmpty />

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
          {posts.map((p) => (
            <FeedPostCard key={p.id} post={p} />
          ))}
        </div>
      </main>

      <RightPanel />
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

function RightPanel() {
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
        {dueReviews.map((r) => (
          <Link key={r.title} to={reviewLink(r.title)} className="row-link rail__row">
            <div className="av" style={{ width: 40, height: 40 }} aria-hidden="true">
              <Icon name="clock" size={18} strokeWidth={1.8} />
            </div>
            <div className="rail__row-text">
              <div className="rail__row-title">{r.title}</div>
              <div className="rail__row-sub">{r.due}</div>
            </div>
            <Icon name="chevronRight" size={18} strokeWidth={2} color="var(--icon-muted)" />
          </Link>
        ))}
      </section>

      <section className="card rail__card rail__card--warn" aria-labelledby="od">
        <div className="rail__card-head">
          <h2 id="od" className="label rail__warn-title">
            Overdue
          </h2>
          <span className="rail__count">{overdueReviews.length} missed</span>
        </div>
        <p className="rail__note">Recall fades fast. Catch these up to protect your retention.</p>
        {overdueReviews.map((o) => (
          <Link key={o.title} to={reviewLink(o.title)} className="row-link rail__row">
            <div className="av rail__warn-av" style={{ width: 40, height: 40 }} aria-hidden="true">
              <Icon name="alert" size={18} strokeWidth={1.8} />
            </div>
            <div className="rail__row-text">
              <div className="rail__row-title">{o.title}</div>
              <div className="rail__row-sub rail__row-sub--warn">{o.late}</div>
            </div>
            <Icon name="chevronRight" size={18} strokeWidth={2} color="var(--icon-muted)" />
          </Link>
        ))}
        <Link to={reviewLink('Overdue reviews')} className="btn btn-soft rail__catch-up">
          Catch up now
        </Link>
      </section>
    </aside>
  )
}
