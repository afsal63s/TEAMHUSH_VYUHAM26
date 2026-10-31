// Display helpers for API values.
import { levels } from '../data/placeholder'
import type { CreateCourseOut } from './types'

/** Backend datetimes are naive UTC strings without a trailing 'Z'. */
export function parseUtc(s: string | null | undefined): Date | null {
  if (!s) return null
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`)
  return Number.isNaN(d.getTime()) ? null : d
}

/** 0..1 -> "72%"; "—" for missing values. */
export const pct = (x: number | null | undefined) => (x == null || Number.isNaN(x) ? '—' : `${Math.round(x * 100)}%`)

export const levelName = (key: string | null | undefined) =>
  levels.find((l) => l.key === key)?.name ?? (key ? key[0].toUpperCase() + key.slice(1) : '')

/** Same rule as the assessment results: a percent (0..100) to a level word. */
export const levelFromPct = (p: number) => (p >= 85 ? 'Advanced' : p >= 65 ? 'Intermediate' : p >= 40 ? 'Beginner' : 'Novice')

const DAY = 24 * 60 * 60 * 1000
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()

/** "12 min ago", "3 h ago", "Yesterday", "Oct 26". */
export function ago(s: string | null | undefined, now = new Date()): string {
  const d = parseUtc(s)
  if (!d) return ''
  const mins = Math.round((now.getTime() - d.getTime()) / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins} min ago`
  if (mins < 24 * 60 && startOfDay(d) === startOfDay(now)) return `${Math.round(mins / 60)} h ago`
  if (startOfDay(now) - startOfDay(d) === DAY) return 'Yesterday'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/** Calendar-day distance: "Today", "Tomorrow", "In 3 days", "2 days ago". */
export function dayDistance(s: string | null | undefined, now = new Date()): string {
  const d = parseUtc(s)
  if (!d) return '—'
  const days = Math.round((startOfDay(d) - startOfDay(now)) / DAY)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  return days > 0 ? `In ${days} days` : `${-days} days ago`
}

export const monthDay = (d: Date) => ({
  month: d.toLocaleDateString(undefined, { month: 'short' }).toUpperCase(),
  day: String(d.getDate()),
})

/** "youtube.com" from a URL. */
export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export interface Concept {
  id: string
  name: string
  prerequisites: string[]
}

/** The course's concept graph (typed loosely in the schema). */
export function conceptsOf(course: CreateCourseOut | null | undefined): Concept[] {
  return ((course?.concepts ?? []) as Partial<Concept>[]).map((c) => ({
    id: String(c.id ?? ''),
    name: String(c.name ?? c.id ?? ''),
    prerequisites: Array.isArray(c.prerequisites) ? c.prerequisites.map(String) : [],
  }))
}

/** concept_id -> display name, falling back to the id. */
export const nameMap = (course: CreateCourseOut | null | undefined) => {
  const m = new Map(conceptsOf(course).map((c) => [c.id, c.name]))
  return (id: string | null | undefined) => (id ? (m.get(id) ?? id) : '')
}

export const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)
