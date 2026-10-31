// Typed client for the OnlyNerds backend (backend/docs/API_REFERENCE.md).
import type {
  AdvanceOut,
  AnswerIn,
  AttemptResultOut,
  AuthCheckOut,
  CourseSummary,
  CreateCourseIn,
  CreateCourseOut,
  DueItem,
  HealthResponse,
  MasteryOut,
  NewSessionResponse,
  ResetOut,
  ResourcesResponse,
  StartOut,
  StepOut,
  ValidationError,
} from './types'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

/** The app has one learner. */
export const LEARNER = 'me'

// Shared with the control panel (public/control.html) through localStorage.
const PASSWORD_KEY = 'onlynerds.password'
const COURSE_KEY = 'onlynerds.course'

function read(key: string): string {
  try {
    return localStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // Storage blocked: the value lasts only until reload.
  }
}

export const getPassword = () => read(PASSWORD_KEY)
export const setPassword = (password: string | null) => write(PASSWORD_KEY, password)
/** Tells the control panel which course to watch. */
export const setCurrentCourse = (courseId: string) => write(COURSE_KEY, courseId)

/** Fired on any 401 so the app can send the user to /login. */
export const UNAUTHORIZED_EVENT = 'onlynerds:unauthorized'

export class ApiError extends Error {
  status: number
  detail: string | ValidationError[]

  constructor(status: number, detail: string | ValidationError[]) {
    super(typeof detail === 'string' ? detail : detail.map((e) => e.msg).join('; '))
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init: RequestInit = {}, password = getPassword()): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', 'X-Master-Password': password, ...init.headers },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server.')
  }
  if (!res.ok) {
    let detail: string | ValidationError[] = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // Non-JSON error body: keep the status text.
    }
    if (res.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

const learner = (cid: string) => `/courses/${encodeURIComponent(cid)}/learners/${LEARNER}`

export const api = {
  health: () => request<HealthResponse>('/health'),
  /** Checks a candidate password without storing it. */
  authCheck: (password: string) => request<AuthCheckOut>('/auth/check', {}, password),

  listCourses: () => request<CourseSummary[]>(`/courses?learner_id=${LEARNER}`),
  due: () => request<DueItem[]>(`/due?learner_id=${LEARNER}`),
  createCourse: (body: CreateCourseIn) => post<CreateCourseOut>('/courses', body),
  getCourse: (cid: string) => request<CreateCourseOut>(`/courses/${encodeURIComponent(cid)}`),

  start: (cid: string) => post<StartOut>(`${learner(cid)}/start`),
  submitAttempts: (cid: string, answers: AnswerIn[]) =>
    post<AttemptResultOut>(`${learner(cid)}/attempts`, { answers }),
  next: (cid: string) => request<StepOut>(`${learner(cid)}/next`),
  state: (cid: string) => request<MasteryOut>(`${learner(cid)}/state`),
  resources: (cid: string) => request<ResourcesResponse>(`${learner(cid)}/resources`),
  newSession: (cid: string) => post<NewSessionResponse>(`${learner(cid)}/sessions/new`),
  reset: (cid: string) => post<ResetOut>(`${learner(cid)}/reset`),
  advance: (cid: string, days: number) => post<AdvanceOut>(`${learner(cid)}/advance`, { days }),
}

/** A short, user-facing message for any thrown error. */
export function errorText(err: unknown): string {
  if (err instanceof ApiError) return err.status === 0 ? err.message : `${err.message} (${err.status})`
  return err instanceof Error ? err.message : String(err)
}
