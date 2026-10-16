import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import { download, todayISO } from '../../lib/format'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Table, Textarea } from '../../components/ui'

const TYPE_TONE = { Company: 'red', Regional: 'amber', Optional: 'blue' }
const EMPTY = { name: '', date: todayISO(), holiday_type: 'Company', region: '', description: '', is_active: true }

export default function HolidaysAdmin() {
  const [year, setYear] = useState(new Date().getFullYear())
  const [items, setItems] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => api.get('/holidays', { params: { year, active_only: false } })
    .then((r) => setItems(r.data)).catch(console.error)

  useEffect(() => { load() }, [year])

  const openCreate = () => { setForm(EMPTY); setEditing(null); setError(''); setOpen(true) }
  const openEdit = (holiday) => {
    setForm({
      name: holiday.name, date: holiday.date, holiday_type: holiday.holiday_type,
      region: holiday.region || '', description: holiday.description || '', is_active: holiday.is_active,
    })
    setEditing(holiday.id)
    setError('')
    setOpen(true)
  }

  const save = async () => {
    const payload = {
      ...form,
      date: form.date,
      region: form.holiday_type === 'Regional' ? form.region : null,
    }
    try {
      if (editing) await api.put(`/holidays/${editing}`, payload)
      else await api.post('/holidays', payload)
      setOpen(false)
      setMsg(editing ? 'Holiday updated' : 'Holiday added and staff notified')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save holiday')
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Delete this holiday? Attendance and payroll will be recalculated without it.')) return
    try {
      await api.delete(`/holidays/${id}`)
      setMsg('Holiday deleted')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not delete holiday')
    }
  }

  const exportCsv = () => {
    api.get('/reports/holidays/export', { params: { year }, responseType: 'blob' })
      .then((r) => download(r.data, `holidays_${year}.csv`))
  }

  const columns = [
    { key: 'date', label: 'Date', render: (h) => <span className="whitespace-nowrap">{h.date}</span> },
    { key: 'name', label: 'Holiday', render: (h) => <span className="font-medium">{h.name}</span> },
    { key: 'holiday_type', label: 'Type', render: (h) => <Badge tone={TYPE_TONE[h.holiday_type]}>{h.holiday_type}</Badge> },
    { key: 'region', label: 'Region', render: (h) => h.region || <span className="text-slate-400">All</span> },
    { key: 'is_active', label: 'Status', render: (h) => <Badge tone={h.is_active ? 'green' : 'slate'}>{h.is_active ? 'Active' : 'Inactive'}</Badge> },
    {
      key: 'actions', label: 'Actions', render: (h) => (
        <div className="flex gap-3 text-xs font-medium">
          <button onClick={() => openEdit(h)} className="text-primary-600 hover:underline">Edit</button>
          <button onClick={() => remove(h.id)} className="text-red-500 hover:underline">Delete</button>
        </div>
      ),
    },
  ]

  const counts = items.reduce((acc, h) => ({ ...acc, [h.holiday_type]: (acc[h.holiday_type] || 0) + 1 }), {})

  return (
    <div>
      <PageTitle
        title="Holidays & Calendar"
        subtitle={`${items.length} holidays in ${year} — excluded from attendance, leave and payroll`}
        actions={<>
          <Field label="Year">
            <Select value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {[year - 1, year, year + 1].map((y) => <option key={y} value={y}>{y}</option>)}
            </Select>
          </Field>
          <Button variant="ghost" onClick={exportCsv}>Export CSV</Button>
          <Link to="/admin/calendar" className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50">
            Open calendar
          </Link>
          <Button onClick={openCreate}>Add holiday</Button>
        </>}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && !open && <Alert tone="red">{error}</Alert>}

      <div className="flex flex-wrap gap-3 mb-4 text-sm">
        <Card className="px-4 py-2">Company: <span className="font-semibold">{counts.Company || 0}</span></Card>
        <Card className="px-4 py-2">Regional: <span className="font-semibold">{counts.Regional || 0}</span></Card>
        <Card className="px-4 py-2">Optional: <span className="font-semibold">{counts.Optional || 0}</span></Card>
      </div>

      <Table columns={columns} rows={items} empty={`No holidays configured for ${year}`} />

      <Modal
        open={open}
        title={editing ? 'Edit holiday' : 'Add holiday'}
        onClose={() => setOpen(false)}
        footer={<>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={save} disabled={!form.name || !form.date || (form.holiday_type === 'Regional' && !form.region)}>
            {editing ? 'Save changes' : 'Add holiday'}
          </Button>
        </>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        <Field label="Holiday name">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Diwali" />
        </Field>
        <Field label="Date">
          <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        </Field>
        <Field label="Type" hint="Company and Regional holidays are non-working. Optional holidays are shown in the calendar but do not block attendance.">
          <Select value={form.holiday_type} onChange={(e) => setForm({ ...form, holiday_type: e.target.value })}>
            <option value="Company">Company-wide</option>
            <option value="Regional">Regional</option>
            <option value="Optional">Optional</option>
          </Select>
        </Field>
        {form.holiday_type === 'Regional' && (
          <Field label="Region" hint="Applies only to employees whose region matches">
            <Input value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="Tamil Nadu" />
          </Field>
        )}
        <Field label="Description">
          <Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>
      </Modal>
    </div>
  )
}
