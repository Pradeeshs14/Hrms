import { useTheme } from '../context/ThemeContext'

const tones = {
  // for white / light surfaces
  light: 'text-slate-600 border border-slate-200 hover:bg-slate-100',
  // for the primary-800/900 headers and the login gradient
  dark: 'text-primary-100 border border-primary-700 hover:bg-primary-700/60',
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" aria-hidden="true">
      <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  )
}

export default function ThemeToggle({ tone = 'light', withLabel = false, className = '' }) {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      title={`Switch to ${next} theme`}
      aria-label={`Switch to ${next} theme`}
      aria-pressed={theme === 'dark'}
      className={`inline-flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium transition ${tones[tone] || tones.light} ${className}`}
    >
      {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
      {withLabel && <span className="hidden sm:inline">{theme === 'dark' ? 'Light' : 'Dark'}</span>}
    </button>
  )
}
