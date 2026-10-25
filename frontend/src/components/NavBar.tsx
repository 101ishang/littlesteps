export type Page = 'app' | 'about' | 'sources'

interface NavBarProps {
  page: Page
  onNavigate: (page: Page) => void
}

export function NavBar({ page, onNavigate }: NavBarProps) {
  return (
    <nav className="nav-bar">
      <button
        className={`nav-link ${page === 'app' ? 'active' : ''}`}
        onClick={() => onNavigate('app')}
      >
        🏠 Home
      </button>
      <button
        className={`nav-link ${page === 'about' ? 'active' : ''}`}
        onClick={() => onNavigate('about')}
      >
        💡 About
      </button>
      <button
        className={`nav-link ${page === 'sources' ? 'active' : ''}`}
        onClick={() => onNavigate('sources')}
      >
        📚 Sources
      </button>
    </nav>
  )
}
