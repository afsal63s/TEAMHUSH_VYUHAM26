import { useState, type FormEvent } from 'react'
import logo from '../../assets/logo.png'
import mark from '../../assets/mark.png'
import './Login.css'

const points = [
  { n: '1', title: 'Assess your level', sub: 'A short quiz pitched at your level, from novice to advanced' },
  { n: '2', title: 'Find weak spots', sub: 'See exactly which ideas need strengthening' },
  { n: '3', title: 'Learn from curated content', sub: 'Videos, articles and notes gathered for you' },
  { n: '4', title: 'Re-check and retain', sub: 'Spaced reviews measure what you really remember' },
]

export type LoginMode = 'login' | 'signup'

// Not routed yet, and not wired to the backend (which has no user accounts).
export function Login({
  mode = 'login',
  onSubmit,
}: {
  mode?: LoginMode
  onSubmit?: (values: { name: string; email: string; password: string }) => void
}) {
  const [showPw, setShowPw] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = mode === 'login'

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit?.({ name, email, password })
  }

  return (
    <div className="login">
      <main className="login__form-side">
        <div className="login__form-wrap">
          <a href="/" aria-label="OnlyNerds home">
            <img src={logo} alt="OnlyNerds" className="login__logo" />
          </a>
          <div className="login__heading">
            <h1>{login ? 'Welcome back' : 'Create your account'}</h1>
            <p>{login ? 'Log in to continue learning' : 'Start learning in under a minute'}</p>
          </div>

          <form className="login__form" onSubmit={handleSubmit}>
            {!login && (
              <div>
                <label className="login__label" htmlFor="nm">
                  Full name
                </label>
                <input
                  id="nm"
                  className="login__field"
                  type="text"
                  autoComplete="name"
                  placeholder="Alex Rivera"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="login__label" htmlFor="em">
                Email
              </label>
              <input
                id="em"
                className="login__field"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="login__label" htmlFor="pw">
                Password
              </label>
              <div className="login__pw">
                <input
                  id="pw"
                  className="login__field login__field--pw"
                  type={showPw ? 'text' : 'password'}
                  autoComplete={login ? 'current-password' : 'new-password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="login__pw-toggle"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPw((s) => !s)}
                >
                  {showPw ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
            <button type="submit" className="login__btn">
              {login ? 'LOG IN' : 'CREATE ACCOUNT'}
            </button>
          </form>

          <p className="login__legal">
            By continuing you agree to our <a href="#">Terms of Service</a> and{' '}
            <a href="#">Privacy Policy</a>.
          </p>
        </div>
      </main>

      <aside className="login__brand">
        <div className="login__mark">
          <img src={mark} alt="OnlyNerds mark" />
        </div>
        <div className="login__pitch">
          <h2>Learn it once. Keep it for good.</h2>
          <p>
            OnlyNerds finds what you are weak at, builds a short course for exactly that, and checks
            later that it actually stuck.
          </p>
        </div>
        <ul className="login__points">
          {points.map((p) => (
            <li key={p.n} className="login__point">
              <span className="login__point-n">{p.n}</span>
              <span>
                <span className="login__point-title">{p.title}</span>
                <span className="login__point-sub">{p.sub}</span>
              </span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
