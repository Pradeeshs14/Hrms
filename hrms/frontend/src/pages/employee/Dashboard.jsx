import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import { currency, periodLabel, WEEKDAYS } from '../../lib/format'
import { Alert, Badge, Button, Card, PageTitle, Spinner, StatCard } from '../../components/ui'

export default function EmpDashboard() {
  const [data, setData] = useState(null)
  const [shift, setShift] = useState(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => {
    api.get('/reports/me/dashboard').then((r) => setData(r.data)).catch(console.error)
    api.get('/shifts/me').then((r) => setShift(r.data)).catch(console.error)
  }

  useEffect(() => { load() }, [])

  const act = async (url, okMessage) => {
    setError('')
    try {
      await api.post(url, {})
      setMsg(okMessage)
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Action failed')
    }
  }

  if (!data) return <Spinner />

  const attendance = data.attendance
  const month = new Date().getMonth() + 1
  const year = new Date().getFullYear()

  return (
    <div>
      <PageTitle
        title={`Welcome, ${data.name.split(' ')[0]}!`}
        subtitle={`${data.designation || 'Employee'} · ${data.department || 'Unassigned'}${data.region ? ` · ${data.region}` : ''}`}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && <Alert tone="red">{error}</Alert>}

      <div className="grid sm:grid-cols-2 gap-4 mb-5">
        <Card className="p-5">
          <h3 className="font-semibold mb-3">Today's attendance</h3>
          <div className="flex flex-wrap gap-2 mb-3 text-xs">
            <Badge tone={attendance.checked_in_today ? 'green' : 'slate'}>
              {attendance.checked_in_today ? 'Checked in' : 'Not checked in'}
            </Badge>
            <Badge tone={attendance.checked_out_today ? 'blue' : 'slate'}>
              {attendance.checked_out_today ? 'Checked out' : 'Still in office'}
            </Badge>
          </div>
          <div className="flex gap-3">
            <Button
              className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-300"
              disabled={attendance.checked_in_today}
              onClick={() => act('/attendance/check-in', 'Checked in successfully')}
            >
              Check in
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              disabled={!attendance.checked_in_today || attendance.checked_out_today}
              onClick={() => act('/attendance/check-out', 'Checked out successfully')}
            >
              Check out
            </Button>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-start justify-between">
            <h3 className="font-semibold mb-2">My shift</h3>
            {data.shift?.is_night && <Badge tone="purple">Night</Badge>}
            {data.shift?.is_remote && <Badge tone="blue">Remote</Badge>}
            {data.shift?.is_flexible && <Badge tone="amber">Flexible</Badge>}
          </div>
          {data.shift ? (
            <>
              <p className="text-lg font-semibold">{data.shift.name}</p>
              <p className="text-sm text-slate-500">
                {data.shift.start_time} – {data.shift.end_time} · {data.shift.standard_hours} h standard ·
                {' '}{data.shift.grace_minutes} min grace
              </p>
              {shift?.schedule && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {shift.schedule.map((day) => (
                    <div key={day.date}
                      className={`text-[11px] px-2 py-1 rounded-lg border ${day.is_weekend ? 'bg-slate-50 text-slate-400' : 'bg-white'}`}>
                      <div className="font-medium">{WEEKDAYS[day.weekday]}</div>
                      <div>{day.is_weekend ? 'Off' : (day.shift || 'Off')}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : <p className="text-sm text-slate-500">No shift assigned yet — contact HR.</p>}
        </Card>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <StatCard label={`Present (${periodLabel(month, year)})`} value={attendance.present_days} tone="bg-green-500"
          hint={`of ${attendance.working_days} working days`} />
        <StatCard label="Holidays this month" value={attendance.holiday_days} tone="bg-red-400" />
        <StatCard label="Late days" value={attendance.late_days} tone="bg-amber-500" />
        <StatCard label="Overtime" value={`${attendance.overtime_hours} h`} tone="bg-blue-500" />
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Upcoming holidays</h3>
            <Link to="/employee/calendar" className="text-xs text-primary-600 hover:underline">Calendar</Link>
          </div>
          <ul className="space-y-2 text-sm">
            {data.upcoming_holidays.map((h) => (
              <li key={`${h.date}-${h.name}`} className="flex items-center gap-2 border-b border-slate-50 pb-2 last:border-0">
                <span className="text-slate-500 w-24">{h.date}</span>
                <span className="font-medium">{h.name}</span>
                {h.holiday_type !== 'Company' && <Badge tone="amber">{h.holiday_type}</Badge>}
              </li>
            ))}
            {data.upcoming_holidays.length === 0 && <li className="text-slate-400">No upcoming holidays</li>}
          </ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Leave balance</h3>
            <Link to="/employee/leave" className="text-xs text-primary-600 hover:underline">Apply</Link>
          </div>
          <ul className="space-y-2 text-sm">
            {data.leave_balances.map((b) => (
              <li key={b.leave_type} className="flex justify-between border-b border-slate-50 pb-2 last:border-0">
                <span>{b.leave_type}</span>
                <span className="font-medium">{b.balance} days</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Pay summary</h3>
            <Link to="/employee/payroll" className="text-xs text-primary-600 hover:underline">Payslips</Link>
          </div>
          <p className="text-sm text-slate-500">Monthly CTC</p>
          <p className="text-xl font-bold">{currency(data.monthly_ctc)}</p>
          {data.latest_payslip ? (
            <div className="mt-3 text-sm">
              <p className="text-slate-500">Latest payslip</p>
              <p className="font-medium">
                {periodLabel(data.latest_payslip.month, data.latest_payslip.year)} · {currency(data.latest_payslip.net_salary)}
              </p>
              <Badge tone={data.latest_payslip.status === 'Credited' ? 'green' : 'amber'}>{data.latest_payslip.status}</Badge>
            </div>
          ) : <p className="text-sm text-slate-400 mt-3">No payslip generated yet</p>}
          <p className="text-xs text-slate-400 mt-3">{data.unread_notifications} unread alert(s)</p>
        </Card>
      </div>

      <Card className="p-5 mt-5">
        <h3 className="font-semibold mb-2">Profile summary</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <Info label="Employee ID" value={`#${data.employee_id}`} />
          <Info label="Department" value={data.department || '-'} />
          <Info label="Designation" value={data.designation || '-'} />
          <Info label="Region" value={data.region || '-'} />
        </div>
      </Card>
    </div>
  )
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}
