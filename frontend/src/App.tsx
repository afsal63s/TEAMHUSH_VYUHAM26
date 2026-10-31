import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router'
import { getPassword, setPassword, UNAUTHORIZED_EVENT } from './api/client'
import { Assessment } from './screens/assessment/Assessment'
import { BuildCourse } from './screens/build/BuildCourse'
import { HomeFeed } from './screens/home/HomeFeed'
import { Login } from './screens/login/Login'
import { NewChat } from './screens/newchat/NewChat'
import { Retention } from './screens/retention/Retention'
import { TutorChat } from './screens/tutor/TutorChat'

/** Screens behind the password: none saved -> /login. */
function RequireAuth({ children }: { children: ReactNode }) {
  return getPassword() ? children : <Navigate to="/login" replace />
}

/** Any 401 from the API forgets the password and goes to /login. */
function UnauthorizedRedirect() {
  const navigate = useNavigate()
  const location = useLocation()
  useEffect(() => {
    const onUnauthorized = () => {
      if (location.pathname === '/login') return
      setPassword(null)
      navigate('/login', { replace: true })
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [navigate, location.pathname])
  return null
}

const guarded = (el: ReactNode) => <RequireAuth>{el}</RequireAuth>

function App() {
  return (
    <BrowserRouter>
      <UnauthorizedRedirect />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={guarded(<HomeFeed />)} />
        <Route path="/new" element={guarded(<NewChat />)} />
        <Route path="/build" element={guarded(<BuildCourse />)} />
        <Route path="/assessment" element={guarded(<Assessment />)} />
        <Route path="/chat/:chatId" element={guarded(<TutorChat />)} />
        <Route path="/retention" element={guarded(<Retention />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
