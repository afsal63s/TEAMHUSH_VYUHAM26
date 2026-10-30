import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { Assessment } from './screens/assessment/Assessment'
import { BuildCourse } from './screens/build/BuildCourse'
import { HomeFeed } from './screens/home/HomeFeed'
import { NewChat } from './screens/newchat/NewChat'
import { Retention } from './screens/retention/Retention'
import { TutorChat } from './screens/tutor/TutorChat'

// The app opens on the Home feed. Login (screens/login) is built but not routed yet.
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomeFeed />} />
        <Route path="/new" element={<NewChat />} />
        <Route path="/build" element={<BuildCourse />} />
        <Route path="/assessment" element={<Assessment />} />
        <Route path="/chat/:chatId" element={<TutorChat />} />
        <Route path="/retention" element={<Retention />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
