import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmpAttendance() {
  const [list, setList] = useState([])
  useEffect(() => {
    api.get('/attendance/me').then(r => setList(r.data)).catch(console.error)
  }, [])
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">My Attendance History</h2>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Check In</th>
              <th className="px-4 py-3">Check Out</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map(a => (
              <tr key={a.id} className="border-t">
                <td className="px-4 py-3">{a.date}</td>
                <td className="px-4 py-3">{a.check_in ? new Date(a.check_in).toLocaleTimeString() : '-'}</td>
                <td className="px-4 py-3">{a.check_out ? new Date(a.check_out).toLocaleTimeString() : '-'}</td>
                <td className="px-4 py-3">{a.working_hours ?? '-'}</td>
                <td className="px-4 py-3">{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
