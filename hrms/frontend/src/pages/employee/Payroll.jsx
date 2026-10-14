import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmpPayroll() {
  const [list, setList] = useState([])
  useEffect(() => {
    api.get('/payroll/me').then(r => setList(r.data)).catch(console.error)
  }, [])

  const download = (id) => {
    api.get(`/payroll/${id}/slip`, { responseType: 'blob' }).then(r => {
      const url = window.URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `salary_slip_${id}.pdf`
      a.click()
    })
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">My Salary Slips</h2>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Month</th>
              <th className="px-4 py-3">Year</th>
              <th className="px-4 py-3">Net Salary</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Download</th>
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">No salary slips yet</td></tr>}
            {list.map(p => (
              <tr key={p.id} className="border-t">
                <td className="px-4 py-3">{p.month}</td>
                <td className="px-4 py-3">{p.year}</td>
                <td className="px-4 py-3 font-medium">₹{Number(p.net_salary).toLocaleString()}</td>
                <td className="px-4 py-3">{p.status}</td>
                <td className="px-4 py-3">
                  <button onClick={() => download(p.id)} className="text-primary-600 text-xs font-medium hover:underline">PDF</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
