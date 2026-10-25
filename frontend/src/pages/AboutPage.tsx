import { COVERED_AGE_RANGE_LABEL } from '../types'

export function AboutPage() {
  return (
    <div className="card about-card">
      <h2>👣 About LittleSteps</h2>

      <p>
        <strong>LittleSteps</strong> is a screening aid for parents and caregivers of children.
        It walks you through a short, friendly check-in about things your child is doing (or not
        doing yet) for their age, and gives you a plain-English read on how things are going —
        plus a few simple things to try at home.
      </p>

      <p className="age-coverage-note">
        <strong>Right now, the check-in covers ages {COVERED_AGE_RANGE_LABEL}</strong> — that's the
        actual range of the CDC milestone data behind it today (see <strong>Sources</strong>). Our
        long-term goal is to support ages 0–18, but we only turn on a check-in once we have real,
        properly licensed data for it — see Sources for what's used now versus what's still being
        worked on.
      </p>

      <h3>What it is</h3>
      <ul>
        <li>A way to notice possible developmental red flags early, based on real, published milestone checklists (see our <strong>Sources</strong> page).</li>
        <li>A way to track one or more children over time, not just a single one-off check — so you can see trends, not just a snapshot.</li>
        <li>Written for parents, not clinicians: plain language, no jargon, kind and honest.</li>
      </ul>

      <h3>What it is not</h3>
      <ul>
        <li>
          <strong>LittleSteps is not a diagnosis.</strong> It never tells you your child "has" a
          condition. If something is worth a closer look, we'll say so clearly and point you
          toward your child's doctor — only a doctor can diagnose.
        </li>
        <li>It's not a replacement for regular well-child visits or professional developmental screening.</li>
      </ul>

      <h3>How it works</h3>
      <p>
        You answer a few simple questions for your child's age (Yes / Sometimes / Not yet / Not
        sure). We group the result into one of three bands — <em>Doing well</em>,{' '}
        <em>Worth watching</em>, or <em>Talk to your doctor soon</em> — along with 1–3 things to
        try at home and one clear next step. If your child was born early, we use their{' '}
        <em>corrected age</em> instead of their birth-date age, the same way pediatricians do.
      </p>

      <h3>Your privacy</h3>
      <p>
        Your account is protected with a securely hashed password, and your family's information
        is only ever visible to you, through your own login. We do use anonymous, aggregate data
        (never anything that identifies you or your child) to see how the app is doing overall and
        make it better over time.
      </p>

      <p className="disclaimer">
        This is a screening aid, not a medical diagnosis. If you ever have a concern about your
        child, trust that instinct and talk to your child's doctor.
      </p>
    </div>
  )
}
