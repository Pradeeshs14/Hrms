import { useEffect } from 'react'

export function Card({ className = '', children }) {
  return <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>{children}</div>
}

export function PageTitle({ title, subtitle, actions }) {
  return (
    <div className="flex flex-wrap items-end gap-3 mb-6">
      <div className="mr-auto">
        <h2 className="text-2xl font-bold">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions}
    </div>
  )
}

const tones = {
  slate: 'bg-slate-100 text-slate-700',
  green: 'bg-green-100 text-green-700',
  red: 'bg-red-100 text-red-700',
  amber: 'bg-amber-100 text-amber-700',
  blue: 'bg-blue-100 text-blue-700',
  purple: 'bg-purple-100 text-purple-700',
}

export function Badge({ tone = 'slate', children }) {
  return <span className={`${tones[tone] || tones.slate} px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap`}>{children}</span>
}

const variants = {
  primary: 'bg-primary-600 text-white hover:bg-primary-700 disabled:bg-primary-300',
  secondary: 'bg-slate-700 text-white hover:bg-slate-800 disabled:bg-slate-400',
  ghost: 'border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:text-slate-400',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
}

export function Button({ variant = 'primary', className = '', ...props }) {
  return (
    <button
      {...props}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    />
  )
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-400 mt-1">{hint}</span>}
    </label>
  )
}

export const inputClass =
  'mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500'

export function Input(props) {
  return <input {...props} className={`${inputClass} ${props.className || ''}`} />
}

export function Select({ children, ...props }) {
  return <select {...props} className={`${inputClass} ${props.className || ''}`}>{children}</select>
}

export function Textarea(props) {
  return <textarea {...props} className={`${inputClass} ${props.className || ''}`} />
}

export function Modal({ open, title, onClose, children, footer, wide }) {
  useEffect(() => {
    if (!open || !onClose) return undefined
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-start justify-center p-4 z-40 overflow-y-auto"
      onClick={(event) => { if (event.target === event.currentTarget) onClose?.() }}>
      <div className={`bg-white rounded-xl shadow-xl w-full ${wide ? 'max-w-3xl' : 'max-w-lg'} mt-10`}>
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
        </div>
        <div className="p-5 space-y-4">{children}</div>
        {footer && <div className="px-5 py-4 border-t flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}

export function Alert({ tone = 'blue', children }) {
  if (!children) return null
  const map = {
    blue: 'bg-blue-50 text-blue-700',
    red: 'bg-red-50 text-red-700',
    green: 'bg-green-50 text-green-700',
    amber: 'bg-amber-50 text-amber-800',
  }
  return <div className={`text-sm px-3 py-2 rounded-lg mb-4 ${map[tone] || map.blue}`}>{children}</div>
}

export function StatCard({ label, value, tone = 'bg-primary-500', hint }) {
  return (
    <Card className="p-5">
      <div className={`w-9 h-9 ${tone} rounded-lg mb-3 opacity-90`} />
      <p className="text-slate-500 text-sm">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </Card>
  )
}

export function Table({ columns, rows, empty = 'No records found', rowKey = (row, i) => row.id ?? i }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>{columns.map((c) => <th key={c.key} className="px-4 py-3 font-medium whitespace-nowrap">{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">{empty}</td></tr>
          )}
          {rows.map((row, index) => (
            <tr key={rowKey(row, index)} className="border-t border-slate-100">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.className || ''}`}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex flex-wrap gap-1 mb-5 bg-slate-100 p-1 rounded-lg w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${active === tab.key ? 'bg-white shadow-sm text-primary-700' : 'text-slate-600 hover:text-slate-900'}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export function Spinner({ label = 'Loading...' }) {
  return <div className="text-slate-500 text-sm py-6">{label}</div>
}
