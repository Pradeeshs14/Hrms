import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmpLeave() {
  const [types, setTypes] = useState([])
  const [requests, setRequests] = useState([])
  const [form, setForm] = useState({ leave_type_id: '', start_date: '', end_date: '', reason: '' })
  const [msg, setMsg] = useState('')

  const load = () => {
    api.get('/leave/types').then(r => setTypes(r.data))
    api.get('/leave/requests/me').then(r => setRequests(r.data))
  }
  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/leave/apply', { ...form, leave_type_id: Number(form.leave_type_id) })
      setMsg('Leave applied successfully')
      load()
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Error')
    }
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Leave Management</h2>
      {msg && <div className="mb-3 text-sm bg-blue-50 text-blue-700 px-3 py-2 rounded">{msg}</div>}
      <form onSubmit={submit} className="bg-white border rounded-xl p-4 mb-6 grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-500">Leave Type</label>
          <select required value={form.leave_type_id} onChange={e => setForm({...form, leave_type_id: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 text-sm">
            <option value="">Select</option>
            {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Start Date</label>
          <input type="date" required value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-500">End Date</label>
          <input type="date" required value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-500">Reason</label>
          <input value={form.reason} onChange={e => setForm({...form, reason: e.target.value})} className="w-full border rounded-lg px-2 py-1.5 text-sm" />
        </div>
        <div className="sm:col-span-2">
          <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm">Apply Leave</button>
        </div>
      </form>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">From</th>
              <th className="px-4 py-3">To</th>
              <th className="px-4 py-3">Days</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {requests.map(r => (
              <tr key={r.id} className="border-t">
                <td className="px-4 py-3">{r.leave_type_name}</td>
                <td className="px-4 py-3">{r.start_date}</td>
                <td className="px-4 py-3">{r.end_date}</td>
                <td className="px-4 py-3">{r.days}</td>
                <td className="px-4 py-3">{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
