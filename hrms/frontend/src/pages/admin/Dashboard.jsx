import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import { currency, currentMonth, currentYear, dateStr, periodLabel } from '../../lib/format'
import { Badge, Button, Card, Field, Input, PageTitle, Select, Spinner, StatCard, Table } from '../../components/ui'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  const [month, setMonth] = useState(currentMonth())
  const [year, setYear] = useState(currentYear())
  const [shifts, setShifts] = useState(null)

  useEffect(() => {
    api.get('/reports/dashboard').then((r) => setData(r.data)).catch(console.error)
  }, [])

  useEffect(() => {
    api.get('/reports/shifts/summary', { params: { month, year } }).then((r) => setShifts(r.data)).catch(console.error)
  }, [month, year])

  if (!data) return <Spinner />

  return (
    <div>
      <PageTitle
        title="Dashboard"
        subtitle="Live workforce, attendance and payroll health"
        actions={<Link to="/admin/reports" className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50">
          Reports & exports
        </Link>}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <StatCard label="Total employees" value={data.total_employees} tone="bg-blue-500" />
        <StatCard label="Present today" value={data.present_today} tone="bg-green-500"
          hint={`${data.absent_today} not marked`} />
        <StatCard label="Late today" value={data.late_today} tone="bg-red-500"
          hint={`${data.overtime_hours_month} h overtime this month`} />
        <StatCard label="Pending leaves" value={data.pending_leaves} tone="bg-amber-500" />
        <StatCard label={`Payroll ${periodLabel(currentMonth(), currentYear())}`}
          value={data.payroll_generated_this_month} tone="bg-purple-500"
          hint={`${data.payroll_locked_this_month} locked`} />
        <StatCard label="Monthly payroll cost" value={currency(data.monthly_payroll_cost)} tone="bg-indigo-500" />
        <StatCard label="Active shifts" value={data.active_shifts} tone="bg-cyan-600" />
        <StatCard label="Holidays this month" value={data.holidays_this_month} tone="bg-rose-500"
          hint={data.upcoming_holiday ? `Next: ${data.upcoming_holiday.name} on ${dateStr(data.upcoming_holiday.date)}` : 'None upcoming'} />
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <h3 className="font-semibold mb-3">Employees by department</h3>
          <div className="space-y-2">
            {data.departments?.map((d) => (
              <div key={d.name} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                <span>{d.name}</span>
                <span className="bg-primary-50 text-primary-700 px-3 py-0.5 rounded-full text-sm font-medium">{d.count}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <h3 className="font-semibold mr-auto">Shift coverage</h3>
            <Field label="Month">
              <Input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} />
            </Field>
            <Field label="Year">
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </Field>
          </div>
          {!shifts ? <Spinner /> : (
            <>
              <Table
                columns={[
                  { key: 'shift_name', label: 'Shift', render: (s) => <span className="font-medium">{s.shift_name}</span> },
                  { key: 'timing', label: 'Timing' },
                  { key: 'assigned_employees', label: 'Staff' },
                  { key: 'late', label: 'Late', render: (s) => (s.late ? <Badge tone="red">{s.late}</Badge> : '0') },
                  { key: 'overtime_hours', label: 'OT (h)' },
                ]}
                rows={shifts.by_shift}
                rowKey={(s) => s.shift_id}
                empty="No shifts configured"
              />
              {shifts.employees_without_shift.length > 0 && (
                <p className="text-xs text-amber-700 mt-3">
                  {shifts.employees_without_shift.length} employee(s) without a shift: {shifts.employees_without_shift.join(', ')}
                </p>
              )}
            </>
          )}
        </Card>
      </div>

      <Card className="p-5 mt-5">
        <h3 className="font-semibold mb-3">Quick actions</h3>
        <div className="flex flex-wrap gap-3">
          {[
            ['/admin/payroll', 'Generate payroll'],
            ['/admin/compensation', 'Revise compensation'],
            ['/admin/shifts', 'Manage shifts'],
            ['/admin/holidays', 'Manage holidays'],
            ['/admin/calendar', 'Company calendar'],
            ['/admin/notifications', 'Notification centre'],
          ].map(([to, label]) => (
            <Link key={to} to={to} className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-700 hover:bg-slate-50">
              {label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  )
}
