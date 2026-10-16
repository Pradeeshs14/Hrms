import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currency, dateStr, download, periodLabel } from '../../lib/format'
import { Alert, Badge, Button, Card, Modal, PageTitle, Spinner, Table, Tabs } from '../../components/ui'

const STATUS_TONE = { Generated: 'amber', Locked: 'blue', Credited: 'green' }

export default function EmpPayroll() {
  const [tab, setTab] = useState('payslips')
  const [list, setList] = useState([])
  const [structure, setStructure] = useState(null)
  const [revisions, setRevisions] = useState([])
  const [breakdown, setBreakdown] = useState(null)
  const [active, setActive] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/payroll/me').then((r) => setList(r.data)).catch(console.error)
    api.get('/compensation/me').then((r) => setStructure(r.data)).catch(console.error)
    api.get('/employees/me').then((me) => {
      api.get(`/compensation/employees/${me.data.id}/revisions`).then((r) => setRevisions(r.data)).catch(console.error)
    }).catch(console.error)
  }, [])

  const openBreakdown = async (row) => {
    setError('')
    setActive(row)
    const r = await api.get(`/payroll/${row.id}/breakdown`)
    setBreakdown(r.data)
  }

  const downloadSlip = (row) => {
    api.get(`/payroll/${row.id}/slip`, { responseType: 'blob' })
      .then((r) => download(r.data, `salary_slip_${row.month}_${row.year}.pdf`))
      .catch(() => setError('Could not download the salary slip'))
  }

  const columns = [
    { key: 'period', label: 'Period', render: (p) => periodLabel(p.month, p.year) },
    { key: 'working_days', label: 'Days', render: (p) => `${p.present_days ?? 0}/${p.working_days ?? 0}` },
    { key: 'holiday_days', label: 'Holidays' },
    { key: 'lop_days', label: 'LOP' },
    { key: 'overtime_hours', label: 'OT', render: (p) => (Number(p.overtime_hours) > 0 ? `${Number(p.overtime_hours).toFixed(2)} h` : '-') },
    { key: 'gross_earnings', label: 'Gross', render: (p) => currency(p.gross_earnings) },
    { key: 'total_deductions', label: 'Deductions', render: (p) => currency(p.total_deductions) },
    { key: 'net_salary', label: 'Net', render: (p) => <span className="font-semibold">{currency(p.net_salary)}</span> },
    { key: 'status', label: 'Status', render: (p) => <Badge tone={STATUS_TONE[p.status] || 'slate'}>{p.status}</Badge> },
    {
      key: 'actions', label: 'Actions', render: (p) => (
        <div className="flex gap-3 text-xs font-medium">
          <button className="text-primary-600 hover:underline" onClick={() => openBreakdown(p)}>Breakdown</button>
          <button className="text-slate-600 hover:underline" onClick={() => downloadSlip(p)}>PDF</button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageTitle title="My Salary" subtitle="Payslip history, component breakdown and your current structure" />
      {error && <Alert tone="red">{error}</Alert>}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'payslips', label: 'Payslips' },
          { key: 'structure', label: 'My salary structure' },
        ]}
      />

      {tab === 'payslips' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
            {list.slice(0, 1).map((p) => (
              <Card key={p.id} className="p-4 col-span-2">
                <p className="text-sm text-slate-500">Latest net salary ({periodLabel(p.month, p.year)})</p>
                <p className="text-2xl font-bold">{currency(p.net_salary)}</p>
                <p className="text-xs text-slate-400 mt-1">
                  Gross {currency(p.gross_earnings)} · Deductions {currency(p.total_deductions)}
                </p>
              </Card>
            ))}
            {list.length > 1 && (
              <Card className="p-4">
                <p className="text-sm text-slate-500">Payslips</p>
                <p className="text-2xl font-bold">{list.length}</p>
              </Card>
            )}
            {list.length > 1 && (
              <Card className="p-4">
                <p className="text-sm text-slate-500">Total overtime logged</p>
                <p className="text-2xl font-bold">
                  {list.reduce((sum, p) => sum + Number(p.overtime_hours || 0), 0).toFixed(2)} h
                </p>
              </Card>
            )}
          </div>
          <Table columns={columns} rows={list} empty="No salary slips yet" />
        </>
      )}

      {tab === 'structure' && (
        <div className="grid lg:grid-cols-2 gap-5">
          <Card className="p-5">
            {!structure ? <Spinner /> : (
              <>
                <h3 className="font-semibold">Current structure</h3>
                <p className="text-xs text-slate-500 mb-4">
                  Effective {dateStr(structure.effective_from)} · source {structure.source}
                </p>
                <div className="grid grid-cols-2 gap-2 text-sm mb-4">
                  <Cell label="Basic pay" value={currency(structure.basic_salary)} />
                  <Cell label="Gross / month" value={currency(structure.gross_earnings)} />
                  <Cell label="Deductions" value={currency(structure.total_deductions)} />
                  <Cell label="Net / month" value={currency(structure.net_monthly)} />
                  <Cell label="Annual CTC" value={currency(structure.annual_ctc)} />
                </div>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Earnings</h4>
                <ul className="text-sm space-y-1 mb-4">
                  {structure.lines.filter((l) => l.component_type === 'Earning').map((l) => (
                    <li key={`${l.component_id}-${l.name}`} className="flex items-center gap-2">
                      <span>{l.name}</span>
                      {l.is_variable && <Badge tone="blue">Variable</Badge>}
                      <span className="ml-auto font-medium text-green-700">{currency(l.amount)}</span>
                    </li>
                  ))}
                </ul>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Deductions</h4>
                <ul className="text-sm space-y-1">
                  {structure.lines.filter((l) => l.component_type === 'Deduction').map((l) => (
                    <li key={`${l.component_id}-${l.name}`} className="flex items-center gap-2">
                      <span>{l.name}</span>
                      {l.is_statutory && <Badge tone="amber">Statutory</Badge>}
                      <span className="ml-auto font-medium text-red-600">{currency(l.amount)}</span>
                    </li>
                  ))}
                  {structure.lines.filter((l) => l.component_type === 'Deduction').length === 0 && (
                    <li className="text-slate-400">No deductions</li>
                  )}
                </ul>
              </>
            )}
          </Card>

          <Card className="p-5">
            <h3 className="font-semibold mb-3">Revision history</h3>
            <ul className="space-y-3 text-sm">
              {revisions.map((rev) => (
                <li key={rev.id} className="border-b border-slate-50 pb-3 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{dateStr(rev.effective_from)}</span>
                    <span className="text-slate-500">Basic {currency(rev.basic_salary)}</span>
                  </div>
                  <p className="text-xs text-slate-500">Annual CTC {currency(rev.total_ctc)}</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {rev.lines.map((line) => (
                      <Badge key={line.name} tone={line.component_type === 'Earning' ? 'green' : 'red'}>
                        {line.name}: {currency(line.amount)}
                      </Badge>
                    ))}
                  </div>
                  {rev.notes && <p className="text-xs text-slate-400 mt-1">{rev.notes}</p>}
                </li>
              ))}
              {revisions.length === 0 && <li className="text-slate-400">No revisions recorded</li>}
            </ul>
          </Card>
        </div>
      )}

      <Modal
        open={!!breakdown}
        title={active ? `Payslip — ${periodLabel(active.month, active.year)}` : ''}
        onClose={() => { setBreakdown(null); setActive(null) }}
        wide
        footer={<>
          <Button variant="ghost" onClick={() => { setBreakdown(null); setActive(null) }}>Close</Button>
          {active && <Button onClick={() => downloadSlip(active)}>Download PDF</Button>}
        </>}
      >
        {breakdown && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Cell label="Working days" value={breakdown.working_days} />
              <Cell label="Holidays" value={breakdown.holiday_days} />
              <Cell label="Present" value={breakdown.present_days} />
              <Cell label="Paid leave" value={breakdown.paid_leave_days} />
              <Cell label="LOP days" value={breakdown.lop_days} />
              <Cell label="Overtime" value={`${Number(breakdown.overtime_hours).toFixed(2)} h`} />
              <Cell label="Gross" value={currency(breakdown.gross_earnings)} />
              <Cell label="Net salary" value={currency(breakdown.net_salary)} />
            </div>
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Earnings</h4>
                <ul className="text-sm space-y-1">
                  {breakdown.earnings.map((l) => (
                    <li key={l.id} className="flex items-center gap-2">
                      <span>{l.name}</span>
                      <Badge tone={l.source === 'Structure' ? 'slate' : 'blue'}>{l.source}</Badge>
                      <span className="ml-auto font-medium text-green-700">{currency(l.amount)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Deductions</h4>
                <ul className="text-sm space-y-1">
                  {breakdown.deductions.map((l) => (
                    <li key={l.id} className="flex items-center gap-2">
                      <span>{l.name}</span>
                      <Badge tone={l.source === 'Structure' ? 'slate' : 'blue'}>{l.source}</Badge>
                      <span className="ml-auto font-medium text-red-600">{currency(l.amount)}</span>
                    </li>
                  ))}
                  {breakdown.deductions.length === 0 && <li className="text-slate-400">No deductions</li>}
                </ul>
              </div>
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}

function Cell({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}
