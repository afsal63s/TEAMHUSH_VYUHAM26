// Small data hooks: loading/error state, shared caches, and the control-panel signal.
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { api, errorText } from './client'
import type { CourseSummary, CreateCourseOut } from './types'

export interface Async<T> {
  data: T | undefined
  error: string | null
  loading: boolean
  reload: () => void
}

/**
 * Runs `fn` on mount and whenever `deps` change; ignores results from stale runs.
 * `loading` is true until a result for the current deps arrives (the previous `data` stays visible).
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): Async<T> {
  const [tick, setTick] = useState(0)
  const key = [...deps, tick].map(String).join('|')
  const [result, setResult] = useState<{ key: string; data?: T; error: string | null } | null>(null)
  const run = useRef(0)

  useEffect(() => {
    const id = ++run.current
    fn().then(
      (data) => {
        if (id === run.current) setResult({ key, data, error: null })
      },
      (e) => {
        if (id === run.current) setResult((r) => ({ key, data: r?.data, error: errorText(e) }))
      },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const current = result?.key === key
  return {
    data: result?.data,
    error: current ? result.error : null,
    loading: !current,
    reload,
  }
}

// ---- Shared course list (sidebar, Home, Retention) ----

interface Snapshot {
  courses: CourseSummary[] | undefined
  error: string | null
}
let snapshot: Snapshot = { courses: undefined, error: null }
let inflight: Promise<void> | null = null
const listeners = new Set<() => void>()

/** Re-fetches the course list; every useCourses() subscriber updates. */
export function refreshCourses(): Promise<void> {
  inflight ??= api
    .listCourses()
    .then(
      (courses) => {
        snapshot = { courses, error: null }
      },
      (e) => {
        snapshot = { ...snapshot, error: errorText(e) }
      },
    )
    .finally(() => {
      inflight = null
      listeners.forEach((l) => l())
    })
  return inflight
}

export function useCourses() {
  const snap = useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => snapshot,
  )
  useEffect(() => {
    void refreshCourses()
  }, [])
  return { ...snap, loading: snap.courses === undefined && !snap.error, reload: refreshCourses }
}

// ---- Course graphs (concept names), cached per course ----

const courseCache = new Map<string, Promise<CreateCourseOut>>()

/** GET /courses/{id}, cached once the course is ready. */
export function getCourseCached(cid: string): Promise<CreateCourseOut> {
  const hit = courseCache.get(cid)
  if (hit) return hit
  const p = api.getCourse(cid).then((c) => {
    if (c.status !== 'ready') courseCache.delete(cid)
    return c
  })
  p.catch(() => courseCache.delete(cid))
  courseCache.set(cid, p)
  return p
}

export const useCourse = (cid: string | undefined) =>
  useAsync(() => (cid ? getCourseCached(cid) : Promise.resolve(undefined)), [cid])

// ---- Control panel (public/control.html) ----

/** Calls `onSignal` when the control panel jumps the clock, starts a session or resets. */
export function useControlPanelSignal(onSignal: (type: string) => void) {
  const cb = useRef(onSignal)
  useEffect(() => {
    cb.current = onSignal
  })
  useEffect(() => {
    let chan: BroadcastChannel | null = null
    try {
      chan = new BroadcastChannel('onlynerds')
      chan.onmessage = (e) => cb.current(String((e.data as { type?: string } | null)?.type ?? ''))
    } catch {
      // BroadcastChannel unavailable: the app just won't auto-refresh.
    }
    return () => chan?.close()
  }, [])
}
