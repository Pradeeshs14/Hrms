import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function AttendanceAdmin() {
  const [list, setList] = useState([])
  useEffect(() => {
    api.get('/attendance/today').then(r => setList(r.data)).catch(console.error)
  }, [])
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Today's Attendance</h2>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Check In</th>
              <th className="px-4 py-3">Check Out</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">No attendance records for today</td></tr>}
            {list.map(a => (
              <tr key={a.id} className="border-t">
                <td className="px-4 py-3">{a.employee_name}</td>
                <td className="px-4 py-3">{a.check_in ? new Date(a.check_in).toLocaleTimeString() : '-'}</td>
                <td className="px-4 py-3">{a.check_out ? new Date(a.check_out).toLocaleTimeString() : '-'}</td>
                <td className="px-4 py-3">{a.working_hours ?? '-'}</td>
                <td className="px-4 py-3"><span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full text-xs">{a.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
