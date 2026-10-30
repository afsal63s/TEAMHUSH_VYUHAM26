import { Link, useNavigate } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { Ring } from '../../components/Ring'
import { Composer, SearchBox } from './HomeFeed'
import './HomeFeed.css'

const emptyPrompts = ['Explain transformers', 'Photosynthesis basics', 'System design roadmap', 'Human psychology']

const steps = [
  { n: '1', title: 'Assess', sub: 'A short quiz at your level' },
  { n: '2', title: 'Find weak spots', sub: 'See what to strengthen' },
  { n: '3', title: 'Learn', sub: 'Curated articles and videos' },
  { n: '4', title: 'Re-check', sub: 'Spaced reviews that stick' },
]

// Home when the learner has no courses yet.
export function HomeEmpty() {
  const navigate = useNavigate()

  return (
    <AppShell active="home">
      <main className="feed">
        <header className="feed__header feed__header--plain">
          <h1 className="feed__title">Home</h1>
        </header>

        <div className="feed__body">
          <Composer />

          <section className="card empty" aria-labelledby="empty">
            <svg width="200" height="130" viewBox="0 0 200 130" aria-hidden="true">
              <rect x="20" y="28" width="160" height="84" rx="14" fill="#EAF3FC" stroke="#CFE4F8" strokeDasharray="6 5" />
              <rect x="38" y="46" width="52" height="48" rx="8" fill="#FFFFFF" stroke="#CFE4F8" />
              <g strokeLinecap="round" strokeWidth="6">
                <path d="M104 54h52" stroke="#CFE4F8" />
                <path d="M104 70h38" stroke="#E4EEF9" />
                <path d="M104 86h46" stroke="#E4EEF9" />
              </g>
              <circle cx="150" cy="30" r="16" fill="#0770C9" />
              <path d="M150 23v14M143 30h14" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" />
            </svg>
            <h2 id="empty" className="empty__title">
              No courses yet
            </h2>
            <p className="empty__text">
              Tell me what you want to learn. I'll check where you stand, find your weak spots, and gather a
              short course just for you. It will show up here.
            </p>
            <Link to="/new" className="btn btn-primary empty__cta">
              Start your first chat
            </Link>
            <div className="empty__chips">
              {emptyPrompts.map((p) => (
                <button
                  key={p}
                  className="chip"
                  type="button"
                  onClick={() => navigate(`/new?topic=${encodeURIComponent(p)}`)}
                >
                  {p}
                </button>
              ))}
            </div>
          </section>

          <section className="card how" aria-labelledby="hw">
            <h2 id="hw" className="label how__title">
              How it works
            </h2>
            <ol className="how__steps">
              {steps.map((s) => (
                <li key={s.n} className="how__step">
                  <span className="how__n">{s.n}</span>
                  <span className="how__step-title">{s.title}</span>
                  <span className="how__step-sub">{s.sub}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </main>

      <aside className="rail">
        <SearchBox />

        <section className="card rail__card rail__empty-card" aria-labelledby="rev">
          <h2 id="rev" className="label">
            Due for review
          </h2>
          <div className="rail__empty">
            <div className="av" style={{ width: 48, height: 48 }} aria-hidden="true">
              <Icon name="clock" size={22} strokeWidth={1.8} />
            </div>
            <div className="rail__empty-title">Nothing due yet</div>
            <div className="rail__empty-text">Reviews are scheduled after you finish your first course.</div>
          </div>
        </section>

        <section className="card rail__card rail__empty-card" aria-labelledby="ms">
          <h2 id="ms" className="label">
            Mastery
          </h2>
          <div className="rail__empty">
            <Ring pct={null} size={72} stroke={7}>
              <span className="rail__empty-ring">--</span>
            </Ring>
            <div className="rail__empty-title">No mastery data</div>
            <div className="rail__empty-text">Take your first assessment to see where you stand.</div>
            <Link to="/new" className="btn btn-soft rail__empty-btn">
              Take an assessment
            </Link>
          </div>
        </section>
      </aside>
    </AppShell>
  )
}
