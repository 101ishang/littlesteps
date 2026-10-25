import { useEffect, useState } from 'react'
import './App.css'
import {
  createChild,
  getCorrectedAge,
  getMe,
  getMilestones,
  getScreeningHistory,
  listChildren,
  login,
  signup,
  submitScreeningForChild,
} from './api'
import { clearToken, getToken, setToken } from './auth'
import { BackgroundShapes } from './components/Shapes'
import { NavBar, type Page } from './components/NavBar'
import { AboutPage } from './pages/AboutPage'
import { SourcesPage } from './pages/SourcesPage'
import {
  ANSWER_OPTIONS,
  BAND_INFO,
  closestAgeLabel,
  COVERED_AGE_RANGE_LABEL,
  DOMAIN_LABELS,
  isWithinCoveredAgeRange,
  type AgeEntry,
  type Answer,
  type Child,
  type CorrectedAgeResult,
  type MilestoneAnswer,
  type ScreeningRecord,
  type AIExplanation,
  type ScreeningResult,
  type User,
} from './types'

type Step = 'loading' | 'auth' | 'children' | 'questionnaire' | 'results' | 'history'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function App() {
  const [page, setPage] = useState<Page>('app')
  const [step, setStep] = useState<Step>('loading')
  const [user, setUser] = useState<User | null>(null)
  const [children, setChildren] = useState<Child[]>([])
  const [selectedChild, setSelectedChild] = useState<Child | null>(null)
  const [globalError, setGlobalError] = useState('')
  const [ageRangeNotice, setAgeRangeNotice] = useState<{ childName: string; months: number } | null>(
    null,
  )

  // Auth form
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authError, setAuthError] = useState('')

  // Add-child form
  const [newChildName, setNewChildName] = useState('')
  const [newChildDob, setNewChildDob] = useState('')
  const [newChildPremature, setNewChildPremature] = useState(false)
  const [newChildWeeks, setNewChildWeeks] = useState(40)
  const [addChildError, setAddChildError] = useState('')

  // Questionnaire
  const [correctedAge, setCorrectedAge] = useState<CorrectedAgeResult | null>(null)
  const [ageEntry, setAgeEntry] = useState<AgeEntry | null>(null)
  const [answers, setAnswers] = useState<Record<string, Answer>>({})
  const [regressionChecked, setRegressionChecked] = useState(false)

  // Results / history
  const [result, setResult] = useState<ScreeningResult | null>(null)
  const [aiExplanation, setAiExplanation] = useState<AIExplanation | null>(null)
  const [history, setHistory] = useState<ScreeningRecord[]>([])

  useEffect(() => {
    if (!getToken()) {
      setStep('auth')
      return
    }
    getMe()
      .then((u) => {
        setUser(u)
        return refreshChildren()
      })
      .then(() => setStep('children'))
      .catch(() => {
        clearToken()
        setStep('auth')
      })
  }, [])

  async function refreshChildren() {
    const list = await listChildren()
    setChildren(list)
  }

  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault()
    setAuthError('')
    try {
      const { access_token } =
        authMode === 'login' ? await login(authEmail, authPassword) : await signup(authEmail, authPassword)
      setToken(access_token)
      const u = await getMe()
      setUser(u)
      await refreshChildren()
      setAuthEmail('')
      setAuthPassword('')
      setStep('children')
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  function handleLogout() {
    clearToken()
    setUser(null)
    setChildren([])
    setSelectedChild(null)
    setAuthMode('login')
    setStep('auth')
  }

  async function handleAddChild(e: React.FormEvent) {
    e.preventDefault()
    setAddChildError('')
    try {
      await createChild(newChildName, newChildDob, newChildPremature ? newChildWeeks : null)
      setNewChildName('')
      setNewChildDob('')
      setNewChildPremature(false)
      setNewChildWeeks(40)
      await refreshChildren()
    } catch (err) {
      setAddChildError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  async function startCheckIn(child: Child) {
    setGlobalError('')
    setAgeRangeNotice(null)
    try {
      setSelectedChild(child)
      const corrected = await getCorrectedAge(child.date_of_birth, child.gestational_age_weeks ?? 40)
      setCorrectedAge(corrected)

      if (!isWithinCoveredAgeRange(corrected.corrected_age_months)) {
        // Hard rule 3 (Agents.md): never apply milestone data outside what it
        // actually covers. The nearest bracket would still "work" technically,
        // but it wouldn't be a true read on a child this far outside the
        // sourced age range, so we say that plainly instead of guessing.
        setAgeRangeNotice({ childName: child.nickname, months: corrected.corrected_age_months })
        return
      }

      const ageLabel = closestAgeLabel(corrected.corrected_age_months)
      const entry = await getMilestones(ageLabel)
      setAgeEntry(entry)
      setAnswers({})
      setRegressionChecked(false)
      setStep('questionnaire')
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  async function viewHistory(child: Child) {
    setGlobalError('')
    try {
      setSelectedChild(child)
      const records = await getScreeningHistory(child.id)
      setHistory(records)
      setStep('history')
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  function setAnswer(milestoneId: string, answer: Answer) {
    setAnswers((prev) => ({ ...prev, [milestoneId]: answer }))
  }

  const allMilestones = ageEntry
    ? Object.entries(ageEntry.domains).flatMap(([domain, items]) =>
        items.map((item) => ({ ...item, domain })),
      )
    : []
  const allAnswered = allMilestones.length > 0 && allMilestones.every((m) => answers[m.id])

  async function handleQuestionnaireSubmit() {
    if (!selectedChild || !ageEntry) return
    const milestoneAnswers: MilestoneAnswer[] = allMilestones.map((m, i) => ({
      milestone_id: m.id,
      domain: m.domain,
      text: m.text,
      answer: answers[m.id],
      regression: regressionChecked && i === 0,
    }))
    const res = await submitScreeningForChild(
      selectedChild.id,
      ageEntry.age_label,
      correctedAge?.corrected_age_months ?? null,
      milestoneAnswers,
    )
    setResult(res.result)
    setAiExplanation(res.ai)
    setStep('results')
  }

  function backToChildren() {
    setStep('children')
    setSelectedChild(null)
    setAgeEntry(null)
    setResult(null)
    setAiExplanation(null)
    setAgeRangeNotice(null)
    refreshChildren()
  }

  return (
    <div className="app">
      <BackgroundShapes />
      <header className="app-header">
        <h1>
          <span className="logo-emoji" aria-hidden="true">
            👣
          </span>{' '}
          LittleSteps
        </h1>
        <p className="tagline">A friendly developmental check-in for parents. Not a diagnosis.</p>
        <NavBar page={page} onNavigate={setPage} />
        {user && page === 'app' && (
          <div className="user-bar">
            Signed in as {user.email}
            <button className="link-button" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        {page === 'about' && <AboutPage />}
        {page === 'sources' && <SourcesPage />}

        {page === 'app' && (
          <>
        {globalError && <p className="error card">{globalError}</p>}

        {step === 'loading' && <p className="hint">Loading…</p>}

        {step === 'auth' && (
          <form className="card" onSubmit={handleAuthSubmit}>
            <h2>{authMode === 'login' ? 'Log in' : 'Create an account'}</h2>
            <label>
              Email
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                required
                minLength={8}
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
              />
            </label>
            {authError && <p className="error">{authError}</p>}
            <button type="submit" className="primary-button">
              {authMode === 'login' ? 'Log in' : 'Sign up'}
            </button>
            <button
              type="button"
              className="link-button centered"
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'signup' : 'login')
                setAuthError('')
              }}
            >
              {authMode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Log in'}
            </button>
          </form>
        )}

        {step === 'children' && (
          <div className="card">
            <h2>Your children</h2>
            <p className="age-coverage-note">
              LittleSteps' check-in is currently built for children{' '}
              <strong>{COVERED_AGE_RANGE_LABEL}</strong>, based on the CDC milestone data we use
              today (see <button className="link-button inline" onClick={() => setPage('sources')}>Sources</button>). We're
              working on extending coverage to more ages.
            </p>
            {ageRangeNotice && (
              <p className="notice">
                {ageRangeNotice.childName} is about {Math.round(ageRangeNotice.months)} month(s)
                old, which is outside the {COVERED_AGE_RANGE_LABEL} range our current milestone
                data covers. To keep results meaningful, we're not running a check-in for this age
                yet — if you have any concerns, your child's doctor is still the best next step.
              </p>
            )}
            {children.length === 0 && <p className="hint">Add a child to get started.</p>}
            <ul className="child-list">
              {children.map((child) => (
                <li key={child.id} className="child-row">
                  <div>
                    <strong>{child.nickname}</strong>
                    <span className="child-dob"> · born {child.date_of_birth}</span>
                  </div>
                  <div className="child-actions">
                    <button className="primary-button small" onClick={() => startCheckIn(child)}>
                      Start check-in
                    </button>
                    <button className="secondary-button small" onClick={() => viewHistory(child)}>
                      View history
                    </button>
                  </div>
                </li>
              ))}
            </ul>

            <h3>Add a child</h3>
            <form onSubmit={handleAddChild}>
              <label>
                First name or nickname
                <input
                  type="text"
                  required
                  value={newChildName}
                  onChange={(e) => setNewChildName(e.target.value)}
                />
              </label>
              <label>
                Date of birth
                <input
                  type="date"
                  required
                  max={todayIso()}
                  value={newChildDob}
                  onChange={(e) => setNewChildDob(e.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={newChildPremature}
                  onChange={(e) => setNewChildPremature(e.target.checked)}
                />
                Born before 37 weeks (premature)
              </label>
              {newChildPremature && (
                <label>
                  Weeks of pregnancy at birth
                  <input
                    type="number"
                    min={20}
                    max={44}
                    value={newChildWeeks}
                    onChange={(e) => setNewChildWeeks(Number(e.target.value))}
                  />
                </label>
              )}
              {addChildError && <p className="error">{addChildError}</p>}
              <button type="submit" className="primary-button">
                Add child
              </button>
            </form>
          </div>
        )}

        {step === 'questionnaire' && ageEntry && selectedChild && (
          <div className="card">
            <h2>Milestones for {ageEntry.age_label}</h2>
            {correctedAge?.correction_applies && (
              <p className="corrected-age-note">
                Using corrected age ({correctedAge.corrected_age_months} months) because{' '}
                {selectedChild.nickname} was born {correctedAge.weeks_premature} weeks early.
              </p>
            )}
            <p className="instructions">
              For each item, choose the answer that best describes {selectedChild.nickname}.
            </p>

            {Object.entries(ageEntry.domains).map(([domain, items]) => (
              <section key={domain} className="domain-section">
                <h3>{DOMAIN_LABELS[domain] ?? domain}</h3>
                {items.map((item) => (
                  <fieldset key={item.id} className="milestone-item">
                    <legend>{item.text}</legend>
                    <div className="answer-options">
                      {ANSWER_OPTIONS.map((opt) => (
                        <label key={opt.value} className="answer-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={opt.value}
                            checked={answers[item.id] === opt.value}
                            onChange={() => setAnswer(item.id, opt.value)}
                          />
                          {opt.label}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ))}
              </section>
            ))}

            <label className="checkbox-label regression-check">
              <input
                type="checkbox"
                checked={regressionChecked}
                onChange={(e) => setRegressionChecked(e.target.checked)}
              />
              {selectedChild.nickname} used to be able to do something on this list and has stopped
            </label>

            <button
              className="primary-button"
              disabled={!allAnswered}
              onClick={handleQuestionnaireSubmit}
            >
              See results
            </button>
            {!allAnswered && <p className="hint">Please answer every item above.</p>}
            <button className="link-button centered" onClick={backToChildren}>
              Cancel
            </button>
          </div>
        )}

        {step === 'results' && result && selectedChild && (
          <div className="card">
            <div className={`band-banner ${BAND_INFO[result.band].className}`}>
              <span className="band-icon" aria-hidden="true">
                {BAND_INFO[result.band].icon}
              </span>
              <span className="band-label">{result.band_label}</span>
            </div>

            {aiExplanation && (
              <section className="ai-explanation">
                <h3>In plain terms</h3>
                <p>{aiExplanation.summary}</p>
                <p className="ai-encouragement">{aiExplanation.encouragement}</p>
                {aiExplanation.used_fallback && (
                  <p className="hint">
                    (Showing a standard note here instead of an AI-written one, to be safe.)
                  </p>
                )}
              </section>
            )}

            {result.flagged.length > 0 && (
              <section>
                <h3>Worth a closer look</h3>
                <ul>
                  {result.flagged.map((f) => (
                    <li key={f.milestone_id}>{f.text}</li>
                  ))}
                </ul>
              </section>
            )}

            <section>
              <h3>Things to try at home</h3>
              <ul>
                {result.home_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </section>

            <section>
              <h3>Next step</h3>
              <p>{result.next_step}</p>
            </section>

            <p className="disclaimer">{result.disclaimer}</p>

            <button className="primary-button" onClick={() => viewHistory(selectedChild)}>
              View {selectedChild.nickname}'s history
            </button>
            <button className="link-button centered" onClick={backToChildren}>
              Back to children
            </button>
          </div>
        )}

        {step === 'history' && selectedChild && (
          <div className="card">
            <h2>{selectedChild.nickname}'s check-in history</h2>
            {history.length === 0 && <p className="hint">No check-ins yet.</p>}
            <ul className="history-list">
              {history.map((h) => (
                <li key={h.id} className={`history-row ${BAND_INFO[h.band].className}`}>
                  <span className="band-icon" aria-hidden="true">
                    {BAND_INFO[h.band].icon}
                  </span>
                  <span>
                    <strong>{BAND_INFO[h.band].label}</strong> — {h.age_label} ·{' '}
                    {new Date(h.created_at).toLocaleDateString()}
                    {h.flagged_count > 0 && ` · ${h.flagged_count} item(s) flagged`}
                  </span>
                </li>
              ))}
            </ul>
            <button className="primary-button" onClick={() => startCheckIn(selectedChild)}>
              New check-in
            </button>
            <button className="link-button centered" onClick={backToChildren}>
              Back to children
            </button>
          </div>
        )}
          </>
        )}
      </main>
    </div>
  )
}
