import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currentMonth, currentYear, download, todayISO } from '../../lib/format'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Table, Tabs, Textarea } from '../../components/ui'

const EMPTY = {
  name: '', code: '', start_time: '09:00', end_time: '18:00', grace_minutes: 10,
  standard_hours: 8, is_night: false, is_flexible: false, is_remote: false,
  is_default: false, is_active: true, description: '',
}

export default function ShiftsAdmin() {
  const [tab, setTab] = useState('shifts')
  const [shifts, setShifts] = useState([])
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const [assign, setAssign] = useState({ employee_id: '', shift_id: '', effective_from: todayISO(), effective_to: '', notes: '' })
  const [deptAssign, setDeptAssign] = useState({ department: '', shift_id: '', effective_from: todayISO() })
  const [history, setHistory] = useState([])
  const [assignments, setAssignments] = useState([])

  const [report, setReport] = useState(null)
  const [filters, setFilters] = useState({ month: currentMonth(), year: currentYear(), department: '', shift_id: '' })

  const loadShifts = () => api.get('/shifts').then((r) => setShifts(r.data)).catch(console.error)

  const loadPeople = () => {
    api.get('/compensation/employees').then((r) => {
      setEmployees(r.data)
      setDepartments([...new Set(r.data.map((e) => e.department).filter(Boolean))].sort())
    }).catch(console.error)
  }

  const loadAssignments = () => api.get('/shifts/assignments').then((r) => setAssignments(r.data)).catch(console.error)

  useEffect(() => {
    loadShifts()
    loadPeople()
    loadAssignments()
  }, [])

  useEffect(() => {
    if (!assign.employee_id) { setHistory([]); return }
    api.get(`/shifts/assignments/employee/${assign.employee_id}`).then((r) => setHistory(r.data)).catch(console.error)
  }, [assign.employee_id])

  useEffect(() => {
    if (tab !== 'reports') return
    const params = { month: filters.month, year: filters.year }
    if (filters.department) params.department = filters.department
    if (filters.shift_id) params.shift_id = filters.shift_id
    api.get('/shifts/reports/attendance', { params }).then((r) => setReport(r.data)).catch(console.error)
  }, [tab, filters])

  const saveShift = async () => {
    try {
      const payload = { ...form, grace_minutes: Number(form.grace_minutes), standard_hours: Number(form.standard_hours) }
      if (editing) await api.put(`/shifts/${editing}`, payload)
      else await api.post('/shifts', payload)
      setOpen(false)
      setMsg(editing ? 'Shift updated' : 'Shift created')
      loadShifts()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save shift')
    }
  }

  const deactivate = async (id) => {
    if (!window.confirm('Deactivate this shift?')) return
    try {
      await api.delete(`/shifts/${id}`)
      setMsg('Shift deactivated')
      loadShifts()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not deactivate shift')
    }
  }

  const assignEmployee = async () => {
    try {
      await api.post('/shifts/assign/employee', {
        employee_id: Number(assign.employee_id),
        shift_id: Number(assign.shift_id),
        effective_from: assign.effective_from,
        effective_to: assign.effective_to || null,
        notes: assign.notes || null,
      })
      setMsg('Shift assigned and the employee was notified')
      loadAssignments()
      api.get(`/shifts/assignments/employee/${assign.employee_id}`).then((r) => setHistory(r.data))
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not assign shift')
    }
  }

  const assignDepartment = async () => {
    try {
      await api.post('/shifts/assign/department', {
        department: deptAssign.department,
        shift_id: Number(deptAssign.shift_id),
        effective_from: deptAssign.effective_from,
      })
      setMsg(`Default shift set for ${deptAssign.department}`)
      loadAssignments()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not assign department shift')
    }
  }

  const exportCsv = () => {
    const params = { month: filters.month, year: filters.year }
    if (filters.department) params.department = filters.department
    if (filters.shift_id) params.shift_id = filters.shift_id
    api.get('/shifts/reports/attendance/export', { params, responseType: 'blob' })
      .then((r) => download(r.data, `shift_attendance_${filters.year}_${filters.month}.csv`))
  }

  const shiftColumns = [
    { key: 'name', label: 'Shift', render: (s) => <span className="font-medium">{s.name}</span> },
    { key: 'code', label: 'Code' },
    { key: 'timing', label: 'Timing', render: (s) => <span className="whitespace-nowrap">{s.start_time} – {s.end_time} ({s.span_hours}h)</span> },
    { key: 'standard_hours', label: 'Std hours' },
    { key: 'grace_minutes', label: 'Grace', render: (s) => `${s.grace_minutes} min` },
    {
      key: 'flags', label: 'Type', render: (s) => (
        <div className="flex flex-wrap gap-1">
          {s.is_night && <Badge tone="purple">Night</Badge>}
          {s.is_remote && <Badge tone="blue">Remote</Badge>}
          {s.is_flexible && <Badge tone="amber">Flexible</Badge>}
          {s.is_default && <Badge tone="green">Default</Badge>}
          {!s.is_active && <Badge>Inactive</Badge>}
        </div>
      ),
    },
    {
      key: 'actions', label: 'Actions', render: (s) => (
        <div className="flex gap-3 text-xs font-medium">
          <button className="text-primary-600 hover:underline" onClick={() => {
            setForm({
              name: s.name, code: s.code, start_time: s.start_time, end_time: s.end_time,
              grace_minutes: s.grace_minutes, standard_hours: s.standard_hours, is_night: s.is_night,
              is_flexible: s.is_flexible, is_remote: s.is_remote, is_default: s.is_default,
              is_active: s.is_active, description: s.description || '',
            })
            setEditing(s.id)
            setError('')
            setOpen(true)
          }}>Edit</button>
          {s.is_active && <button className="text-red-500 hover:underline" onClick={() => deactivate(s.id)}>Deactivate</button>}
        </div>
      ),
    },
  ]

  const reportColumns = [
    { key: 'date', label: 'Date' },
    { key: 'employee_code', label: 'Code' },
    { key: 'employee_name', label: 'Employee' },
    { key: 'shift_code', label: 'Shift' },
    { key: 'status', label: 'Status', render: (r) => <Badge tone={r.status === 'Present' ? 'green' : r.status === 'Half-day' ? 'amber' : 'slate'}>{r.status}</Badge> },
    { key: 'working_hours', label: 'Hours', render: (r) => Number(r.working_hours).toFixed(2) },
    { key: 'late_minutes', label: 'Late', render: (r) => r.is_late ? <Badge tone="red">{r.late_minutes} min</Badge> : <span className="text-slate-400">-</span> },
    { key: 'early_exit_minutes', label: 'Early exit', render: (r) => r.is_early_exit ? <Badge tone="amber">{r.early_exit_minutes} min</Badge> : <span className="text-slate-400">-</span> },
    { key: 'overtime_hours', label: 'Overtime', render: (r) => Number(r.overtime_hours) > 0 ? <Badge tone="blue">{Number(r.overtime_hours).toFixed(2)} h</Badge> : <span className="text-slate-400">-</span> },
  ]

  return (
    <div>
      <PageTitle
        title="Shifts & Work Schedules"
        subtitle="Define shifts, assign them to people or departments, and track shift-wise attendance"
        actions={<Button onClick={() => { setForm(EMPTY); setEditing(null); setError(''); setOpen(true) }}>Add shift</Button>}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && !open && <Alert tone="red">{error}</Alert>}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'shifts', label: 'Shifts' },
          { key: 'assign', label: 'Assignments' },
          { key: 'reports', label: 'Shift-wise attendance' },
        ]}
      />

      {tab === 'shifts' && <Table columns={shiftColumns} rows={shifts} empty="No shifts configured" />}

      {tab === 'assign' && (
        <div className="grid lg:grid-cols-2 gap-5">
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold">Assign to an employee</h3>
            <p className="text-xs text-slate-500">Employee-level assignments override the department default. History is kept for every change.</p>
            <Field label="Employee">
              <Select value={assign.employee_id} onChange={(e) => setAssign({ ...assign, employee_id: e.target.value })}>
                <option value="">Select employee</option>
                {employees.map((e) => <option key={e.employee_id} value={e.employee_id}>{e.employee_code} · {e.employee_name}</option>)}
              </Select>
            </Field>
            <Field label="Shift">
              <Select value={assign.shift_id} onChange={(e) => setAssign({ ...assign, shift_id: e.target.value })}>
                <option value="">Select shift</option>
                {shifts.filter((s) => s.is_active).map((s) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.start_time}-{s.end_time})</option>
                ))}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Effective from">
                <Input type="date" value={assign.effective_from} onChange={(e) => setAssign({ ...assign, effective_from: e.target.value })} />
              </Field>
              <Field label="Effective to" hint="Optional">
                <Input type="date" value={assign.effective_to} onChange={(e) => setAssign({ ...assign, effective_to: e.target.value })} />
              </Field>
            </div>
            <Field label="Notes">
              <Input value={assign.notes} onChange={(e) => setAssign({ ...assign, notes: e.target.value })} />
            </Field>
            <Button onClick={assignEmployee} disabled={!assign.employee_id || !assign.shift_id}>Assign shift</Button>

            {history.length > 0 && (
              <div className="pt-3 border-t">
                <h4 className="text-sm font-semibold mb-2">Shift history</h4>
                <ul className="space-y-2 text-sm">
                  {history.map((h) => (
                    <li key={h.id} className="flex items-center gap-2">
                      <Badge tone={h.effective_to ? 'slate' : 'green'}>{h.shift_code}</Badge>
                      <span className="text-slate-600">{h.effective_from} → {h.effective_to || 'current'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <Card className="p-5 space-y-4">
            <h3 className="font-semibold">Department default shift</h3>
            <p className="text-xs text-slate-500">Applies to every employee in the department who has no individual assignment.</p>
            <Field label="Department">
              <Select value={deptAssign.department} onChange={(e) => setDeptAssign({ ...deptAssign, department: e.target.value })}>
                <option value="">Select department</option>
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </Select>
            </Field>
            <Field label="Shift">
              <Select value={deptAssign.shift_id} onChange={(e) => setDeptAssign({ ...deptAssign, shift_id: e.target.value })}>
                <option value="">Select shift</option>
                {shifts.filter((s) => s.is_active).map((s) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.start_time}-{s.end_time})</option>
                ))}
              </Select>
            </Field>
            <Field label="Effective from">
              <Input type="date" value={deptAssign.effective_from} onChange={(e) => setDeptAssign({ ...deptAssign, effective_from: e.target.value })} />
            </Field>
            <Button onClick={assignDepartment} disabled={!deptAssign.department || !deptAssign.shift_id}>Set department shift</Button>

            <div className="pt-3 border-t">
              <h4 className="text-sm font-semibold mb-2">Current assignments</h4>
              <ul className="space-y-2 text-sm max-h-64 overflow-y-auto">
                {assignments.map((a) => (
                  <li key={`${a.employee_id || a.department}-${a.id}`} className="flex items-center gap-2">
                    <Badge tone={a.employee_id ? 'blue' : 'purple'}>{a.employee_id ? 'Employee' : 'Department'}</Badge>
                    <span className="text-slate-600">
                      {a.employee_id ? `#${a.employee_id}` : a.department} → {a.shift_code} from {a.effective_from}
                      {a.effective_to ? ` to ${a.effective_to}` : ''}
                    </span>
                  </li>
                ))}
                {assignments.length === 0 && <li className="text-slate-400">No assignments yet</li>}
              </ul>
            </div>
          </Card>
        </div>
      )}

      {tab === 'reports' && (
        <>
          <div className="flex flex-wrap gap-3 items-end mb-5">
            <Field label="Month">
              <Input type="number" min={1} max={12} value={filters.month}
                onChange={(e) => setFilters({ ...filters, month: Number(e.target.value) })} />
            </Field>
            <Field label="Year">
              <Input type="number" value={filters.year}
                onChange={(e) => setFilters({ ...filters, year: Number(e.target.value) })} />
            </Field>
            <Field label="Department">
              <Select value={filters.department} onChange={(e) => setFilters({ ...filters, department: e.target.value })}>
                <option value="">All</option>
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </Select>
            </Field>
            <Field label="Shift">
              <Select value={filters.shift_id} onChange={(e) => setFilters({ ...filters, shift_id: e.target.value })}>
                <option value="">All</option>
                {shifts.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </Field>
            <Button variant="ghost" onClick={exportCsv}>Export CSV</Button>
          </div>

          {report && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
              {report.by_shift.map((s) => (
                <Card key={s.shift_code} className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{s.shift_name}</span>
                    <Badge tone="blue">{s.shift_code}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-3 text-sm">
                    <span className="text-slate-500">Present</span><span className="text-right font-medium">{s.present}/{s.records}</span>
                    <span className="text-slate-500">Late</span><span className="text-right font-medium">{s.late}</span>
                    <span className="text-slate-500">Early exits</span><span className="text-right font-medium">{s.early_exits}</span>
                    <span className="text-slate-500">Overtime</span><span className="text-right font-medium">{s.overtime_hours} h</span>
                    <span className="text-slate-500">Hours logged</span><span className="text-right font-medium">{s.total_hours}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}

          <Table columns={reportColumns} rows={report?.rows || []} empty="No attendance records for this period" />
        </>
      )}

      <Modal
        open={open}
        title={editing ? 'Edit shift' : 'Add shift'}
        onClose={() => setOpen(false)}
        wide
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={saveShift} disabled={!form.name || !form.code}>{editing ? 'Save changes' : 'Create shift'}</Button>
        </>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Shift name">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Night Shift" />
          </Field>
          <Field label="Code" hint="Unique short code, e.g. NIGHT">
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} disabled={!!editing} />
          </Field>
          <Field label="Start time">
            <Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
          </Field>
          <Field label="End time">
            <Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
          </Field>
          <Field label="Grace minutes" hint="Late / early-exit tolerance">
            <Input type="number" min={0} value={form.grace_minutes} onChange={(e) => setForm({ ...form, grace_minutes: e.target.value })} />
          </Field>
          <Field label="Standard hours" hint="Hours above this count as overtime">
            <Input type="number" step="0.5" min={1} value={form.standard_hours} onChange={(e) => setForm({ ...form, standard_hours: e.target.value })} />
          </Field>
        </div>
        <Field label="Description">
          <Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <div className="flex flex-wrap gap-4 text-sm">
          {[['is_night', 'Night shift (crosses midnight)'], ['is_flexible', 'Flexible (no late tracking)'],
            ['is_remote', 'Remote'], ['is_default', 'Default for new joiners'], ['is_active', 'Active']].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2">
              <input type="checkbox" checked={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
      </Modal>
    </div>
  )
}
