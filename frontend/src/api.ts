import { getToken } from './auth'
import type {
  AgeEntry,
  Child,
  CorrectedAgeResult,
  MilestoneAnswer,
  ScreeningRecord,
  ScreenResponse,
  User,
} from './types'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function getAges(): Promise<string[]> {
  return request('/api/ages')
}

export function getMilestones(ageLabel: string): Promise<AgeEntry> {
  return request(`/api/milestones/${encodeURIComponent(ageLabel)}`)
}

export function getCorrectedAge(
  dateOfBirth: string,
  gestationalAgeWeeks: number,
): Promise<CorrectedAgeResult> {
  return request('/api/corrected-age', {
    method: 'POST',
    body: JSON.stringify({
      date_of_birth: dateOfBirth,
      gestational_age_weeks: gestationalAgeWeeks,
    }),
  })
}

export function signup(email: string, password: string): Promise<{ access_token: string }> {
  return request('/api/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export function login(email: string, password: string): Promise<{ access_token: string }> {
  return request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export function getMe(): Promise<User> {
  return request('/api/auth/me')
}

export function createChild(
  nickname: string,
  dateOfBirth: string,
  gestationalAgeWeeks: number | null,
): Promise<Child> {
  return request('/api/children', {
    method: 'POST',
    body: JSON.stringify({
      nickname,
      date_of_birth: dateOfBirth,
      gestational_age_weeks: gestationalAgeWeeks,
    }),
  })
}

export function listChildren(): Promise<Child[]> {
  return request('/api/children')
}

export function submitScreeningForChild(
  childId: number,
  ageLabel: string,
  correctedAgeMonths: number | null,
  answers: MilestoneAnswer[],
): Promise<ScreenResponse> {
  return request(`/api/children/${childId}/screenings`, {
    method: 'POST',
    body: JSON.stringify({ age_label: ageLabel, corrected_age_months: correctedAgeMonths, answers }),
  })
}

export function getScreeningHistory(childId: number): Promise<ScreeningRecord[]> {
  return request(`/api/children/${childId}/screenings`)
}
