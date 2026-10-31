import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { api, ApiError, errorText, setPassword } from '../../api/client'
import logo from '../../assets/logo.png'
import mark from '../../assets/mark.png'
import './Login.css'

const points = [
  { n: '1', title: 'Assess your level', sub: 'A short quiz pitched at your level, from novice to advanced' },
  { n: '2', title: 'Find weak spots', sub: 'See exactly which ideas need strengthening' },
  { n: '3', title: 'Learn from curated content', sub: 'Videos, articles and notes gathered for you' },
  { n: '4', title: 'Re-check and retain', sub: 'Spaced reviews measure what you really remember' },
]

// The backend has one shared password (no accounts): check it with GET /auth/check, then store it.
export function Login() {
  const navigate = useNavigate()
  const [showPw, setShowPw] = useState(false)
  const [password, setPw] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await api.authCheck(password)
      setPassword(password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? 'Wrong password' : errorText(err))
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <main className="login__form-side">
        <div className="login__form-wrap">
          <img src={logo} alt="OnlyNerds" className="login__logo" />
          <div className="login__heading">
            <h1>Welcome back</h1>
            <p>Enter the password to continue learning</p>
          </div>

          <form className="login__form" onSubmit={handleSubmit}>
            <div>
              <label className="login__label" htmlFor="pw">
                Password
              </label>
              <div className="login__pw">
                <input
                  id="pw"
                  className="login__field login__field--pw"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPw(e.target.value)}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? 'pw-error' : undefined}
                  autoFocus
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
              {error && (
                <p id="pw-error" className="login__error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <button type="submit" className="login__btn" disabled={busy || !password}>
              {busy ? 'CHECKING…' : 'LOG IN'}
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
