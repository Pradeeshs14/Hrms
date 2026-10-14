import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const links = [
  { to: '/admin', end: true, label: 'Dashboard' },
  { to: '/admin/employees', label: 'Employees' },
  { to: '/admin/attendance', label: 'Attendance' },
  { to: '/admin/leave', label: 'Leave' },
  { to: '/admin/payroll', label: 'Payroll' },
  { to: '/admin/reports', label: 'Reports' },
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-primary-900 text-white flex flex-col">
        <div className="p-5 border-b border-primary-800">
          <h1 className="text-xl font-bold">HRMS Admin</h1>
          <p className="text-primary-300 text-sm mt-1">{user?.email}</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links.map(l => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `block px-4 py-2.5 rounded-lg text-sm font-medium transition ${isActive ? 'bg-primary-700 text-white' : 'text-primary-200 hover:bg-primary-800'}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-primary-800">
          <button onClick={() => { logout(); navigate('/login') }}
            className="w-full text-left px-4 py-2 text-sm text-primary-200 hover:text-white">Logout</button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
