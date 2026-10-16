import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import HolidayCalendar from '../components/HolidayCalendar'
import { Button, Card, Field, PageTitle, Select, Spinner, StatCard } from '../components/ui'
import { currentMonth, currentYear, monthName } from '../lib/format'

export default function CalendarPage() {
  const { isAdmin } = useAuth()
  const [year, setYear] = useState(currentYear())
  const [month, setMonth] = useState(currentMonth())
  const [view, setView] = useState('month')
  const [monthData, setMonthData] = useState(null)
  const [yearData, setYearData] = useState(null)
  const [selectedYearMonth, setSelectedYearMonth] = useState(currentMonth())

  useEffect(() => {
    if (view === 'month') {
      api.get('/holidays/calendar', { params: { year, month } }).then((r) => setMonthData(r.data)).catch(console.error)
    } else {
      api.get('/holidays/calendar/year', { params: { year } }).then((r) => {
        setYearData(r.data)
        setSelectedYearMonth((prev) => prev)
      }).catch(console.error)
    }
  }, [year, month, view])

  const shiftMonth = (delta) => {
    let m = month + delta
    let y = year
    if (m < 1) { m = 12; y -= 1 }
    if (m > 12) { m = 1; y += 1 }
    setMonth(m)
    setYear(y)
  }

  const yearlyMonths = yearData?.months || []
  const activeYearMonth = yearlyMonths.find((m) => m.month === selectedYearMonth)

  return (
    <div>
      <PageTitle
        title="Company Calendar"
        subtitle="Holidays are excluded from attendance, leave and payroll calculations"
        actions={
          <div className="flex flex-wrap items-end gap-3">
            <Field label="View">
              <Select value={view} onChange={(e) => setView(e.target.value)}>
                <option value="month">Monthly</option>
                <option value="year">Yearly</option>
              </Select>
            </Field>
            <Field label="Year">
              <Select value={year} onChange={(e) => setYear(Number(e.target.value))}>
                {[currentYear() - 1, currentYear(), currentYear() + 1].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </Select>
            </Field>
            {isAdmin && (
              <Link to="/admin/holidays" className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50">
                Manage holidays
              </Link>
            )}
          </div>
        }
      />

      {view === 'month' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard label="Working days" value={monthData?.working_days ?? '-'} tone="bg-primary-500" />
            <StatCard label="Holidays" value={monthData?.holiday_count ?? '-'} tone="bg-red-400" />
            <StatCard label="Optional holidays" value={monthData?.optional_count ?? '-'} tone="bg-blue-400" />
            <StatCard label="Weekends" value={monthData ? monthData.days.filter((d) => d.is_weekend).length : '-'} tone="bg-slate-400" />
          </div>
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <Button variant="ghost" onClick={() => shiftMonth(-1)}>← Previous</Button>
              <span className="font-semibold">{monthName(month)} {year}</span>
              <Button variant="ghost" onClick={() => shiftMonth(1)}>Next →</Button>
            </div>
            {monthData ? (
              <HolidayCalendar
                year={year}
                month={month}
                days={monthData.days}
                holidays={monthData.holidays}
              />
            ) : <Spinner />}
          </Card>
        </>
      )}

      {view === 'year' && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Total holidays" value={yearData?.total_holidays ?? '-'} tone="bg-red-400" />
            <StatCard label="Total working days" value={yearData?.total_working_days ?? '-'} tone="bg-primary-500" />
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {yearlyMonths.map((m) => (
              <Card key={m.month} className="p-4">
                <button
                  className="w-full text-left"
                  onClick={() => { setSelectedYearMonth(m.month); setMonth(m.month); setView('month') }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{monthName(m.month)}</span>
                    <span className="text-xs text-slate-500">{m.working_days} working days</span>
                  </div>
                  <div className="mt-2 space-y-1">
                    {m.holidays.length === 0 && <p className="text-xs text-slate-400">No holidays</p>}
                    {m.holidays.map((h) => (
                      <p key={h.id} className="text-xs text-slate-600 truncate">
                        {h.date.slice(8)} · {h.name}
                        {h.holiday_type !== 'Company' && <span className="text-slate-400"> ({h.holiday_type})</span>}
                      </p>
                    ))}
                  </div>
                </button>
              </Card>
            ))}
          </div>
          {activeYearMonth && (
            <Card className="p-5">
              <h3 className="font-semibold mb-3">{monthName(activeYearMonth.month)} {year} overview</h3>
              <HolidayCalendar
                year={year}
                month={activeYearMonth.month}
                days={activeYearMonth.days}
                holidays={activeYearMonth.holidays}
              />
            </Card>
          )}
        </div>
      )}

      {!monthData && view === 'month' && <Spinner />}
    </div>
  )
}
