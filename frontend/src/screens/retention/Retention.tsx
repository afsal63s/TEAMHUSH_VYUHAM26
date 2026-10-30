import { useState } from 'react'
import { Link } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Ring } from '../../components/Ring'
import { retention } from '../../data/placeholder'
import { reviewLink } from '../../routes'
import './Retention.css'

const courses = ['All', ...new Set(retention.concepts.map((c) => c.course))]

export function Retention() {
  const [course, setCourse] = useState('All')
  const concepts = retention.concepts.filter((c) => course === 'All' || c.course === course)
  const levelTotal = retention.levels.reduce((s, l) => s + l.n, 0)

  return (
    <AppShell active="retention">
      <main className="ret">
        <header className="ret__header">
          <div>
            <h1>Retention</h1>
            <p className="muted">How well you remember what you have learned, and what to review next.</p>
          </div>
          <Link to={reviewLink('Due reviews')} className="btn btn-primary">
            Start review
          </Link>
        </header>

        <div className="ret__body">
          <section aria-label="Key numbers" className="ret__kpis">
            {retention.kpis.map((k) => (
              <div key={k.label} className="card ret__kpi">
                <div className="ret__kpi-head">
                  <span className="ret__kpi-icon" aria-hidden="true">
                    {k.icon}
                  </span>
                  <span className="ret__kpi-label">{k.label}</span>
                </div>
                <div className="ret__kpi-value">
                  <span>{k.value}</span>
                  <span className={k.good ? 'ret__good' : 'ret__warn'}>{k.delta}</span>
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
                <Ring pct={retention.masteryPct} size={132} stroke={13} label={`${retention.masteryPct} percent overall mastery`}>
                  <span className="ret__ring-pct">{retention.masteryPct}%</span>
                  <span className="ret__ring-sub">Mastery</span>
                </Ring>
                <div>
                  <div className="ret__mastery-level">{retention.masteryLevel}</div>
                  <div className="ret__good ret__mastery-delta">{retention.masteryDelta}</div>
                  <div className="ret__mastery-note">{retention.masteryNote}</div>
                </div>
              </div>
              <div>
                <div
                  className="ret__stack"
                  role="img"
                  aria-label={retention.levels.map((l) => `${l.name} ${l.n}`).join(', ')}
                >
                  {retention.levels.map((l) => (
                    <span key={l.name} style={{ flex: l.n / levelTotal, background: l.color }} />
                  ))}
                </div>
                <ul className="ret__legend">
                  {retention.levels.map((l) => (
                    <li key={l.name}>
                      <span className="ret__swatch" style={{ background: l.color }} />
                      <span className="ret__legend-name">{l.name}</span>
                      <strong>{l.n}</strong>
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
                  { n: retention.memory.strong, label: 'Strong', color: '#0A4C8A' },
                  { n: retention.memory.fading, label: 'Fading', color: '#7FB5E6' },
                  { n: retention.memory.atRisk, label: 'At risk', color: '#D97706' },
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
              <ForgettingCurve concept={retention.memory.curveConcept} />
            </div>
          </section>

          <section className="ret__row">
            <div className="card ret__panel ret__panel--full" aria-labelledby="cp">
              <div className="ret__panel-head ret__panel-head--center">
                <h2 id="cp" className="ret__label">
                  Concept progress
                </h2>
                <div role="tablist" aria-label="Filter by course" className="ret__tabs">
                  {courses.map((c) => (
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
              </div>
              <div className="ret__table-head">
                <span className="ret__col-name">Concept</span>
                <span className="ret__col-mastery">Mastery</span>
                <span className="ret__col-memory">Memory</span>
              </div>
              {concepts.map((c) => {
                const strength = c.strength >= 80 ? 'strong' : c.strength >= 60 ? 'fading' : 'risk'
                return (
                  <div key={c.name} className="ret__concept">
                    <div className="ret__col-name">
                      <div className="ret__concept-name">{c.name}</div>
                      <div className="ret__concept-course">{c.course}</div>
                    </div>
                    <div className="ret__col-mastery ret__concept-mastery">
                      <div className="ret__track">
                        <div
                          className="ret__fill"
                          style={{
                            width: `${c.pct}%`,
                            background: c.pct >= 75 ? '#0770C9' : c.pct >= 50 ? '#7FB5E6' : '#D97706',
                          }}
                        />
                      </div>
                      <span>{c.pct}%</span>
                    </div>
                    <span className={`ret__col-memory ret__memory ret__memory--${strength}`}>
                      {strength === 'strong' ? 'Strong' : strength === 'fading' ? 'Fading' : 'At risk'} · {c.strength}%
                    </span>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="ret__row">
            <div className="card ret__panel ret__panel--half" aria-labelledby="rv">
              <h2 id="rv" className="ret__label ret__label--gap">
                Reviews
              </h2>
              <div className="ret__group-head">
                <span className="ret__overdue-title">Overdue</span>
                <span className="ret__overdue-count">{retention.overdue.length}</span>
              </div>
              {retention.overdue.map((o) => (
                <div key={o.name} className="ret__review">
                  <span className="ret__review-bar" aria-hidden="true" />
                  <div className="ret__review-text">
                    <div className="ret__review-name">{o.name}</div>
                    <div className="ret__review-late">{o.late}</div>
                  </div>
                  <Link to={reviewLink(o.name)} className="btn btn-soft ret__small-btn">
                    Review
                  </Link>
                </div>
              ))}
              <div className="ret__group-head ret__group-head--spaced">
                <span className="ret__upcoming-title">Upcoming</span>
                <span className="muted ret__upcoming-sub">next 7 days</span>
              </div>
              {retention.upcoming.map((u, i) => (
                <div key={u.name} className="ret__review">
                  <span className={`ret__day${i === 0 ? ' ret__day--today' : ''}`}>{u.day}</span>
                  <div className="ret__review-text">
                    <div className="ret__review-name">{u.name}</div>
                    <div className="ret__review-meta">{u.meta}</div>
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
              {retention.attention.map((a, i) => (
                <div key={a.name} className="ret__attention">
                  <span className={`ret__rank${i === 0 ? ' ret__rank--top' : ''}`}>{i + 1}</span>
                  <div className="ret__attention-body">
                    <div>
                      <div className="ret__attention-name">{a.name}</div>
                      <div className="ret__attention-course">{a.course}</div>
                    </div>
                    <div className="ret__reasons">
                      {a.reasons.map((r) => (
                        <span key={r.text} className={`ret__reason${r.warn ? ' ret__reason--warn' : ''}`}>
                          {r.text}
                        </span>
                      ))}
                    </div>
                  </div>
                  <Link to={`/chat/${a.chatId}`} className="btn btn-soft ret__small-btn">
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
                  <strong>{retention.misconceptions.active}</strong> active
                </span>
                <span>
                  <strong>{retention.misconceptions.resolvedThisMonth}</strong> resolved this month
                </span>
              </div>
            </div>
            <div className="ret__mcs">
              {retention.misconceptions.items.map((m) => (
                <article key={m.title} className="ret__mc">
                  <div className="ret__mc-head">
                    <span className="ret__mc-concept">{m.concept}</span>
                    <span className={`ret__mc-status${m.recurring ? ' ret__mc-status--warn' : ''}`}>
                      {m.recurring ? 'Recurring' : 'Improving'}
                    </span>
                  </div>
                  <h3>{m.title}</h3>
                  <p>{m.detail}</p>
                  <div className="ret__mc-foot">
                    <span>{m.seen}</span>
                    <Link to={`/chat/${m.chatId}`}>See the fix</Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </main>
    </AppShell>
  )
}

// Forgetting curve with four reviews; each review resets recall and slows the decay.
function ForgettingCurve({ concept }: { concept: string }) {
  const reviewsAt = [0, 3, 8, 16]
  const strengths = [6, 10, 14, 18]
  const today = 24
  const cx = (d: number) => 34 + (d / 30) * 316
  const cy = (v: number) => 10 + ((100 - v) / 100) * 134

  let path = ''
  let lastIdx = 0
  for (let t = 0; t <= today + 0.001; t += 0.5) {
    let idx = 0
    reviewsAt.forEach((r, j) => {
      if (t >= r) idx = j
    })
    const val = 100 * Math.exp(-(t - reviewsAt[idx]) / strengths[idx])
    if (t === reviewsAt[idx] && idx > 0) {
      const prev = 100 * Math.exp(-(t - reviewsAt[idx - 1]) / strengths[idx - 1])
      path += `L${cx(t).toFixed(1)} ${cy(prev).toFixed(1)} `
    }
    path += `${path === '' ? 'M' : 'L'}${cx(t).toFixed(1)} ${cy(val).toFixed(1)} `
    lastIdx = idx
  }
  const now = Math.round(100 * Math.exp(-(today - reviewsAt[lastIdx]) / strengths[lastIdx]))

  return (
    <>
      <div className="ret__curve-head">
        <div className="ret__curve-title">Forgetting curve: {concept}</div>
        <div className="ret__curve-sub">
          Each review makes the memory last longer. Strength is now {now}%, below your 70% line.
        </div>
      </div>
      <svg
        viewBox="0 0 360 170"
        className="ret__chart"
        role="img"
        aria-label={`Forgetting curve with four reviews. Predicted recall today is ${now} percent.`}
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
        <g fill="#0A4C8A">
          {reviewsAt.map((r) => (
            <circle key={r} cx={cx(r)} cy="10" r="4" />
          ))}
        </g>
        <path d={`M${cx(today)} 10V144`} stroke="#334155" strokeWidth="1.2" strokeDasharray="3 3" fill="none" />
        <circle cx={cx(today)} cy={cy(now)} r="5.5" fill="#FFFFFF" stroke="#D97706" strokeWidth="3" />
        <g fill="#5B6577" fontSize="10">
          <text x="34" y="162">Day 0</text>
          <text x={cx(today)} y="162" textAnchor="middle">
            Today
          </text>
          <text x="350" y="162" textAnchor="end">
            Day 30
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
