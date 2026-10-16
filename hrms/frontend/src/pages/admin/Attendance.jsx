import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currentMonth, currentYear, download, time, todayISO } from '../../lib/format'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Table, Tabs, Textarea } from '../../components/ui'

const STATUS_TONE = { Present: 'green', 'Half-day': 'amber', Absent: 'red', Leave: 'blue', 'Paid Leave': 'blue', 'Unpaid Leave (LOP)': 'red', Upcoming: 'slate' }

export default function AttendanceAdmin() {
  const [tab, setTab] = useState('today')
  const [today, setToday] = useState([])
  const [employees, setEmployees] = useState([])
  const [summary, setSummary] = useState(null)
  const [target, setTarget] = useState('')
  const [period, setPeriod] = useState({ month: currentMonth(), year: currentYear() })
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [shifts, setShifts] = useState([])
  const [form, setForm] = useState({
    date: todayISO(), check_in: '', check_out: '', status: '', shift_id: '', overtime_hours: '', notes: '',
  })

  useEffect(() => {
    api.get('/attendance/today').then((r) => setToday(r.data)).catch(console.error)
    api.get('/compensation/employees').then((r) => setEmployees(r.data)).catch(console.error)
    api.get('/shifts', { params: { active_only: true } }).then((r) => setShifts(r.data)).catch(console.error)
  }, [])

  const loadSummary = (employeeId, month = period.month, year = period.year) => {
    if (!employeeId) { setSummary(null); return }
    api.get(`/attendance/summary/${employeeId}`, { params: { month, year } })
      .then((r) => setSummary(r.data)).catch(console.error)
  }

  useEffect(() => { loadSummary(target) }, [target, period])

  const openOverride = (row) => {
    setForm({
      date: row?.date || todayISO(),
      check_in: row?.check_in ? row.check_in.slice(0, 16) : '',
      check_out: row?.check_out ? row.check_out.slice(0, 16) : '',
      status: row?.status || '',
      shift_id: row?.shift_id || '',
      overtime_hours: row?.overtime_hours ?? '',
      notes: row?.notes || '',
    })
    setTarget(String(row?.employee_id || target || ''))
    setError('')
    setOverrideOpen(true)
  }

  const submitOverride = async () => {
    if (!target) { setError('Select an employee first'); return }
    try {
      await api.post(`/attendance/override/${target}`, {
        date: form.date,
        check_in: form.check_in ? `${form.check_in}:00` : null,
        check_out: form.check_out ? `${form.check_out}:00` : null,
        status: form.status || null,
        shift_id: form.shift_id ? Number(form.shift_id) : null,
        overtime_hours: form.overtime_hours === '' ? null : Number(form.overtime_hours),
        notes: form.notes || null,
      })
      setOverrideOpen(false)
      setMsg('Attendance corrected (audited)')
      api.get('/attendance/today').then((r) => setToday(r.data))
      loadSummary(target)
    } catch (e) {
      setError(e.response?.data?.detail || 'Override failed')
    }
  }

  const exportAttendance = () => {
    api.get('/reports/attendance/export', { params: period, responseType: 'blob' })
      .then((r) => download(r.data, `attendance_${period.year}_${period.month}.csv`))
  }

  const todayColumns = [
    { key: 'employee_name', label: 'Employee', render: (a) => <span className="font-medium">{a.employee_name || `#${a.employee_id}`}</span> },
    { key: 'shift_code', label: 'Shift', render: (a) => a.shift_code ? <Badge tone="purple">{a.shift_code}</Badge> : <span className="text-slate-400">-</span> },
    { key: 'check_in', label: 'Check in', render: (a) => time(a.check_in) },
    { key: 'check_out', label: 'Check out', render: (a) => time(a.check_out) },
    { key: 'working_hours', label: 'Hours', render: (a) => (a.working_hours ? Number(a.working_hours).toFixed(2) : '-') },
    { key: 'late_minutes', label: 'Late', render: (a) => (a.is_late ? <Badge tone="red">{a.late_minutes} min</Badge> : <span className="text-slate-400">-</span>) },
    { key: 'early_exit_minutes', label: 'Early exit', render: (a) => (a.is_early_exit ? <Badge tone="amber">{a.early_exit_minutes} min</Badge> : <span className="text-slate-400">-</span>) },
    { key: 'overtime_hours', label: 'Overtime', render: (a) => (Number(a.overtime_hours) > 0 ? <Badge tone="blue">{Number(a.overtime_hours).toFixed(2)} h</Badge> : '-') },
    { key: 'status', label: 'Status', render: (a) => <Badge tone={STATUS_TONE[a.status] || 'slate'}>{a.status}</Badge> },
    { key: 'override', label: '', render: (a) => (
      <button className="text-primary-600 text-xs font-medium hover:underline" onClick={() => openOverride(a)}>Override</button>
    ) },
  ]

  const dayColumns = [
    { key: 'date', label: 'Date' },
    { key: 'shift_code', label: 'Shift', render: (d) => d.shift_code || '-' },
    {
      key: 'status', label: 'Status', render: (d) => (
        <Badge tone={STATUS_TONE[d.status] || 'slate'}>{d.status}</Badge>
      ),
    },
    { key: 'working_hours', label: 'Hours', render: (d) => (d.working_hours ? Number(d.working_hours).toFixed(2) : '-') },
    { key: 'overtime_hours', label: 'OT', render: (d) => (Number(d.overtime_hours) > 0 ? Number(d.overtime_hours).toFixed(2) : '-') },
    { key: 'is_late', label: 'Late', render: (d) => (d.is_late ? <Badge tone="red">Yes</Badge> : '-') },
  ]

  return (
    <div>
      <PageTitle
        title="Attendance"
        subtitle="Shift-aware check-in tracking with holiday exclusion and admin override"
        actions={<>
          <Field label="Month">
            <Input type="number" min={1} max={12} value={period.month}
              onChange={(e) => setPeriod({ ...period, month: Number(e.target.value) })} />
          </Field>
          <Field label="Year">
            <Input type="number" value={period.year}
              onChange={(e) => setPeriod({ ...period, year: Number(e.target.value) })} />
          </Field>
          <Button variant="ghost" onClick={exportAttendance}>Export CSV</Button>
          <Button onClick={() => openOverride(null)}>Override attendance</Button>
        </>}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && !overrideOpen && <Alert tone="red">{error}</Alert>}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'today', label: "Today's attendance" },
          { key: 'summary', label: 'Monthly summary' },
        ]}
      />

      {tab === 'today' && (
        <Table columns={todayColumns} rows={today} empty="No attendance records for today" />
      )}

      {tab === 'summary' && (
        <>
          <div className="mb-4 max-w-sm">
            <Field label="Employee">
              <Select value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">Select employee</option>
                {employees.map((e) => (
                  <option key={e.employee_id} value={e.employee_id}>{e.employee_code} · {e.employee_name}</option>
                ))}
              </Select>
            </Field>
          </div>

          {summary && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-5">
                <Stat label="Working days" value={summary.working_days} />
                <Stat label="Holidays" value={summary.holiday_days} />
                <Stat label="Present" value={summary.present_days} />
                <Stat label="Paid leave" value={summary.paid_leave_days} />
                <Stat label="LOP days" value={summary.lop_days} />
                <Stat label="Absent" value={summary.absent_days} />
                <Stat label="Late days" value={summary.late_days} />
                <Stat label="Early exits" value={summary.early_exits} />
                <Stat label="Overtime" value={`${summary.overtime_hours} h`} />
                <Stat label="Hours logged" value={`${summary.total_hours} h`} />
              </div>

              {summary.holidays.length > 0 && (
                <Card className="p-4 mb-5">
                  <h3 className="text-sm font-semibold mb-2">Holidays excluded this month</h3>
                  <div className="flex flex-wrap gap-2">
                    {summary.holidays.map((h) => (
                      <Badge key={h.date} tone={h.holiday_type === 'Regional' ? 'amber' : 'red'}>
                        {h.date} · {h.name}
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}

              <Table columns={dayColumns} rows={summary.days} empty="No working days in this period" rowKey={(d) => d.date} />
            </>
          )}
          {!summary && <Card className="p-8 text-center text-slate-400 text-sm">Pick an employee to view the monthly summary</Card>}
        </>
      )}

      <Modal
        open={overrideOpen}
        title="Override attendance"
        onClose={() => setOverrideOpen(false)}
        wide
        footer={<>
          <Button variant="ghost" onClick={() => setOverrideOpen(false)}>Cancel</Button>
          <Button onClick={submitOverride} disabled={!target}>Save correction</Button>
        </>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        <Field label="Employee">
          <Select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">Select employee</option>
            {employees.map((e) => (
              <option key={e.employee_id} value={e.employee_id}>{e.employee_code} · {e.employee_name}</option>
            ))}
          </Select>
        </Field>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Date">
            <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <Field label="Shift" hint="Leave empty to use the assigned shift">
            <Select value={form.shift_id} onChange={(e) => setForm({ ...form, shift_id: e.target.value })}>
              <option value="">Assigned shift</option>
              {shifts.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.start_time}-{s.end_time})</option>)}
            </Select>
          </Field>
          <Field label="Check in">
            <Input type="datetime-local" value={form.check_in} onChange={(e) => setForm({ ...form, check_in: e.target.value })} />
          </Field>
          <Field label="Check out">
            <Input type="datetime-local" value={form.check_out} onChange={(e) => setForm({ ...form, check_out: e.target.value })} />
          </Field>
          <Field label="Status" hint="Late / early-exit / overtime recompute automatically">
            <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="">Keep computed</option>
              {['Present', 'Half-day', 'Absent', 'Leave'].map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
          <Field label="Overtime hours" hint="Optional manual override">
            <Input type="number" step="0.25" value={form.overtime_hours}
              onChange={(e) => setForm({ ...form, overtime_hours: e.target.value })} />
          </Field>
        </div>
        <Field label="Notes">
          <Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Field>
      </Modal>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <Card className="p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </Card>
  )
}
