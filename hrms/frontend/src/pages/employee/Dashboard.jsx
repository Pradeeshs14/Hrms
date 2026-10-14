import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmpDashboard() {
  const [profile, setProfile] = useState(null)
  const [balances, setBalances] = useState([])
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.get('/employees/me').then(r => setProfile(r.data)).catch(console.error)
    api.get('/leave/balances').then(r => setBalances(r.data)).catch(console.error)
  }, [])

  const checkIn = async () => {
    try {
      await api.post('/attendance/check-in', {})
      setMsg('Checked in successfully')
    } catch (e) { setMsg(e.response?.data?.detail || 'Error') }
  }
  const checkOut = async () => {
    try {
      await api.post('/attendance/check-out')
      setMsg('Checked out successfully')
    } catch (e) { setMsg(e.response?.data?.detail || 'Error') }
  }

  if (!profile) return <div>Loading...</div>
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome, {profile.first_name}!</h2>
      {msg && <div className="mb-4 text-sm bg-blue-50 text-blue-700 px-3 py-2 rounded">{msg}</div>}
      <div className="grid sm:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border rounded-xl p-5">
          <h3 className="font-semibold mb-3">Today's Attendance</h3>
          <div className="flex gap-3">
            <button onClick={checkIn} className="flex-1 bg-green-600 text-white py-2.5 rounded-lg font-medium hover:bg-green-700">Check In</button>
            <button onClick={checkOut} className="flex-1 bg-slate-700 text-white py-2.5 rounded-lg font-medium hover:bg-slate-800">Check Out</button>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-5">
          <h3 className="font-semibold mb-3">Leave Balance</h3>
          <div className="space-y-1 text-sm">
            {balances.map(b => (
              <div key={b.id} className="flex justify-between">
                <span>{b.leave_type_name}</span>
                <span className="font-medium">{b.balance} days</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="bg-white border rounded-xl p-5">
        <h3 className="font-semibold mb-2">Profile Summary</h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div><span className="text-slate-500">Code:</span> {profile.employee_code}</div>
          <div><span className="text-slate-500">Department:</span> {profile.department}</div>
          <div><span className="text-slate-500">Designation:</span> {profile.designation}</div>
          <div><span className="text-slate-500">Joining:</span> {profile.joining_date}</div>
        </div>
      </div>
    </div>
  )
}
