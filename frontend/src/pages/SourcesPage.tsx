import { COVERED_AGE_RANGE_LABEL } from '../types'

interface Source {
  name: string
  publisher: string
  url: string
  note: string
}

const USED_SOURCES: Source[] = [
  {
    name: 'CDC "Learn the Signs. Act Early." (LTSAE) milestone checklists',
    publisher: 'U.S. Centers for Disease Control and Prevention',
    url: 'https://www.cdc.gov/act-early/milestones/',
    note: 'Milestone questions for ages 2 months through 5 years, across Social/Emotional, Language/Communication, Cognitive, and Movement/Physical domains.',
  },
  {
    name: 'CDC growth charts',
    publisher: 'U.S. Centers for Disease Control and Prevention / National Center for Health Statistics',
    url: 'https://www.cdc.gov/growthcharts/',
    note: 'Official percentile data for weight, height/stature, head circumference, and BMI, ages 2–20 years (and birth–36 months).',
  },
  {
    name: 'WHO child growth standards',
    publisher: 'World Health Organization (hosted via CDC)',
    url: 'https://www.cdc.gov/growthcharts/who-data-files.htm',
    note: 'Official percentile data for weight, length, head circumference, and weight-for-length, birth–24 months — used for this age range per CDC/AAP guidance.',
  },
]

const PLANNED_SOURCES: Source[] = [
  {
    name: 'Vision milestones',
    publisher: 'Prevent Blindness — National Center for Children’s Vision and Eye Health',
    url: 'https://nationalcenter.preventblindness.org/',
    note: 'A real, expert-reviewed checklist exists, but it’s copyrighted — we’re seeking permission before adding it.',
  },
  {
    name: 'Hearing milestones',
    publisher: 'State Early Hearing Detection & Intervention (EHDI) programs',
    url: 'https://www.cdc.gov/ehdi/',
    note: 'Pending confirmation of reuse terms before we add this content.',
  },
  {
    name: 'PHQ-A, PSC-17, and Vanderbilt behavior/mental-health screens',
    publisher: 'Multiple developers (Pfizer-funded PHQ family, Massachusetts General Hospital, NICHQ/AAP)',
    url: 'https://www.phqscreeners.com/',
    note: 'For school-age and adolescent behavior screening. Licensing and the exact validated item sets are still being confirmed before anything is added.',
  },
]

function SourceCard({ source }: { source: Source }) {
  return (
    <li className="source-card">
      <h4>{source.name}</h4>
      <p className="source-publisher">{source.publisher}</p>
      <p>{source.note}</p>
      <a href={source.url} target="_blank" rel="noreferrer">
        {source.url}
      </a>
    </li>
  )
}

export function SourcesPage() {
  return (
    <div className="card sources-card">
      <h2>📚 Sources</h2>
      <p>
        LittleSteps doesn't make up milestones or growth data — every question and chart comes
        from a real, published source, cited below. Where we haven't been able to confirm we can
        use a source yet (usually a licensing question), we say so rather than guess. That's also
        why the check-in only runs for ages <strong>{COVERED_AGE_RANGE_LABEL}</strong> today: it's
        exactly the range the sources below actually cover.
      </p>

      <h3>Currently used</h3>
      <ul className="source-list">
        {USED_SOURCES.map((s) => (
          <SourceCard key={s.name} source={s} />
        ))}
      </ul>

      <h3>Planned, pending permission or licensing</h3>
      <ul className="source-list">
        {PLANNED_SOURCES.map((s) => (
          <SourceCard key={s.name} source={s} />
        ))}
      </ul>

      <p className="disclaimer">
        These checklists are screening tools, not a substitute for standardized, validated
        developmental screening administered by a professional (e.g. ASQ-3, M-CHAT-R/F).
      </p>
    </div>
  )
}
