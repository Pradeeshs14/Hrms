import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmpProfile() {
  const [p, setP] = useState(null)
  useEffect(() => {
    api.get('/employees/me').then(r => setP(r.data)).catch(console.error)
  }, [])
  if (!p) return <div>Loading...</div>
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">My Profile</h2>
      <div className="bg-white border rounded-xl p-6 max-w-lg space-y-3 text-sm">
        {[
          ['Employee Code', p.employee_code],
          ['Name', `${p.first_name} ${p.last_name}`],
          ['Email', p.email],
          ['Department', p.department],
          ['Designation', p.designation],
          ['Joining Date', p.joining_date],
          ['Phone', p.phone],
          ['Address', p.address],
          ['Basic Salary', `₹${Number(p.basic_salary).toLocaleString()}`],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-slate-50 pb-2">
            <span className="text-slate-500">{k}</span>
            <span className="font-medium">{v || '-'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
