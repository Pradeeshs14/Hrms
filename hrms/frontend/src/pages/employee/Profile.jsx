import { useEffect, useState } from 'react'
import api from '../../api/client'
import { currency, dateStr } from '../../lib/format'
import { Badge, Card, PageTitle, Spinner, StatCard } from '../../components/ui'

export default function EmpProfile() {
  const [profile, setProfile] = useState(null)
  const [shift, setShift] = useState(null)
  const [structure, setStructure] = useState(null)

  useEffect(() => {
    api.get('/employees/me').then((r) => setProfile(r.data)).catch(console.error)
    api.get('/shifts/me').then((r) => setShift(r.data)).catch(console.error)
    api.get('/compensation/me').then((r) => setStructure(r.data)).catch(console.error)
  }, [])

  if (!profile) return <Spinner />

  const details = [
    ['Employee code', profile.employee_code],
    ['Name', `${profile.first_name} ${profile.last_name}`],
    ['Email', profile.email],
    ['Department', profile.department],
    ['Designation', profile.designation],
    ['Region', profile.region],
    ['Joining date', dateStr(profile.joining_date)],
    ['Phone', profile.phone],
    ['Address', profile.address],
    ['Role', profile.role],
    ['Documents on file', (profile.documents || []).length],
  ]

  return (
    <div>
      <PageTitle title="My Profile" subtitle="Personal details, shift and salary structure" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <StatCard label="Basic pay" value={currency(profile.basic_salary)} tone="bg-primary-500" />
        <StatCard label="Monthly CTC" value={structure ? currency(structure.monthly_ctc) : '-'} tone="bg-indigo-500" />
        <StatCard label="Annual CTC" value={structure ? currency(structure.annual_ctc) : '-'} tone="bg-purple-500" />
        <StatCard label="Shift" value={shift?.shift?.code || '-'} tone="bg-cyan-600"
          hint={shift?.shift ? `${shift.shift.start_time} - ${shift.shift.end_time}` : 'Not assigned'} />
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <Card className="p-6">
          <h3 className="font-semibold mb-3">Personal details</h3>
          <div className="space-y-2 text-sm">
            {details.map(([label, value]) => (
              <div key={label} className="flex justify-between border-b border-slate-50 pb-2 last:border-0">
                <span className="text-slate-500">{label}</span>
                <span className="font-medium text-right">{value || '-'}</span>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-6">
            <h3 className="font-semibold mb-3">My shift</h3>
            {shift?.shift ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{shift.shift.name}</span>
                  {shift.shift.is_night && <Badge tone="purple">Night</Badge>}
                  {shift.shift.is_remote && <Badge tone="blue">Remote</Badge>}
                  {shift.shift.is_flexible && <Badge tone="amber">Flexible</Badge>}
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm mt-3">
                  <Info label="Timing" value={`${shift.shift.start_time} – ${shift.shift.end_time}`} />
                  <Info label="Standard hours" value={`${shift.shift.standard_hours} h`} />
                  <Info label="Grace period" value={`${shift.shift.grace_minutes} min`} />
                  <Info label="Overtime rate" value="1.5x hourly" />
                </div>
              </>
            ) : <p className="text-sm text-slate-500">No shift assigned yet — contact HR.</p>}
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-3">Salary structure</h3>
            {!structure ? <Spinner label="Loading structure..." /> : (
              <ul className="text-sm space-y-1">
                {structure.lines.map((line) => (
                  <li key={`${line.component_id}-${line.name}`} className="flex items-center gap-2">
                    <span>{line.name}</span>
                    {line.is_variable && <Badge tone="blue">Variable</Badge>}
                    {line.is_statutory && <Badge tone="amber">Statutory</Badge>}
                    <span className={`ml-auto font-medium ${line.component_type === 'Earning' ? 'text-green-700' : 'text-red-600'}`}>
                      {currency(line.amount)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

function Info({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}
