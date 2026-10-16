import { useEffect, useState } from 'react'
import api from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { currency, dateTime, download, periodLabel } from '../../lib/format'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Table } from '../../components/ui'

const STATUS_TONE = { Generated: 'amber', Locked: 'blue', Credited: 'green' }

export default function PayrollAdmin() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'Admin'
  const [list, setList] = useState([])
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [status, setStatus] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [breakdown, setBreakdown] = useState(null)
  const [active, setActive] = useState(null)
  const [adjustment, setAdjustment] = useState({ label: '', kind: 'Bonus', amount: '', reason: '' })

  const load = () => api.get('/payroll', { params: { month, year, status: status || undefined } })
    .then((r) => setList(r.data)).catch(console.error)

  useEffect(() => { load() }, [month, year, status])

  const run = async (fn, okMessage) => {
    setBusy(true)
    setError('')
    try {
      await fn()
      if (okMessage) setMsg(okMessage)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  const openBreakdown = async (row) => {
    setActive(row)
    setAdjustment({ label: '', kind: 'Bonus', amount: '', reason: '' })
    const r = await api.get(`/payroll/${row.id}/breakdown`)
    setBreakdown(r.data)
  }

  const addAdjustment = async () => {
    if (!active) return
    try {
      const r = await api.post(`/payroll/${active.id}/adjustments`, {
        label: adjustment.label,
        kind: adjustment.kind,
        amount: Number(adjustment.amount),
        reason: adjustment.reason || null,
      })
      setBreakdown(r.data)
      setAdjustment({ label: '', kind: 'Bonus', amount: '', reason: '' })
      setMsg('Adjustment applied and the payslip totals were recalculated')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not apply adjustment')
    }
  }

  const removeAdjustment = async (id) => {
    try {
      const r = await api.delete(`/payroll/${active.id}/adjustments/${id}`)
      setBreakdown(r.data)
      setMsg('Adjustment removed')
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not remove adjustment')
    }
  }

  const slip = (id, code, m, y) => {
    api.get(`/payroll/${id}/slip`, { responseType: 'blob' })
      .then((r) => download(r.data, `salary_slip_${code || id}_${m}_${y}.pdf`))
  }

  const exportCsv = () => {
    api.get('/reports/payroll/export', { params: { month, year }, responseType: 'blob' })
      .then((r) => download(r.data, `payroll_${year}_${month}.csv`))
  }

  const totals = list.reduce((acc, p) => ({
    gross: acc.gross + Number(p.gross_earnings || 0),
    deductions: acc.deductions + Number(p.total_deductions || 0),
    net: acc.net + Number(p.net_salary || 0),
  }), { gross: 0, deductions: 0, net: 0 })

  const columns = [
    { key: 'employee_code', label: 'Code' },
    { key: 'employee_name', label: 'Employee', render: (p) => <span className="font-medium">{p.employee_name}</span> },
    { key: 'working_days', label: 'Days', render: (p) => `${p.present_days ?? 0}/${p.working_days ?? 0}` },
    { key: 'holiday_days', label: 'Holidays' },
    { key: 'lop_days', label: 'LOP', render: (p) => Number(p.lop_days) > 0 ? <Badge tone="red">{p.lop_days}</Badge> : '0' },
    { key: 'overtime_hours', label: 'OT', render: (p) => Number(p.overtime_hours) > 0 ? <Badge tone="blue">{Number(p.overtime_hours).toFixed(2)} h</Badge> : '-' },
    { key: 'gross_earnings', label: 'Gross', render: (p) => currency(p.gross_earnings) },
    { key: 'total_deductions', label: 'Deductions', render: (p) => currency(p.total_deductions) },
    { key: 'net_salary', label: 'Net', render: (p) => <span className="font-semibold">{currency(p.net_salary)}</span> },
    { key: 'status', label: 'Status', render: (p) => <Badge tone={STATUS_TONE[p.status] || 'slate'}>{p.status}</Badge> },
    {
      key: 'actions', label: 'Actions', render: (p) => (
        <div className="flex flex-wrap gap-3 text-xs font-medium">
          <button className="text-primary-600 hover:underline" onClick={() => openBreakdown(p)}>Breakdown</button>
          <button className="text-slate-600 hover:underline" onClick={() => slip(p.id, p.employee_code, p.month, p.year)}>PDF</button>
          {p.status !== 'Locked' && p.status !== 'Credited' && (
            <button className="text-slate-600 hover:underline" disabled={busy}
              onClick={() => run(() => api.post(`/payroll/${p.id}/lock`), 'Payroll locked')}>Lock</button>
          )}
          {p.status === 'Locked' && (
            <button className="text-slate-600 hover:underline" disabled={busy}
              onClick={() => run(() => api.post(`/payroll/${p.id}/credit`), 'Salary credited (simulated)')}>Credit</button>
          )}
          {p.status === 'Locked' && isAdmin && (
            <button className="text-amber-600 hover:underline" disabled={busy}
              onClick={() => run(() => api.post(`/payroll/${p.id}/unlock`), 'Payroll unlocked')}>Unlock</button>
          )}
          {p.status !== 'Locked' && p.status !== 'Credited' && (
            <button className="text-slate-600 hover:underline" disabled={busy}
              onClick={() => run(() => api.post(`/payroll/${p.id}/recalculate`), 'Payslip recalculated')}>Recalculate</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageTitle
        title="Payroll"
        subtitle={`${list.length} payslips for ${periodLabel(month, year)}`}
        actions={<>
          <Field label="Month">
            <Input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} />
          </Field>
          <Field label="Year">
            <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
          </Field>
          <Field label="Status">
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="Generated">Generated</option>
              <option value="Locked">Locked</option>
              <option value="Credited">Credited</option>
            </Select>
          </Field>
          <Button variant="ghost" onClick={exportCsv}>Export CSV</Button>
          <Button disabled={busy} onClick={() => run(() => api.post('/payroll/generate', { month, year }), 'Payroll generated')}>
            Generate payroll
          </Button>
        </>}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && <Alert tone="red">{error}</Alert>}

      {list.length > 0 && (
        <div className="grid sm:grid-cols-3 gap-4 mb-5">
          <Card className="p-4"><p className="text-sm text-slate-500">Gross earnings</p><p className="text-xl font-bold">{currency(totals.gross)}</p></Card>
          <Card className="p-4"><p className="text-sm text-slate-500">Total deductions</p><p className="text-xl font-bold">{currency(totals.deductions)}</p></Card>
          <Card className="p-4"><p className="text-sm text-slate-500">Net payable</p><p className="text-xl font-bold">{currency(totals.net)}</p></Card>
        </div>
      )}

      <Table columns={columns} rows={list} empty={`No payroll generated for ${periodLabel(month, year)}`} />

      <Modal
        open={!!breakdown}
        title={active ? `Payslip breakdown — ${active.employee_name} (${periodLabel(active.month, active.year)})` : ''}
        onClose={() => { setBreakdown(null); setActive(null) }}
        wide
        footer={<Button variant="ghost" onClick={() => { setBreakdown(null); setActive(null) }}>Close</Button>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        {breakdown && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Stat label="Working days" value={breakdown.working_days} />
              <Stat label="Holidays" value={breakdown.holiday_days} />
              <Stat label="Present" value={breakdown.present_days} />
              <Stat label="Paid leave" value={breakdown.paid_leave_days} />
              <Stat label="LOP days" value={breakdown.lop_days} />
              <Stat label="Overtime" value={`${Number(breakdown.overtime_hours).toFixed(2)} h`} />
              <Stat label="Status" value={breakdown.status} />
              <Stat label="Net salary" value={currency(breakdown.net_salary)} />
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Earnings ({currency(breakdown.gross_earnings)})</h4>
                <ul className="text-sm space-y-1">
                  {breakdown.earnings.map((line) => (
                    <li key={line.id} className="flex items-center gap-2">
                      <span>{line.name}</span>
                      <Badge tone={line.source === 'Structure' ? 'slate' : 'blue'}>{line.source}</Badge>
                      <span className="ml-auto font-medium text-green-700">{currency(line.amount)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Deductions ({currency(breakdown.total_deductions)})</h4>
                <ul className="text-sm space-y-1">
                  {breakdown.deductions.map((line) => (
                    <li key={line.id} className="flex items-center gap-2">
                      <span>{line.name}</span>
                      <Badge tone={line.source === 'Structure' ? 'slate' : 'blue'}>{line.source}</Badge>
                      <span className="ml-auto font-medium text-red-600">{currency(line.amount)}</span>
                    </li>
                  ))}
                  {breakdown.deductions.length === 0 && <li className="text-slate-400">No deductions</li>}
                </ul>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Apply an adjustment</h4>
              <div className="grid sm:grid-cols-4 gap-3 items-end">
                <Field label="Label">
                  <Input value={adjustment.label} onChange={(e) => setAdjustment({ ...adjustment, label: e.target.value })} />
                </Field>
                <Field label="Kind">
                  <Select value={adjustment.kind} onChange={(e) => setAdjustment({ ...adjustment, kind: e.target.value })}>
                    <option value="Bonus">Bonus (earning)</option>
                    <option value="Deduction">Deduction</option>
                  </Select>
                </Field>
                <Field label="Amount">
                  <Input type="number" value={adjustment.amount} onChange={(e) => setAdjustment({ ...adjustment, amount: e.target.value })} />
                </Field>
                <Button onClick={addAdjustment} disabled={!adjustment.label || !adjustment.amount}>Add</Button>
              </div>
              <ul className="text-sm mt-3 space-y-1">
                {[...breakdown.earnings, ...breakdown.deductions].filter((l) => l.source === 'Adjustment').map((line) => (
                  <li key={line.id} className="flex items-center gap-2">
                    <Badge tone={line.component_type === 'Earning' ? 'green' : 'red'}>{line.component_type}</Badge>
                    <span>{line.name}</span>
                    <span className="ml-auto font-medium">{currency(line.amount)}</span>
                    <button className="text-red-500 text-xs hover:underline ml-2" onClick={() => removeAdjustment(line.id)}>Remove</button>
                  </li>
                ))}
                {[...breakdown.earnings, ...breakdown.deductions].filter((l) => l.source === 'Adjustment').length === 0 && (
                  <li className="text-slate-400 text-xs">No manual adjustments on this payslip</li>
                )}
              </ul>
            </div>

            <p className="text-xs text-slate-400">
              Locked {active?.locked_at ? dateTime(active.locked_at) : '—'} · payroll must be unlocked before adjustments or recalculation.
            </p>
          </>
        )}
      </Modal>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}
