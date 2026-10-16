import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currentMonth, currentYear, periodLabel, time } from '../../lib/format'
import { Badge, Button, Card, Field, Input, PageTitle, Spinner, StatCard, Table } from '../../components/ui'

const STATUS_TONE = {
  Present: 'green', 'Half-day': 'amber', Absent: 'red',
  'Paid Leave': 'blue', 'Unpaid Leave (LOP)': 'red', Upcoming: 'slate',
}

export default function EmpAttendance() {
  const [month, setMonth] = useState(currentMonth())
  const [year, setYear] = useState(currentYear())
  const [summary, setSummary] = useState(null)
  const [history, setHistory] = useState([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => {
    api.get('/attendance/summary/me', { params: { month, year } })
      .then((r) => setSummary(r.data)).catch(console.error)
    api.get('/attendance/me', { params: { month, year } })
      .then((r) => setHistory(r.data)).catch(console.error)
  }

  useEffect(() => { load() }, [month, year])

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

  const columns = [
    { key: 'date', label: 'Date' },
    { key: 'shift_code', label: 'Shift', render: (a) => a.shift_code ? <Badge tone="purple">{a.shift_code}</Badge> : '-' },
    { key: 'check_in', label: 'In', render: (a) => time(a.check_in) },
    { key: 'check_out', label: 'Out', render: (a) => time(a.check_out) },
    { key: 'working_hours', label: 'Hours', render: (a) => (a.working_hours ? Number(a.working_hours).toFixed(2) : '-') },
    { key: 'late_minutes', label: 'Late', render: (a) => (a.is_late ? <Badge tone="red">{a.late_minutes} min</Badge> : '-') },
    { key: 'early_exit_minutes', label: 'Early exit', render: (a) => (a.is_early_exit ? <Badge tone="amber">{a.early_exit_minutes} min</Badge> : '-') },
    { key: 'overtime_hours', label: 'OT', render: (a) => (Number(a.overtime_hours) > 0 ? `${Number(a.overtime_hours).toFixed(2)} h` : '-') },
    { key: 'status', label: 'Status', render: (a) => <Badge tone={STATUS_TONE[a.status] || 'slate'}>{a.status}</Badge> },
  ]

  return (
    <div>
      <PageTitle
        title="My Attendance"
        subtitle="Weekends and company/regional holidays are excluded from your attendance"
        actions={<>
          <Field label="Month">
            <Input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} />
          </Field>
          <Field label="Year">
            <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
          </Field>
          <Button className="bg-green-600 hover:bg-green-700" onClick={() => act('/attendance/check-in', 'Checked in')}>Check in</Button>
          <Button variant="secondary" onClick={() => act('/attendance/check-out', 'Checked out')}>Check out</Button>
        </>}
      />
      {msg && <div className="mb-4 text-sm bg-green-50 text-green-700 px-3 py-2 rounded-lg">{msg}</div>}
      {error && <div className="mb-4 text-sm bg-red-50 text-red-700 px-3 py-2 rounded-lg">{error}</div>}

      {!summary ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-5">
            <StatCard label="Working days" value={summary.working_days} tone="bg-primary-500" />
            <StatCard label="Holidays" value={summary.holiday_days} tone="bg-red-400" />
            <StatCard label="Present" value={summary.present_days} tone="bg-green-500" />
            <StatCard label="Paid leave" value={summary.paid_leave_days} tone="bg-blue-500" />
            <StatCard label="LOP days" value={summary.lop_days} tone="bg-amber-500" />
            <StatCard label="Absent" value={summary.absent_days} tone="bg-rose-500" />
            <StatCard label="Late days" value={summary.late_days} tone="bg-orange-500" />
            <StatCard label="Early exits" value={summary.early_exits} tone="bg-slate-500" />
            <StatCard label="Overtime" value={`${summary.overtime_hours} h`} tone="bg-indigo-500" />
            <StatCard label="Hours logged" value={`${summary.total_hours} h`} tone="bg-cyan-600" />
          </div>

          {summary.holidays.length > 0 && (
            <Card className="p-4 mb-5">
              <h3 className="text-sm font-semibold mb-2">Holidays in {periodLabel(month, year)}</h3>
              <div className="flex flex-wrap gap-2">
                {summary.holidays.map((h) => (
                  <Badge key={h.date} tone={h.holiday_type === 'Regional' ? 'amber' : 'red'}>
                    {h.date} · {h.name}{h.region ? ` (${h.region})` : ''}
                  </Badge>
                ))}
              </div>
            </Card>
          )}

          <h3 className="font-semibold mb-3">Day-by-day</h3>
          <Table
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'shift_code', label: 'Shift', render: (d) => d.shift_code || '-' },
              { key: 'status', label: 'Status', render: (d) => <Badge tone={STATUS_TONE[d.status] || 'slate'}>{d.status}</Badge> },
              { key: 'working_hours', label: 'Hours', render: (d) => (d.working_hours ? Number(d.working_hours).toFixed(2) : '-') },
              { key: 'overtime_hours', label: 'OT', render: (d) => (Number(d.overtime_hours) > 0 ? Number(d.overtime_hours).toFixed(2) : '-') },
              { key: 'is_late', label: 'Late', render: (d) => (d.is_late ? <Badge tone="red">Yes</Badge> : '-') },
            ]}
            rows={summary.days}
            rowKey={(d) => d.date}
            empty="No working days in this month"
          />

          <h3 className="font-semibold mb-3 mt-6">Raw check-in records</h3>
          <Table columns={columns} rows={history} empty="No attendance records for this month" />
        </>
      )}
    </div>
  )
}
