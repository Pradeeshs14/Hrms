import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  useEffect(() => {
    api.get('/reports/dashboard').then(r => setData(r.data)).catch(console.error)
  }, [])
  if (!data) return <div className="text-slate-500">Loading...</div>
  const cards = [
    { label: 'Total Employees', value: data.total_employees, color: 'bg-blue-500' },
    { label: 'Present Today', value: data.present_today, color: 'bg-green-500' },
    { label: 'Pending Leaves', value: data.pending_leaves, color: 'bg-amber-500' },
    { label: 'Payroll This Month', value: data.payroll_generated_this_month, color: 'bg-purple-500' },
  ]
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(c => (
          <div key={c.label} className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
            <div className={`w-10 h-10 ${c.color} rounded-lg mb-3 opacity-90`} />
            <p className="text-slate-500 text-sm">{c.label}</p>
            <p className="text-3xl font-bold mt-1">{c.value}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
        <h3 className="font-semibold mb-3">Employees by Department</h3>
        <div className="space-y-2">
          {data.departments?.map(d => (
            <div key={d.name} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
              <span>{d.name}</span>
              <span className="bg-primary-50 text-primary-700 px-3 py-0.5 rounded-full text-sm font-medium">{d.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
