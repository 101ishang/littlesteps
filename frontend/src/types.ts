export type Answer = 'yes' | 'sometimes' | 'not_yet' | 'not_sure'

export interface MilestoneItem {
  id: string
  text: string
  source: string
}

export interface AgeEntry {
  age_label: string
  age_months_min: number
  age_months_max: number
  domains: Record<string, MilestoneItem[]>
}

export interface MilestoneAnswer {
  milestone_id: string
  domain: string
  text: string
  answer: Answer
  regression: boolean
}

export type Band = 'doing_well' | 'worth_watching' | 'talk_to_doctor_soon'

export interface ScreeningResult {
  band: Band
  band_label: string
  flagged: MilestoneAnswer[]
  regression_detected: boolean
  home_tips: string[]
  next_step: string
  disclaimer: string
}

export interface AIExplanation {
  summary: string
  encouragement: string
  used_fallback: boolean
  safety_passed: boolean | null
}

export interface ScreenResponse {
  result: ScreeningResult
  ai: AIExplanation
}

export interface CorrectedAgeResult {
  chronological_age_days: number
  chronological_age_months: number
  is_premature: boolean
  weeks_premature: number
  correction_applies: boolean
  corrected_age_days: number
  corrected_age_months: number
}

export interface User {
  id: number
  email: string
  created_at: string
}

export interface Child {
  id: number
  nickname: string
  date_of_birth: string
  gestational_age_weeks: number | null
}

export interface ScreeningRecord {
  id: number
  created_at: string
  age_label: string
  corrected_age_months: number | null
  band: Band
  regression_detected: boolean
  flagged_count: number
  ai_summary: string | null
  ai_encouragement: string | null
  ai_used_fallback: boolean
}

export const DOMAIN_LABELS: Record<string, string> = {
  social_emotional: 'Social / Emotional',
  language_communication: 'Language / Communication',
  cognitive: 'Thinking & Problem-Solving',
  movement_physical: 'Movement / Physical',
}

// Mirrors the age_label -> age_months_min values in data/milestones.json,
// used client-side to find the closest screening bracket for a computed
// (corrected) age without an extra round trip per age.
export const AGE_LABEL_MONTHS: Record<string, number> = {
  '2 months': 2,
  '4 months': 4,
  '6 months': 6,
  '9 months': 9,
  '1 year': 12,
  '15 months': 15,
  '18 months': 18,
  '2 years': 24,
  '30 months': 30,
  '3 years': 36,
  '4 years': 48,
  '5 years': 60,
}

export function closestAgeLabel(ageMonths: number): string {
  let best = '2 months'
  let bestDiff = Infinity
  for (const [label, months] of Object.entries(AGE_LABEL_MONTHS)) {
    const diff = Math.abs(months - ageMonths)
    if (diff < bestDiff) {
      bestDiff = diff
      best = label
    }
  }
  return best
}

// The actual, sourced range of CDC "Learn the Signs. Act Early." milestone data
// this app runs on (see data/milestones.json) — derived from AGE_LABEL_MONTHS
// above, not a separately-stated claim, so it can't drift out of sync with the
// real data. Used to tell parents what LittleSteps is (and isn't) built for yet,
// and to avoid quietly screening a child against the nearest bracket when their
// actual age is well outside what the data covers.
const COVERED_MONTHS = Object.values(AGE_LABEL_MONTHS)
export const MIN_COVERED_AGE_MONTHS = Math.min(...COVERED_MONTHS)
export const MAX_COVERED_AGE_MONTHS = Math.max(...COVERED_MONTHS)
const MIN_LABEL = Object.entries(AGE_LABEL_MONTHS).find(([, m]) => m === MIN_COVERED_AGE_MONTHS)![0]
const MAX_LABEL = Object.entries(AGE_LABEL_MONTHS).find(([, m]) => m === MAX_COVERED_AGE_MONTHS)![0]
export const COVERED_AGE_RANGE_LABEL = `${MIN_LABEL} to ${MAX_LABEL}`

export function isWithinCoveredAgeRange(ageMonths: number): boolean {
  return ageMonths >= MIN_COVERED_AGE_MONTHS && ageMonths <= MAX_COVERED_AGE_MONTHS
}

export const ANSWER_OPTIONS: { value: Answer; label: string }[] = [
  { value: 'yes', label: 'Yes' },
  { value: 'sometimes', label: 'Sometimes' },
  { value: 'not_yet', label: 'Not yet' },
  { value: 'not_sure', label: 'Not sure' },
]

export const BAND_INFO: Record<Band, { icon: string; className: string; label: string }> = {
  doing_well: { icon: '✅', className: 'band-doing-well', label: 'Doing well' },
  worth_watching: { icon: '🟡', className: 'band-worth-watching', label: 'Worth watching' },
  talk_to_doctor_soon: { icon: '❗', className: 'band-talk-to-doctor', label: 'Talk to your doctor soon' },
}
