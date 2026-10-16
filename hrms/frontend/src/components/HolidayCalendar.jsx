import { WEEKDAYS, monthName } from '../lib/format'

const TYPE_STYLES = {
  Company: 'bg-red-100 text-red-700 border-red-200',
  Regional: 'bg-amber-100 text-amber-800 border-amber-200',
  Optional: 'bg-blue-50 text-blue-700 border-blue-200',
}

export default function HolidayCalendar({ year, month, days, holidays = [], compact = false }) {
  const first = new Date(year, month - 1, 1)
  const leading = first.getDay()
  const totalInMonth = new Date(year, month, 0).getDate()
  const byDate = Object.fromEntries((days || []).map((d) => [d.date, d]))
  const cells = []
  for (let i = 0; i < leading; i += 1) cells.push(null)
  for (let day = 1; day <= totalInMonth; day += 1) {
    const iso = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    cells.push(byDate[iso] || { date: iso, day, is_weekend: new Date(year, month - 1, day).getDay() % 6 === 0 })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">{monthName(month)} {year}</h3>
        {!compact && (
          <div className="flex gap-3 text-xs text-slate-500">
            <Legend className="bg-red-300" label="Company" />
            <Legend className="bg-amber-300" label="Regional" />
            <Legend className="bg-blue-300" label="Optional" />
          </div>
        )}
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-slate-500 mb-1">
        {WEEKDAYS.map((d) => <div key={d} className="py-1">{d}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell, index) => {
          if (!cell) return <div key={`blank-${index}`} />
          const style = cell.is_holiday
            ? TYPE_STYLES[cell.holiday_type] || TYPE_STYLES.Company
            : cell.is_optional_holiday
              ? TYPE_STYLES.Optional
              : cell.is_weekend
                ? 'bg-slate-50 text-slate-400 border-slate-100'
                : 'bg-white text-slate-700 border-slate-200'
          return (
            <div
              key={cell.date}
              title={cell.holiday_name || ''}
              className={`border rounded-lg p-1.5 min-h-[62px] text-left ${style}`}
            >
              <div className="text-xs font-semibold">{cell.day}</div>
              {cell.holiday_name && (
                <div className="text-[10px] leading-tight mt-0.5 break-words">{cell.holiday_name}</div>
              )}
            </div>
          )
        })}
      </div>

      {holidays.length > 0 && (
        <ul className="mt-5 space-y-2">
          {holidays.map((h) => (
            <li key={h.id} className="flex flex-wrap items-center gap-2 text-sm border-b border-slate-50 pb-2 last:border-0">
              <span className="w-24 text-slate-500">{h.date}</span>
              <span className="font-medium">{h.name}</span>
              <span className={`ml-auto px-2 py-0.5 rounded-full text-xs border ${TYPE_STYLES[h.holiday_type] || TYPE_STYLES.Company}`}>
                {h.holiday_type}{h.region ? ` · ${h.region}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Legend({ className, label }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`w-3 h-3 rounded ${className}`} />
      {label}
    </span>
  )
}
