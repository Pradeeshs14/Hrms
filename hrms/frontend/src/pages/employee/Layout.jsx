import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import NotificationBell from '../../components/NotificationBell'
import ThemeToggle from '../../components/ThemeToggle'

const links = [
  { to: '/employee', end: true, label: 'Dashboard' },
  { to: '/employee/attendance', label: 'Attendance' },
  { to: '/employee/leave', label: 'Leave' },
  { to: '/employee/calendar', label: 'Calendar' },
  { to: '/employee/payroll', label: 'Salary' },
  { to: '/employee/notifications', label: 'Alerts' },
  { to: '/employee/profile', label: 'Profile' },
]

export default function EmployeeLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-primary-800 text-white">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <h1 className="font-bold text-lg">HRMS Employee</h1>
          <div className="flex items-center gap-3">
            <span className="text-xs text-primary-200 hidden sm:inline break-all">{user?.email}</span>
            <ThemeToggle tone="dark" />
            <NotificationBell dark />
            <button onClick={() => { logout(); navigate('/login') }} className="text-sm hover:underline">Logout</button>
          </div>
        </div>
        <nav className="max-w-5xl mx-auto px-4 flex gap-1 pb-2 overflow-x-auto">
          {links.map(l => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${isActive ? 'bg-primary-600' : 'hover:bg-primary-700'}`}>
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
