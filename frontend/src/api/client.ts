// Typed client for the verified OnlyNerds backend routes (docs/API_REFERENCE.md).
import type {
  AdvanceOut,
  AnswerIn,
  AttemptResultOut,
  CreateCourseIn,
  CreateCourseOut,
  HealthResponse,
  MasteryOut,
  NewSessionResponse,
  StartOut,
  StepOut,
  ValidationError,
} from './types'

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

// Shared with the control panel window through localStorage.
const PASSWORD_KEY = 'onlynerds.password'

export function getPassword(): string {
  try {
    return localStorage.getItem(PASSWORD_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setPassword(password: string): void {
  try {
    localStorage.setItem(PASSWORD_KEY, password)
  } catch {
    // Storage blocked: the password lasts only until reload.
  }
}

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Master-Password': getPassword(),
      ...init.headers,
    },
  })
  if (!res.ok) {
    let detail: string | ValidationError[] = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // Non-JSON error body: keep the status text.
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

const learner = (cid: string, lid: string) =>
  `/courses/${encodeURIComponent(cid)}/learners/${encodeURIComponent(lid)}`

export const api = {
  health: () => request<HealthResponse>('/health'),

  createCourse: (body: CreateCourseIn) => post<CreateCourseOut>('/courses', body),
  getCourse: (cid: string) => request<CreateCourseOut>(`/courses/${encodeURIComponent(cid)}`),

  start: (cid: string, lid: string) => post<StartOut>(`${learner(cid, lid)}/start`),
  submitAttempts: (cid: string, lid: string, answers: AnswerIn[]) =>
    post<AttemptResultOut>(`${learner(cid, lid)}/attempts`, { answers }),
  next: (cid: string, lid: string) => request<StepOut>(`${learner(cid, lid)}/next`),
  state: (cid: string, lid: string) => request<MasteryOut>(`${learner(cid, lid)}/state`),
  advance: (cid: string, lid: string, days: number) =>
    post<AdvanceOut>(`${learner(cid, lid)}/advance`, { days }),
  newSession: (cid: string, lid: string) =>
    post<NewSessionResponse>(`${learner(cid, lid)}/sessions/new`),
}

// Backend datetimes are naive UTC strings without a trailing 'Z'.
export function parseUtc(s: string | null | undefined): Date | null {
  if (!s) return null
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : `${s}Z`)
}
