import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currentMonth, currentYear, download, periodLabel } from '../../lib/format'
import { Alert, Card, Field, Input, PageTitle, Select, Spinner, Table } from '../../components/ui'

export default function ReportsPage() {
  const [month, setMonth] = useState(currentMonth())
  const [year, setYear] = useState(currentYear())
  const [msg, setMsg] = useState('')
  const [shifts, setShifts] = useState(null)

  useEffect(() => {
    api.get('/reports/shifts/summary', { params: { month, year } })
      .then((r) => setShifts(r.data)).catch(console.error)
  }, [month, year])

  const grab = (path, params, filename) => {
    setMsg('')
    api.get(path, { params, responseType: 'blob' })
      .then((r) => download(r.data, filename))
      .catch(() => setMsg('Export failed'))
  }

  const reports = [
    {
      title: 'Attendance report (CSV)',
      description: 'Shift, late minutes, early exits and overtime per check-in record',
      run: () => grab('/reports/attendance/export', { month, year }, `attendance_${year}_${month}.csv`),
    },
    {
      title: 'Leave report (CSV)',
      description: 'Working-day leave with paid/unpaid classification',
      run: () => grab('/reports/leave/export', { year }, 'leave_report.csv'),
    },
    {
      title: 'Payroll report (CSV)',
      description: 'Component-level earnings, statutory deductions, LOP and overtime',
      run: () => grab('/reports/payroll/export', { month, year }, `payroll_${year}_${month}.csv`),
    },
    {
      title: 'Shift-wise attendance (CSV)',
      description: 'Attendance grouped by shift with late and overtime totals',
      run: () => grab('/shifts/reports/attendance/export', { month, year }, `shift_attendance_${year}_${month}.csv`),
    },
    {
      title: 'Holiday list (CSV)',
      description: 'Company, regional and optional holidays for the year',
      run: () => grab('/reports/holidays/export', { year }, `holidays_${year}.csv`),
    },
    {
      title: 'Compensation report (CSV)',
      description: 'Latest structure, gross, deductions and annual CTC per employee',
      run: () => grab('/reports/compensation/export', {}, 'compensation_report.csv'),
    },
  ]

  return (
    <div>
      <PageTitle
        title="Reports & Export"
        subtitle={`Exports reflect the same figures shown on screen for ${periodLabel(month, year)}`}
        actions={<>
          <Field label="Month">
            <Input type="number" min={1} max={12} value={month} onChange={(e) => setMonth(Number(e.target.value))} />
          </Field>
          <Field label="Year">
            <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
          </Field>
        </>}
      />
      {msg && <Alert tone="red">{msg}</Alert>}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {reports.map((report) => (
          <button
            key={report.title}
            onClick={report.run}
            className="text-left bg-white border border-slate-200 rounded-xl p-5 hover:border-primary-400 transition"
          >
            <h3 className="font-semibold">{report.title}</h3>
            <p className="text-sm text-slate-500 mt-1">{report.description}</p>
          </button>
        ))}
      </div>

      <h3 className="font-semibold mb-3">Shift headcount & attendance health</h3>
      {!shifts ? <Spinner /> : (
        <>
          <Table
            columns={[
              { key: 'shift_name', label: 'Shift', render: (s) => <span className="font-medium">{s.shift_name}</span> },
              { key: 'timing', label: 'Timing' },
              { key: 'assigned_employees', label: 'Assigned staff' },
              { key: 'records', label: 'Records' },
              { key: 'present', label: 'Present' },
              { key: 'late', label: 'Late' },
              { key: 'early_exits', label: 'Early exits' },
              { key: 'overtime_hours', label: 'Overtime (h)' },
              { key: 'total_hours', label: 'Hours logged' },
            ]}
            rows={shifts.by_shift}
            rowKey={(s) => s.shift_id}
            empty="No shifts configured"
          />
          {shifts.employees_without_shift.length > 0 && (
            <Card className="p-4 mt-4 text-sm text-amber-800 bg-amber-50 border-amber-200">
              Employees without a shift: {shifts.employees_without_shift.join(', ')}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
