// Courses the learner built in this browser (placeholder until the backend is wired).
// Kept in localStorage so they survive reloads and show up in Previous chats.
import { useSyncExternalStore } from 'react'

export interface CourseConcept {
  id: string
  name: string
  prerequisites: string[]
}

export interface BuiltCourse {
  id: string
  topic: string
  /** Level name as shown, e.g. "Intermediate". */
  level: string
  concepts: CourseConcept[]
  createdAt: string
  /** The diagnostic has been taken; until then the chat asks for it. */
  assessed: boolean
  /** Diagnostic score in percent, once assessed. */
  score?: number
}

const KEY = 'onlynerds.courses'
const listeners = new Set<() => void>()
let courses: BuiltCourse[] = load()

function load(): BuiltCourse[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as BuiltCourse[]) : []
  } catch {
    return []
  }
}

function save(next: BuiltCourse[]) {
  courses = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Storage blocked: courses last until reload.
  }
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Newest first. */
export const useBuiltCourses = () => useSyncExternalStore(subscribe, () => courses)

export const useBuiltCourse = (id: string | undefined) =>
  useSyncExternalStore(subscribe, () => courses.find((c) => c.id === id))

/** Same topic (case and spacing ignored) and level, like the backend's course reuse. */
export function findCourse(topic: string, level: string) {
  const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ')
  return courses.find((c) => norm(c.topic) === norm(topic) && c.level === level)
}

export function addCourse(course: BuiltCourse) {
  save([course, ...courses.filter((c) => c.id !== course.id)])
}

export function updateCourse(id: string, patch: Partial<BuiltCourse>) {
  save(courses.map((c) => (c.id === id ? { ...c, ...patch } : c)))
}

/** Placeholder concept graph (8 concepts, each building on the one before). */
export function mockConcepts(topic: string): CourseConcept[] {
  const t = topic.trim()
  const names = [
    `What ${t} is`,
    'Core terms and ideas',
    'How the parts fit together',
    'A worked example, step by step',
    'Common mistakes and misconceptions',
    'Checking and measuring results',
    'Trade-offs and limits',
    'Putting it into practice',
  ]
  return names.map((name, i) => ({
    id: `c${i + 1}`,
    name,
    prerequisites: i === 0 ? [] : [`c${i}`],
  }))
}

export const newCourseId = () => `course-${Date.now().toString(36)}`

/** "Now", "Today" or a short date, for the Previous chats list. */
export function whenLabel(iso: string) {
  const d = new Date(iso)
  const mins = (Date.now() - d.getTime()) / 60000
  if (mins < 60) return 'Now'
  if (d.toDateString() === new Date().toDateString()) return 'Today'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
