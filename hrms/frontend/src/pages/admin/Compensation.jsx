import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currency, dateStr, download, todayISO } from '../../lib/format'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Table, Tabs, Textarea } from '../../components/ui'

const EMPTY_COMPONENT = {
  name: '', code: '', component_type: 'Earning', calc_type: 'Fixed', default_value: 0,
  max_amount: '', is_taxable: true, is_statutory: false, is_variable: false,
  display_order: 10, is_active: true, description: '',
}

export default function CompensationAdmin() {
  const [tab, setTab] = useState('structures')
  const [components, setComponents] = useState([])
  const [rows, setRows] = useState([])
  const [selected, setSelected] = useState(null)
  const [structure, setStructure] = useState(null)
  const [revisions, setRevisions] = useState([])
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const [componentForm, setComponentForm] = useState(EMPTY_COMPONENT)
  const [componentEditing, setComponentEditing] = useState(null)
  const [componentOpen, setComponentOpen] = useState(false)

  const [reviseOpen, setReviseOpen] = useState(false)
  const [revise, setRevise] = useState({ effective_from: todayISO(), basic_salary: 0, notes: '', values: {} })

  const loadComponents = () => api.get('/compensation/components').then((r) => setComponents(r.data)).catch(console.error)
  const loadRows = () => api.get('/compensation/employees').then((r) => setRows(r.data)).catch(console.error)

  useEffect(() => {
    loadComponents()
    loadRows()
  }, [])

  const openStructure = (row) => {
    setSelected(row)
    api.get(`/compensation/employees/${row.employee_id}`).then((r) => setStructure(r.data)).catch(console.error)
    api.get(`/compensation/employees/${row.employee_id}/revisions`).then((r) => setRevisions(r.data)).catch(console.error)
  }

  // The component catalogue defines the default rule, but a single employee can hold a
  // fixed amount for a percentage component - keep the rule in force when re-saving.
  const ruleFor = (componentId) =>
    structure?.lines.find((l) => l.component_id === componentId)?.calc_type || 'Fixed'

  const openRevise = () => {
    if (!structure) return
    const values = {}
    structure.lines.forEach((line) => {
      if (line.name === 'Basic Pay') return
      values[line.component_id] = line.value
    })
    setRevise({ effective_from: todayISO(), basic_salary: structure.basic_salary, notes: '', values })
    setError('')
    setReviseOpen(true)
  }

  const submitRevise = async () => {
    if (!selected) return
    const lines = Object.entries(revise.values)
      .filter(([, value]) => value !== '' && value !== null)
      .map(([componentId, value]) => ({
        component_id: Number(componentId),
        value: Number(value),
        calc_type: ruleFor(Number(componentId)),
      }))
    try {
      await api.post(`/compensation/employees/${selected.employee_id}/revise`, {
        effective_from: revise.effective_from,
        basic_salary: Number(revise.basic_salary),
        notes: revise.notes || null,
        lines,
      })
      setReviseOpen(false)
      setMsg('Compensation revised and the employee was notified')
      openStructure(selected)
      loadRows()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save the revision')
    }
  }

  const saveComponent = async () => {
    try {
      const payload = {
        ...componentForm,
        default_value: Number(componentForm.default_value || 0),
        max_amount: componentForm.max_amount === '' ? null : Number(componentForm.max_amount),
        display_order: Number(componentForm.display_order || 0),
      }
      if (componentEditing) await api.put(`/compensation/components/${componentEditing}`, payload)
      else await api.post('/compensation/components', payload)
      setComponentOpen(false)
      setMsg(componentEditing ? 'Component updated' : 'Component created')
      loadComponents()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save the component')
    }
  }

  const deactivateComponent = async (id) => {
    if (!window.confirm('Deactivate this component? It will no longer be offered in new structures.')) return
    try {
      await api.delete(`/compensation/components/${id}`)
      setMsg('Component deactivated')
      loadComponents()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not deactivate component')
    }
  }

  const exportCsv = () => {
    api.get('/reports/compensation/export', { responseType: 'blob' })
      .then((r) => download(r.data, 'compensation_report.csv'))
  }

  const componentColumns = [
    { key: 'name', label: 'Component', render: (c) => <span className="font-medium">{c.name}</span> },
    { key: 'code', label: 'Code' },
    { key: 'component_type', label: 'Type', render: (c) => <Badge tone={c.component_type === 'Earning' ? 'green' : 'red'}>{c.component_type}</Badge> },
    {
      key: 'rule', label: 'Rule', render: (c) => (
        c.calc_type === 'Fixed' ? `Fixed ${currency(c.default_value)}`
          : c.calc_type === 'PercentOfBasic' ? `${Number(c.default_value)}% of basic`
            : `${Number(c.default_value)}% of gross`
      ),
    },
    { key: 'max_amount', label: 'Cap', render: (c) => (c.max_amount ? currency(c.max_amount) : <span className="text-slate-400">-</span>) },
    {
      key: 'flags', label: 'Flags', render: (c) => (
        <div className="flex flex-wrap gap-1">
          {c.is_basic && <Badge tone="purple">Basic</Badge>}
          {c.is_statutory && <Badge tone="amber">Statutory</Badge>}
          {c.is_variable && <Badge tone="blue">Variable</Badge>}
          {!c.is_active && <Badge>Inactive</Badge>}
        </div>
      ),
    },
    {
      key: 'actions', label: 'Actions', render: (c) => (
        <div className="flex gap-3 text-xs font-medium">
          <button className="text-primary-600 hover:underline" onClick={() => {
            setComponentForm({
              name: c.name, code: c.code, component_type: c.component_type, calc_type: c.calc_type,
              default_value: c.default_value, max_amount: c.max_amount ?? '', is_taxable: c.is_taxable,
              is_statutory: c.is_statutory, is_variable: c.is_variable, display_order: c.display_order,
              is_active: c.is_active, description: c.description || '',
            })
            setComponentEditing(c.id)
            setError('')
            setComponentOpen(true)
          }}>Edit</button>
          {c.is_active && !c.is_basic && (
            <button className="text-red-500 hover:underline" onClick={() => deactivateComponent(c.id)}>Deactivate</button>
          )}
        </div>
      ),
    },
  ]

  const rowColumns = [
    { key: 'employee_code', label: 'Code' },
    { key: 'employee_name', label: 'Employee', render: (r) => <span className="font-medium">{r.employee_name}</span> },
    { key: 'department', label: 'Department' },
    { key: 'basic_salary', label: 'Basic', render: (r) => currency(r.basic_salary) },
    { key: 'gross_earnings', label: 'Gross / month', render: (r) => currency(r.gross_earnings) },
    { key: 'total_deductions', label: 'Deductions', render: (r) => currency(r.total_deductions) },
    { key: 'annual_ctc', label: 'Annual CTC', render: (r) => <span className="font-medium">{currency(r.annual_ctc)}</span> },
    { key: 'effective_from', label: 'Effective' },
    {
      key: 'actions', label: '', render: (r) => (
        <button className="text-primary-600 text-xs font-medium hover:underline" onClick={() => openStructure(r)}>View / revise</button>
      ),
    },
  ]

  return (
    <div>
      <PageTitle
        title="Compensation"
        subtitle="Configure salary components and revise employee compensation with full history"
        actions={<>
          <Button variant="ghost" onClick={exportCsv}>Export CTC report</Button>
          <Button onClick={() => { setComponentForm(EMPTY_COMPONENT); setComponentEditing(null); setError(''); setComponentOpen(true) }}>
            Add component
          </Button>
        </>}
      />
      {msg && <Alert tone="green">{msg}</Alert>}
      {error && !componentOpen && !reviseOpen && <Alert tone="red">{error}</Alert>}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'structures', label: 'Employee structures' },
          { key: 'components', label: 'Salary components' },
        ]}
      />

      {tab === 'structures' && (
        <div className="grid lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <Table columns={rowColumns} rows={rows} rowKey={(r) => r.employee_id} empty="No active employees" />
          </div>
          <Card className="p-5">
            {!structure && <p className="text-sm text-slate-400">Select an employee to view the resolved structure.</p>}
            {structure && (
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{selected?.employee_name}</h3>
                    <p className="text-xs text-slate-500">
                      {structure.source} · effective {dateStr(structure.effective_from)}
                    </p>
                  </div>
                  <Button onClick={openRevise}>Revise</Button>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  <Metric label="Basic" value={currency(structure.basic_salary)} />
                  <Metric label="Gross" value={currency(structure.gross_earnings)} />
                  <Metric label="Deductions" value={currency(structure.total_deductions)} />
                  <Metric label="Net / month" value={currency(structure.net_monthly)} />
                  <Metric label="Annual CTC" value={currency(structure.annual_ctc)} />
                </div>

                <h4 className="text-xs uppercase tracking-wide text-slate-500 mt-5 mb-2">Earnings</h4>
                <LineList lines={structure.lines.filter((l) => l.component_type === 'Earning')} tone="text-green-700" />
                <h4 className="text-xs uppercase tracking-wide text-slate-500 mt-4 mb-2">Deductions</h4>
                <LineList lines={structure.lines.filter((l) => l.component_type === 'Deduction')} tone="text-red-600" />

                <h4 className="text-xs uppercase tracking-wide text-slate-500 mt-5 mb-2">Revision history</h4>
                <ul className="space-y-2 text-sm max-h-56 overflow-y-auto">
                  {revisions.map((rev) => (
                    <li key={rev.id} className="border-b border-slate-50 pb-2 last:border-0">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{rev.effective_from}</span>
                        <span className="text-slate-500">Basic {currency(rev.basic_salary)}</span>
                      </div>
                      <p className="text-xs text-slate-500">CTC {currency(rev.total_ctc)} · {rev.lines.length} components</p>
                      {rev.notes && <p className="text-xs text-slate-400">{rev.notes}</p>}
                    </li>
                  ))}
                  {revisions.length === 0 && <li className="text-slate-400">No revisions recorded</li>}
                </ul>
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === 'components' && (
        <>
          <p className="text-sm text-slate-500 mb-4">
            Components drive every payslip. Percentages are resolved against basic pay (or gross for TDS-style rules),
            and statutory caps such as the PF ceiling are applied automatically.
          </p>
          <Table columns={componentColumns} rows={components} empty="No components configured" />
        </>
      )}

      <Modal
        open={componentOpen}
        title={componentEditing ? 'Edit salary component' : 'Add salary component'}
        onClose={() => setComponentOpen(false)}
        wide
        footer={<>
          <Button variant="ghost" onClick={() => setComponentOpen(false)}>Cancel</Button>
          <Button onClick={saveComponent} disabled={!componentForm.name || !componentForm.code}>
            {componentEditing ? 'Save changes' : 'Create component'}
          </Button>
        </>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Name">
            <Input value={componentForm.name} onChange={(e) => setComponentForm({ ...componentForm, name: e.target.value })} />
          </Field>
          <Field label="Code" hint="Unique code used in payroll rules">
            <Input value={componentForm.code} disabled={!!componentEditing}
              onChange={(e) => setComponentForm({ ...componentForm, code: e.target.value.toUpperCase() })} />
          </Field>
          <Field label="Type">
            <Select value={componentForm.component_type}
              onChange={(e) => setComponentForm({ ...componentForm, component_type: e.target.value })}>
              <option value="Earning">Earning</option>
              <option value="Deduction">Deduction</option>
            </Select>
          </Field>
          <Field label="Calculation">
            <Select value={componentForm.calc_type}
              onChange={(e) => setComponentForm({ ...componentForm, calc_type: e.target.value })}>
              <option value="Fixed">Fixed amount</option>
              <option value="PercentOfBasic">Percent of basic</option>
              <option value="PercentOfGross">Percent of gross</option>
            </Select>
          </Field>
          <Field label={componentForm.calc_type === 'Fixed' ? 'Default amount' : 'Default percentage'}>
            <Input type="number" step="0.01" value={componentForm.default_value}
              onChange={(e) => setComponentForm({ ...componentForm, default_value: e.target.value })} />
          </Field>
          <Field label="Maximum amount" hint="Optional cap, e.g. 1800 for PF">
            <Input type="number" step="0.01" value={componentForm.max_amount}
              onChange={(e) => setComponentForm({ ...componentForm, max_amount: e.target.value })} />
          </Field>
          <Field label="Display order">
            <Input type="number" value={componentForm.display_order}
              onChange={(e) => setComponentForm({ ...componentForm, display_order: e.target.value })} />
          </Field>
        </div>
        <Field label="Description">
          <Textarea rows={2} value={componentForm.description}
            onChange={(e) => setComponentForm({ ...componentForm, description: e.target.value })} />
        </Field>
        <div className="flex flex-wrap gap-4 text-sm">
          {[['is_taxable', 'Taxable'], ['is_statutory', 'Statutory'], ['is_variable', 'Variable pay'], ['is_active', 'Active']].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2">
              <input type="checkbox" checked={componentForm[key]}
                onChange={(e) => setComponentForm({ ...componentForm, [key]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
      </Modal>

      <Modal
        open={reviseOpen}
        title={`Revise compensation — ${selected?.employee_name || ''}`}
        onClose={() => setReviseOpen(false)}
        wide
        footer={<>
          <Button variant="ghost" onClick={() => setReviseOpen(false)}>Cancel</Button>
          <Button onClick={submitRevise} disabled={!revise.basic_salary}>Save revision</Button>
        </>}
      >
        {error && <Alert tone="red">{error}</Alert>}
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Effective from">
            <Input type="date" value={revise.effective_from}
              onChange={(e) => setRevise({ ...revise, effective_from: e.target.value })} />
          </Field>
          <Field label="Basic pay">
            <Input type="number" value={revise.basic_salary}
              onChange={(e) => setRevise({ ...revise, basic_salary: e.target.value })} />
          </Field>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500 mb-2">Component values</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {components.filter((c) => c.is_active && !c.is_basic).map((c) => {
              const rule = ruleFor(c.id)
              return (
                <Field
                  key={c.id}
                  label={`${c.name} (${rule === 'Fixed' ? 'amount' : '%'})`}
                  hint={`${c.component_type} · ${rule}${c.max_amount ? ` · cap ${currency(c.max_amount)}` : ''}`}
                >
                  <Input
                    type="number"
                    step="0.01"
                    value={revise.values[c.id] ?? ''}
                    onChange={(e) => setRevise({ ...revise, values: { ...revise.values, [c.id]: e.target.value } })}
                  />
                </Field>
              )
            })}
          </div>
        </div>
        <Field label="Notes">
          <Textarea rows={2} value={revise.notes} onChange={(e) => setRevise({ ...revise, notes: e.target.value })} />
        </Field>
      </Modal>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}

function LineList({ lines, tone }) {
  return (
    <ul className="text-sm space-y-1">
      {lines.map((l) => (
        <li key={`${l.component_id}-${l.name}`} className="flex items-center gap-2">
          <span className="text-slate-600">{l.name}</span>
          {l.is_variable && <Badge tone="blue">Variable</Badge>}
          {l.is_statutory && <Badge tone="amber">Statutory</Badge>}
          <span className={`ml-auto font-medium ${tone}`}>{currency(l.amount)}</span>
        </li>
      ))}
      {lines.length === 0 && <li className="text-slate-400">None</li>}
    </ul>
  )
}
