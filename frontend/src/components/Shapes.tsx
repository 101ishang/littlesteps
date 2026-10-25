// Purely decorative background shapes (stars, circles) built with inline SVG,
// per Agents.md -> Images ("prefer HTML/CSS... whenever viable"). aria-hidden
// since they carry no information — see Agents.md -> Styling for the palette.

function Star({ className }: { className: string }) {
  return (
    <svg className={`deco-shape ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 1.5l2.95 6.62 7.2.72-5.46 4.83 1.62 7.08L12 16.9l-6.31 3.85 1.62-7.08-5.46-4.83 7.2-.72z"
      />
    </svg>
  )
}

function Circle({ className }: { className: string }) {
  return (
    <svg className={`deco-shape ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="11" fill="currentColor" />
    </svg>
  )
}

/** A fixed, full-viewport layer of soft background shapes. Place once per page. */
export function BackgroundShapes() {
  return (
    <div className="deco-layer" aria-hidden="true">
      <Circle className="deco-circle deco-1" />
      <Star className="deco-star deco-2" />
      <Circle className="deco-circle deco-3" />
      <Star className="deco-star deco-4" />
      <Circle className="deco-circle deco-5" />
      <Star className="deco-star deco-6" />
      <Circle className="deco-circle deco-7" />
    </div>
  )
}
