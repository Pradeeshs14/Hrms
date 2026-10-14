import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function LeaveAdmin() {
  const [list, setList] = useState([])
  const load = () => api.get('/leave/requests').then(r => setList(r.data)).catch(console.error)
  useEffect(() => { load() }, [])

  const action = async (id, status) => {
    await api.post(`/leave/requests/${id}/action`, { status })
    load()
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Leave Requests</h2>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">From</th>
              <th className="px-4 py-3">To</th>
              <th className="px-4 py-3">Days</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {list.map(r => (
              <tr key={r.id} className="border-t">
                <td className="px-4 py-3">{r.employee_name}</td>
                <td className="px-4 py-3">{r.leave_type_name}</td>
                <td className="px-4 py-3">{r.start_date}</td>
                <td className="px-4 py-3">{r.end_date}</td>
                <td className="px-4 py-3">{r.days}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    r.status === 'Approved' ? 'bg-green-100 text-green-700' :
                    r.status === 'Rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                  }`}>{r.status}</span>
                </td>
                <td className="px-4 py-3 space-x-2">
                  {r.status === 'Pending' && (
                    <>
                      <button onClick={() => action(r.id, 'Approved')} className="text-green-600 text-xs font-medium hover:underline">Approve</button>
                      <button onClick={() => action(r.id, 'Rejected')} className="text-red-600 text-xs font-medium hover:underline">Reject</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
