import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const links = [
  { to: '/employee', end: true, label: 'Dashboard' },
  { to: '/employee/attendance', label: 'Attendance' },
  { to: '/employee/leave', label: 'Leave' },
  { to: '/employee/payroll', label: 'Salary Slips' },
  { to: '/employee/profile', label: 'Profile' },
]

export default function EmployeeLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-primary-800 text-white">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="font-bold text-lg">HRMS Employee</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-primary-200">{user?.email}</span>
            <button onClick={() => { logout(); navigate('/login') }} className="text-sm hover:underline">Logout</button>
          </div>
        </div>
        <nav className="max-w-5xl mx-auto px-4 flex gap-1 pb-2">
          {links.map(l => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `px-3 py-1.5 rounded-lg text-sm ${isActive ? 'bg-primary-600' : 'hover:bg-primary-700'}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 max-w-5xl mx-auto w-full p-4">
        <Outlet />
      </main>
    </div>
  )
}
