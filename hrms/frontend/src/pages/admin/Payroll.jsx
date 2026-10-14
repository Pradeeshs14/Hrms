import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function PayrollAdmin() {
  const [list, setList] = useState([])
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [msg, setMsg] = useState('')

  const load = () => api.get('/payroll', { params: { month, year } }).then(r => setList(r.data)).catch(console.error)
  useEffect(() => { load() }, [month, year])

  const generate = async () => {
    setMsg('Generating...')
    try {
      await api.post('/payroll/generate', { month: Number(month), year: Number(year) })
      setMsg('Payroll generated successfully')
      load()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Error')
    }
  }

  const download = (id) => {
    const token = localStorage.getItem('access_token')
    window.open(`http://localhost:8000/api/payroll/${id}/slip?token=${token}`, '_blank')
    // better: fetch with auth
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
      <div className="flex flex-wrap gap-3 items-end mb-6">
        <h2 className="text-2xl font-bold mr-auto">Payroll</h2>
        <div>
          <label className="text-xs text-slate-500">Month</label>
          <input type="number" min={1} max={12} value={month} onChange={e => setMonth(e.target.value)} className="border rounded-lg px-2 py-1.5 text-sm w-20 block" />
        </div>
        <div>
          <label className="text-xs text-slate-500">Year</label>
          <input type="number" value={year} onChange={e => setYear(e.target.value)} className="border rounded-lg px-2 py-1.5 text-sm w-24 block" />
        </div>
        <button onClick={generate} className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700">Generate Payroll</button>
      </div>
      {msg && <div className="mb-4 text-sm bg-blue-50 text-blue-700 px-3 py-2 rounded">{msg}</div>}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Net Salary</th>
              <th className="px-4 py-3">LOP</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Slip</th>
            </tr>
          </thead>
          <tbody>
            {list.map(p => (
              <tr key={p.id} className="border-t">
                <td className="px-4 py-3">{p.employee_code}</td>
                <td className="px-4 py-3">{p.employee_name}</td>
                <td className="px-4 py-3 font-medium">₹{Number(p.net_salary).toLocaleString()}</td>
                <td className="px-4 py-3">{p.lop_days}</td>
                <td className="px-4 py-3"><span className="bg-slate-100 px-2 py-0.5 rounded-full text-xs">{p.status}</span></td>
                <td className="px-4 py-3">
                  <button onClick={() => download(p.id)} className="text-primary-600 text-xs font-medium hover:underline">Download PDF</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
