import { useState } from 'react'
import { Link } from 'react-router'
import { api } from '../../api/client'
import { dayDistance, levelFromPct, mean, nameMap, parseUtc } from '../../api/format'
import { getCourseCached, useAsync, useControlPanelSignal, useCourses } from '../../api/hooks'
import type { CourseSummary, CreateCourseOut, MasteryOut } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { Ring } from '../../components/Ring'
import { ErrorBox, Loading } from '../../components/Status'
import { chatLink, reviewLink } from '../../routes'
import './Retention.css'

const DAY = 24 * 60 * 60 * 1000

interface CourseData {
  summary: CourseSummary
  state: MasteryOut
  course: CreateCourseOut
}

interface ConceptRow {
  key: string
  courseId: string
  course: string
  name: string
  p: number
  /** Recall probability now; null until the concept has a review schedule. */
  r: number | null
  stability: number
  lastReviewed: Date | null
  now: Date
  needsHelp: boolean
  lapses: number
}

// Mastery bands for the stacked bar (0.85+ is the backend's "mastered").
const BANDS = [
  { name: 'Mastered', min: 0.85, color: '#0A4C8A' },
  { name: 'Solid', min: 0.6, color: '#0770C9' },
  { name: 'Developing', min: 0.3, color: '#7FB5E6' },
  { name: 'Weak', min: -1, color: '#D97706' },
]

