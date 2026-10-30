import type { ReactNode } from 'react'
import { Link } from 'react-router'
import logo from '../assets/logo.png'
import { useBuiltCourses, whenLabel } from '../data/courseStore'
import { previousChats, user } from '../data/placeholder'
import { Icon, type IconName } from './Icon'
import './AppShell.css'

export type NavKey = 'home' | 'courses' | 'retention'

const navItems: { key: NavKey; label: string; icon: IconName; to: string }[] = [
  { key: 'home', label: 'Home', icon: 'home', to: '/' },
  { key: 'courses', label: 'My courses', icon: 'book', to: '/chat' },
  { key: 'retention', label: 'Retention', icon: 'bars', to: '/retention' },
]

// Left navigation + content area shared by the signed-in screens.
export function AppShell({
  active,
  activeChatId,
  children,
}: {
  active?: NavKey
  activeChatId?: string
  children: ReactNode
}) {
  // Courses built in this browser come first, then the placeholder history.
  const built = useBuiltCourses()
  const chats = [
    ...built.map((c) => ({
      id: c.id,
      title: c.topic,
      meta: `${whenLabel(c.createdAt)} · ${c.assessed ? c.level : 'Assessment pending'}`,
    })),
    ...previousChats,
  ]
  // "My courses" has no screen of its own yet: it opens the latest course's tutor chat.
  const navTo = (item: (typeof navItems)[number]) => (item.key === 'courses' ? `/chat/${chats[0].id}` : item.to)

  return (
    <div className="shell">
      <div className="shell__frame">
        <aside className="sidenav">
          <Link to="/" className="sidenav__logo" aria-label="OnlyNerds home">
            <img src={logo} alt="OnlyNerds" />
          </Link>

          <nav aria-label="Primary" className="sidenav__nav">
            {navItems.map((item) => (
              <Link
                key={item.key}
                to={navTo(item)}
                className={`nav${item.key === active ? ' nav--active' : ''}`}
                aria-current={item.key === active ? 'page' : undefined}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            ))}
          </nav>

          <Link to="/new" className="btn btn-primary sidenav__new">
            <Icon name="plus" size={18} strokeWidth={2.2} />
            NEW CHAT
          </Link>

          <div className="sidenav__chats">
            <div className="label sidenav__chats-label">Previous chats</div>
            {chats.map((c) => (
              <Link
                key={c.id}
                to={`/chat/${c.id}`}
                className={`row-link sidenav__chat${c.id === activeChatId ? ' sidenav__chat--active' : ''}`}
                aria-current={c.id === activeChatId ? 'page' : undefined}
              >
                <span className="sidenav__chat-title">{c.title}</span>
                <span className="sidenav__chat-meta">{c.meta}</span>
              </Link>
            ))}
          </div>

          <div className="sidenav__footer">
            <a href="#" className="nav">
              <Icon name="settings" />
              Settings
            </a>
            <a href="#" className="row-link sidenav__profile" aria-label="My profile">
              <div className="av" style={{ width: 42, height: 42, fontSize: 14 }} aria-hidden="true">
                {user.initials}
              </div>
              <div className="sidenav__profile-text">
                <div className="sidenav__profile-name">{user.name}</div>
                <div className="sidenav__profile-sub">My profile</div>
              </div>
            </a>
          </div>
        </aside>

        {children}
      </div>
    </div>
  )
}
