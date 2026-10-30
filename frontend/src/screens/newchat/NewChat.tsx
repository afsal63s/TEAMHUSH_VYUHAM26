import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import mark from '../../assets/mark.png'
import { AppShell } from '../../components/AppShell'
import { Icon } from '../../components/Icon'
import { levels, type LevelKey } from '../../data/placeholder'
import { buildLink } from '../../routes'
import '../../components/LevelSelect.css'
import './NewChat.css'

// Topic + level, then on to building the course.
export function NewChat() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [topic, setTopic] = useState(params.get('topic') ?? '')
  const [level, setLevel] = useState<LevelKey>(
    levels.find((l) => l.key === params.get('level'))?.key ?? 'intermediate',
  )
  const current = levels.find((l) => l.key === level)!

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!topic.trim()) return
    navigate(buildLink(topic.trim(), current.key))
  }

  return (
    <AppShell>
      <main className="newchat">
        <header className="newchat__header">
          <Link to="/" className="icon-btn" aria-label="Close and go home">
            <Icon name="close" strokeWidth={2} />
          </Link>
        </header>

        <div className="newchat__body">
          <div className="newchat__intro">
            <div className="newchat__mark" aria-hidden="true">
              <img src={mark} alt="" />
            </div>
            <h1>What do you want to learn today?</h1>
            <p>Type any topic. I'll check where you stand, then build your course.</p>
          </div>

          <div className="newchat__entry">
            <form className="newchat__form" onSubmit={handleSubmit}>
              <label htmlFor="topic" className="sr-only">
                What do you want to learn?
              </label>
              <textarea
                id="topic"
                rows={2}
                placeholder="e.g. Backpropagation in neural networks"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    e.currentTarget.form?.requestSubmit()
                  }
                }}
              />
              <div className="newchat__tools">
                <button type="submit" className="newchat__start" aria-label="Start" disabled={!topic.trim()}>
                  <Icon name="arrowUp" strokeWidth={2.2} />
                </button>
              </div>
            </form>

            <div className="newchat__levels">
              <div className="newchat__levels-label">Your level on this topic</div>
              <div role="group" aria-label="Your level" className="newchat__level-group">
                {levels.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    className={`lvl${l.key === level ? ' lvl--on' : ''}`}
                    aria-pressed={l.key === level}
                    onClick={() => setLevel(l.key)}
                  >
                    <span className="lvl__bars" aria-hidden="true">
                      {[5, 8, 12, 16].map((h, i) => (
                        <span key={h} className={i < l.bars ? 'lvl__bar lvl__bar--on' : 'lvl__bar'} style={{ height: h }} />
                      ))}
                    </span>
                    {l.name}
                  </button>
                ))}
              </div>
              <div className="newchat__level-desc">{current.desc}</div>
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  )
}