// Retention across every started course: GET /courses, GET .../state per course, GET /due.
export function Retention() {
  const { courses, error: coursesError, reload: reloadCourses } = useCourses()
  const started = (courses ?? []).filter((c) => c.status === 'ready' && c.started)
  const ids = started.map((c) => c.course_id).join(',')

  const data = useAsync<CourseData[]>(
    () =>
      Promise.all(
        started.map(async (summary) => ({
          summary,
          state: await api.state(summary.course_id),
          course: await getCourseCached(summary.course_id),
        })),
      ),
    [ids],
  )
  const due = useAsync(() => api.due(), [])
  useControlPanelSignal(() => {
    void reloadCourses()
    data.reload()
    due.reload()
  })

  const [course, setCourse] = useState('All')
  // Fallback "now" until a course's state returns the learner's simulated now.
  const [mountedAt] = useState(() => new Date())
  const [selected, setSelected] = useState<string | null>(null)

  const loading = !courses || data.loading
  const error = coursesError ?? data.error
  const all = data.data ?? []

  // One row per concept, across courses.
  const rows: ConceptRow[] = all.flatMap(({ summary, state, course: graph }) => {
    const name = nameMap(graph)
    const now = parseUtc(state.now) ?? mountedAt
    return state.concepts.map((c) => {
      const lastReviewed = parseUtc(c.last_reviewed_at)
      return {
        key: `${summary.course_id}:${c.concept_id}`,
        courseId: summary.course_id,
        course: summary.topic,
        name: name(c.concept_id),
        p: c.p_mastery ?? 0,
        r: lastReviewed ? (state.retrievability?.[c.concept_id] ?? null) : null,
        stability: c.stability_days ?? 0,
        lastReviewed,
        now,
        needsHelp: !!c.needs_help,
        lapses: c.lapses ?? 0,
      }
    })
  })
  const reviewed = rows.filter((r) => r.r !== null)

  // KPI: pass rates pooled over courses (null until there is data).
  const pool = (total: (s: MasteryOut) => number, passed: (s: MasteryOut) => number) => {
    const t = all.reduce((a, d) => a + total(d.state), 0)
    return t > 0 ? all.reduce((a, d) => a + passed(d.state), 0) / t : null
  }
  const reviewRate = pool(
    (s) => s.retention?.reviews_total ?? 0,
    (s) => s.retention?.reviews_passed ?? 0,
  )
  const delayedRate = pool(
    (s) => s.retention?.delayed_reviews_total ?? 0,
    (s) => (s.retention?.delayed_pass_rate ?? 0) * (s.retention?.delayed_reviews_total ?? 0),
  )
  const reviewsTotal = all.reduce((a, d) => a + (d.state.retention?.reviews_total ?? 0), 0)
  const mastered = rows.filter((r) => r.p >= 0.85).length

  const dueItems = due.data ?? []
  const overdue = dueItems.filter((d) => (d.overdue_days ?? 0) > 0)
  const upcoming = dueItems.filter((d) => {
    const at = parseUtc(d.due_at)
    return !((d.overdue_days ?? 0) > 0) && at && at.getTime() - mountedAt.getTime() <= 7 * DAY
  })
  const firstDue = overdue[0] ?? dueItems[0]

  // Mastery overview: mean p_mastery; change = latest history sample vs one about 30 days earlier.
  const avg = mean(rows.map((r) => r.p))
  const deltas = all
    .map(({ state }) => {
      const h = state.history ?? []
      if (h.length < 2) return null
      const last = h[h.length - 1]
      const cutoff = (parseUtc(last.at)?.getTime() ?? 0) - 30 * DAY
      const old = h.find((x) => (parseUtc(x.at)?.getTime() ?? 0) >= cutoff) ?? h[0]
      return { d: last.avg_mastery - old.avg_mastery, w: state.concepts.length }
    })
    .filter((x): x is { d: number; w: number } => x !== null)
  const wsum = deltas.reduce((a, x) => a + x.w, 0)
  const delta = wsum ? deltas.reduce((a, x) => a + x.d * x.w, 0) / wsum : null

  const bandCounts = BANDS.map((b, i) => ({
    ...b,
    n: rows.filter((r) => r.p >= b.min && (i === 0 || r.p < BANDS[i - 1].min)).length,
  }))

  const strong = reviewed.filter((r) => (r.r ?? 0) >= 0.8).length
  const fading = reviewed.filter((r) => (r.r ?? 0) >= 0.6 && (r.r ?? 0) < 0.8).length
  const atRisk = reviewed.length - strong - fading

  const curveRow =
    reviewed.find((r) => r.key === selected) ?? [...reviewed].sort((a, b) => (a.r ?? 1) - (b.r ?? 1))[0] ?? null

  const courseTabs = ['All', ...started.map((c) => c.topic)]
  const tableRows = rows.filter((r) => course === 'All' || r.course === course)

  const attention = [
    ...rows.filter((r) => r.needsHelp),
    ...[...reviewed].filter((r) => !r.needsHelp && (r.r ?? 1) < 0.8).sort((a, b) => (a.r ?? 1) - (b.r ?? 1)),
  ].slice(0, 4)

  const miscon = all.flatMap(({ summary, state, course: graph }) =>
    state.misconceptions.map((m) => ({ ...m, courseId: summary.course_id, concept: nameMap(graph)(m.concept_id) })),
  )
  const activeMis = miscon.filter((m) => m.status !== 'resolved')
  const resolvedMis = miscon.filter((m) => m.status === 'resolved')

  const kpis = [
    {
      icon: 'R',
      label: 'Retention rate',
      value: delayedRate === null ? null : `${Math.round(delayedRate * 100)}%`,
      sub: 'Recall after 7+ days',
    },
    {
      icon: 'P',
      label: 'Review pass rate',
      value: reviewRate === null ? null : `${Math.round(reviewRate * 100)}%`,
      sub: reviewsTotal ? `${reviewsTotal} review rounds so far` : 'No reviews yet',
    },
    { icon: 'M', label: 'Concepts mastered', value: String(mastered), sub: `Out of ${rows.length} tracked` },
    {
      icon: 'O',
      label: 'Overdue reviews',
      value: due.data ? String(overdue.length) : null,
      warn: overdue.length > 0,
      sub: `${upcoming.length} due in the next 7 days`,
    },
  ]

  return (
    <AppShell active="retention">
      <main className="ret">
        <header className="ret__header">
          <div>
            <h1>Retention</h1>
            <p className="muted">How well you remember what you have learned, and what to review next.</p>
          </div>
          {firstDue ? (
            <Link to={reviewLink(firstDue.course_id)} className="btn btn-primary">
              Start review
            </Link>
          ) : (
            <button type="button" className="btn btn-primary" disabled title="Nothing is due yet">
              Start review
            </button>
          )}
        </header>

        <div className="ret__body">
          {error && <ErrorBox message={`Could not load retention: ${error}`} onRetry={() => (coursesError ? void reloadCourses() : data.reload())} />}
          {!error && loading && <Loading label="Loading your progress…" />}
          {!error && !loading && started.length === 0 && (
            <section className="card ret__panel ret__empty">
              <h2 className="ret__empty-title">Nothing to show yet</h2>
              <p className="muted">Take a course's first assessment and your retention appears here.</p>
              <Link to="/new" className="btn btn-primary">
                Start a course
              </Link>
            </section>
          )}

          {!error && !loading && started.length > 0 && (
            <>
              <section aria-label="Key numbers" className="ret__kpis">
                {kpis.map((k) => (
                  <div key={k.label} className="card ret__kpi">
                    <div className="ret__kpi-head">
                      <span className="ret__kpi-icon" aria-hidden="true">
                        {k.icon}
                      </span>
                      <span className="ret__kpi-label">{k.label}</span>
                    </div>
                    <div className="ret__kpi-value">
                      {k.value === null ? (
                        <span className="ret__kpi-empty">Not enough data yet</span>
                      ) : (
                        <span className={k.warn ? 'ret__warn' : undefined}>{k.value}</span>
                      )}
                    </div>
                    <div className="ret__kpi-sub">{k.sub}</div>
                  </div>
                ))}
              </section>

              <section className="ret__row">
                <div className="card ret__panel ret__panel--narrow" aria-labelledby="mo">
                  <h2 id="mo" className="ret__label">
                    Mastery overview
                  </h2>
                  <div className="ret__mastery">
                    <Ring pct={avg === null ? null : Math.round(avg * 100)} size={132} stroke={13} label={`${Math.round((avg ?? 0) * 100)} percent overall mastery`}>
                      <span className="ret__ring-pct">{avg === null ? '--' : `${Math.round(avg * 100)}%`}</span>
                      <span className="ret__ring-sub">Mastery</span>
                    </Ring>
                    <div>
                      <div className="ret__mastery-level">{levelFromPct((avg ?? 0) * 100)}</div>
                      {delta !== null && Math.round(delta * 100) !== 0 && (
                        <div className={`ret__mastery-delta ${delta > 0 ? 'ret__good' : 'ret__warn'}`}>
                          {delta > 0 ? '+' : '−'}
                          {Math.abs(Math.round(delta * 100))} pts this month
                        </div>
                      )}
                      <div className="ret__mastery-note">
                        {rows.length} concepts tracked across {started.length} course{started.length === 1 ? '' : 's'}
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="ret__stack" role="img" aria-label={bandCounts.map((b) => `${b.name} ${b.n}`).join(', ')}>
                      {bandCounts.map((b) => b.n > 0 && <span key={b.name} style={{ flex: b.n, background: b.color }} />)}
                    </div>
                    <ul className="ret__legend">
                      {bandCounts.map((b) => (
                        <li key={b.name}>
                          <span className="ret__swatch" style={{ background: b.color }} />
                          <span className="ret__legend-name">{b.name}</span>
                          <strong>{b.n}</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="card ret__panel ret__panel--narrow" aria-labelledby="ms">
                  <h2 id="ms" className="ret__label">
                    Memory strength
                  </h2>
                  <div className="ret__strengths">
                    {[
                      { n: strong, label: 'Strong', color: '#0A4C8A' },
                      { n: fading, label: 'Fading', color: '#7FB5E6' },
                      { n: atRisk, label: 'At risk', color: '#D97706' },
                    ].map((s) => (
                      <div key={s.label} className="ret__strength">
                        <div className="ret__strength-n">{s.n}</div>
                        <div className="ret__strength-label">
                          <span className="ret__swatch ret__swatch--sm" style={{ background: s.color }} />
                          {s.label}
                        </div>
                      </div>
                    ))}
                  </div>
                  {curveRow ? (
                    <ForgettingCurve row={curveRow} />
                  ) : (
                    <p className="muted ret__curve-sub">Memory curves appear once a concept is mastered and scheduled for review.</p>
                  )}
                </div>
              </section>

              <section className="ret__row">
                <div className="card ret__panel ret__panel--full" aria-labelledby="cp">
                  <div className="ret__panel-head ret__panel-head--center">
                    <h2 id="cp" className="ret__label">
                      Concept progress
                    </h2>
                    {courseTabs.length > 2 && (
                      <div role="tablist" aria-label="Filter by course" className="ret__tabs">
                        {courseTabs.map((c) => (
                          <button
                            key={c}
                            type="button"
                            role="tab"
                            aria-selected={c === course}
                            className={`ret__tab${c === course ? ' ret__tab--on' : ''}`}
                            onClick={() => setCourse(c)}
                          >
                            {c}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="ret__table-head">
                    <span className="ret__col-name">Concept</span>
                    <span className="ret__col-mastery">Mastery</span>
                    <span className="ret__col-memory">Memory</span>
                  </div>
                  {tableRows.map((c) => {
                    const pctM = Math.round(c.p * 100)
                    const strength = c.r === null ? 'none' : c.r >= 0.8 ? 'strong' : c.r >= 0.6 ? 'fading' : 'risk'
                    return (
                      <button
                        key={c.key}
                        type="button"
                        className={`ret__concept${curveRow?.key === c.key ? ' ret__concept--on' : ''}`}
                        onClick={() => c.r !== null && setSelected(c.key)}
                        disabled={c.r === null}
                        title={c.r === null ? undefined : 'Show its forgetting curve'}
                      >
                        <div className="ret__col-name">
                          <div className="ret__concept-name">{c.name}</div>
                          <div className="ret__concept-course">{c.course}</div>
                        </div>
                        <div className="ret__col-mastery ret__concept-mastery">
                          <div className="ret__track">
                            <div
                              className="ret__fill"
                              style={{ width: `${pctM}%`, background: pctM >= 75 ? '#0770C9' : pctM >= 50 ? '#7FB5E6' : '#D97706' }}
                            />
                          </div>
                          <span>{pctM}%</span>
                        </div>
                        <span className={`ret__col-memory ret__memory ret__memory--${strength}`}>
                          {c.r === null
                            ? 'Not reviewed'
                            : `${strength === 'strong' ? 'Strong' : strength === 'fading' ? 'Fading' : 'At risk'} · ${Math.round(c.r * 100)}%`}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </section>

              <section className="ret__row">
                <div className="card ret__panel ret__panel--half" aria-labelledby="rv">
                  <h2 id="rv" className="ret__label ret__label--gap">
                    Reviews
                  </h2>
                  {due.error && <ErrorBox message={due.error} onRetry={due.reload} />}
                  <div className="ret__group-head">
                    <span className="ret__overdue-title">Overdue</span>
                    <span className="ret__overdue-count">{overdue.length}</span>
                  </div>
                  {overdue.length === 0 && <p className="muted ret__none">Nothing overdue.</p>}
                  {overdue.map((o) => (
                    <div key={`${o.course_id}:${o.concept_id}`} className="ret__review">
                      <span className="ret__review-bar" aria-hidden="true" />
                      <div className="ret__review-text">
                        <div className="ret__review-name">{o.concept_name}</div>
                        <div className="ret__review-late">
                          {(o.overdue_days ?? 0) < 1 ? 'Due now' : `${Math.floor(o.overdue_days ?? 0)} days overdue`} · {o.topic}
                        </div>
                      </div>
                      <Link to={reviewLink(o.course_id)} className="btn btn-soft ret__small-btn">
                        Review
                      </Link>
                    </div>
                  ))}
                  <div className="ret__group-head ret__group-head--spaced">
                    <span className="ret__upcoming-title">Upcoming</span>
                    <span className="muted ret__upcoming-sub">next 7 days</span>
                  </div>
                  {upcoming.length === 0 && <p className="muted ret__none">Nothing in the next 7 days.</p>}
                  {upcoming.slice(0, 6).map((u, i) => (
                    <div key={`${u.course_id}:${u.concept_id}`} className="ret__review">
                      <span className={`ret__day${i === 0 ? ' ret__day--today' : ''}`}>{dayDistance(u.due_at)}</span>
                      <div className="ret__review-text">
                        <div className="ret__review-name">{u.concept_name}</div>
                        <div className="ret__review-meta">{u.topic}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="card ret__panel ret__panel--half" aria-labelledby="na">
                  <div className="ret__panel-head">
                    <h2 id="na" className="ret__label">
                      Needs attention
                    </h2>
                    <span className="muted ret__ranked">Ranked by urgency</span>
                  </div>
                  {attention.length === 0 && <p className="muted ret__none">Nothing needs attention right now.</p>}
                  {attention.map((a, i) => (
                    <div key={a.key} className="ret__attention">
                      <span className={`ret__rank${i === 0 ? ' ret__rank--top' : ''}`}>{i + 1}</span>
                      <div className="ret__attention-body">
                        <div>
                          <div className="ret__attention-name">{a.name}</div>
                          <div className="ret__attention-course">{a.course}</div>
                        </div>
                        <div className="ret__reasons">
                          {a.needsHelp && <span className="ret__reason ret__reason--warn">Needs help</span>}
                          {a.r !== null && <span className="ret__reason ret__reason--warn">Memory {Math.round(a.r * 100)}%</span>}
                          {a.lapses > 0 && (
                            <span className="ret__reason">
                              {a.lapses} lapse{a.lapses === 1 ? '' : 's'}
                            </span>
                          )}
                        </div>
                      </div>
                      <Link to={chatLink(a.courseId)} className="btn btn-soft ret__small-btn">
                        Strengthen
                      </Link>
                    </div>
                  ))}
                </div>
              </section>

              <section className="card ret__panel" aria-labelledby="mc">
                <div className="ret__panel-head">
                  <div>
                    <h2 id="mc" className="ret__label">
                      Misconception insights
                    </h2>
                    <p className="muted ret__mc-sub">Patterns in your wrong answers, not just topics you missed.</p>
                  </div>
                  <div className="ret__mc-stats">
                    <span>
                      <strong>{activeMis.length}</strong> active
                    </span>
                    <span>
                      <strong>{resolvedMis.length}</strong> resolved
                    </span>
                  </div>
                </div>
                {miscon.length === 0 && <p className="muted ret__none">No misconceptions spotted yet.</p>}
                <div className="ret__mcs">
                  {[...activeMis, ...resolvedMis].slice(0, 6).map((m) => (
                    <article key={`${m.courseId}:${m.tag}`} className="ret__mc">
                      <div className="ret__mc-head">
                        <span className="ret__mc-concept">{m.concept}</span>
                        <span className={`ret__mc-status${m.status === 'resolved' ? '' : ' ret__mc-status--warn'}`}>
                          {m.status === 'confirmed' ? 'Recurring' : m.status === 'resolved' ? 'Improving' : 'Suspected'}
                        </span>
                      </div>
                      <h3>{m.description || m.tag}</h3>
                      <div className="ret__mc-foot">
                        <span>
                          Seen {m.evidence ?? 0} time{m.evidence === 1 ? '' : 's'}
                        </span>
                        <Link to={chatLink(m.courseId)}>See the fix</Link>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </main>
    </AppShell>
  )
}

// Forgetting curve since the concept's last review: R = 0.9^(days / stability_days).
function ForgettingCurve({ row }: { row: ConceptRow }) {
  const stability = Math.max(row.stability, 0.1)
  const since = row.lastReviewed ? Math.max(0, (row.now.getTime() - row.lastReviewed.getTime()) / DAY) : 0
  const span = Math.max(7, Math.ceil(Math.max(since * 1.5, stability * 2)))
  const R = (t: number) => 100 * Math.pow(0.9, t / stability)
  const cx = (d: number) => 34 + (d / span) * 316
  const cy = (v: number) => 10 + ((100 - v) / 100) * 134
  const steps = 60
  const path = Array.from({ length: steps + 1 }, (_, i) => {
    const t = (i / steps) * span
    return `${i === 0 ? 'M' : 'L'}${cx(t).toFixed(1)} ${cy(R(t)).toFixed(1)}`
  }).join(' ')
  const now = Math.round(row.r !== null ? row.r * 100 : R(since))

  return (
    <>
      <div className="ret__curve-head">
        <div className="ret__curve-title">Forgetting curve: {row.name}</div>
        <div className="ret__curve-sub">
          Memory lasts about {row.stability.toFixed(1)} days now; each passed review makes it last longer. Strength is{' '}
          {now}%, {now < 70 ? 'below' : 'above'} your 70% line.
        </div>
      </div>
      <svg
        viewBox="0 0 360 170"
        className="ret__chart"
        role="img"
        aria-label={`Forgetting curve for ${row.name}. Predicted recall today is ${now} percent.`}
      >
        <g stroke="#EEF2F6">
          <path d="M34 10H350M34 77H350M34 144H350" />
        </g>
        <g fill="#5B6577" fontSize="10" textAnchor="end">
          <text x="28" y="14">100</text>
          <text x="28" y="81">50</text>
          <text x="28" y="148">0</text>
        </g>
        <path d="M34 50.2H350" stroke="#D97706" strokeWidth="1.5" strokeDasharray="5 4" fill="none" />
        <path d={path} fill="none" stroke="#0770C9" strokeWidth="2.5" strokeLinejoin="round" />
        <circle cx={cx(0)} cy={cy(100)} r="4" fill="#0A4C8A" />
        <path d={`M${cx(since)} 10V144`} stroke="#334155" strokeWidth="1.2" strokeDasharray="3 3" fill="none" />
        <circle cx={cx(since)} cy={cy(now)} r="5.5" fill="#FFFFFF" stroke="#D97706" strokeWidth="3" />
        <g fill="#5B6577" fontSize="10">
          <text x="34" y="162">Last review</text>
          <text x={cx(since)} y="162" textAnchor="middle">
            {since > span * 0.15 && since < span * 0.85 ? 'Today' : ''}
          </text>
          <text x="350" y="162" textAnchor="end">
            Day {span}
          </text>
        </g>
      </svg>
      <div className="ret__curve-keys">
        <span>
          <span className="ret__dot" />
          Review
        </span>
        <span>
          <span className="ret__key-dash" />
          70% line
        </span>
      </div>
    </>
  )
}
