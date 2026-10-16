import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import NotificationBell from '../../components/NotificationBell'
import ThemeToggle from '../../components/ThemeToggle'

const links = [
  { to: '/admin', end: true, label: 'Dashboard' },
  { to: '/admin/employees', label: 'Employees' },
  { to: '/admin/attendance', label: 'Attendance' },
  { to: '/admin/leave', label: 'Leave' },
  { to: '/admin/shifts', label: 'Shifts' },
  { to: '/admin/holidays', label: 'Holidays' },
  { to: '/admin/calendar', label: 'Calendar' },
  { to: '/admin/payroll', label: 'Payroll' },
  { to: '/admin/compensation', label: 'Compensation' },
  { to: '/admin/reports', label: 'Reports' },
  { to: '/admin/notifications', label: 'Alerts' },
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="min-h-screen flex">
      <aside className={`${navOpen ? 'flex' : 'hidden'} lg:flex w-64 shrink-0 bg-primary-900 text-white flex-col max-h-screen overflow-y-auto`}>
        <div className="p-5 border-b border-primary-800">
          <h1 className="text-xl font-bold">HRMS Admin</h1>
          <p className="text-primary-300 text-xs mt-1 break-all">{user?.email}</p>
          <p className="text-primary-400 text-xs mt-0.5">{user?.role}</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links.map(l => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={() => setNavOpen(false)}
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

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="flex items-center gap-3 px-4 py-3 bg-white border-b lg:hidden">
          <button onClick={() => setNavOpen((v) => !v)} className="text-slate-600 text-lg" aria-label="Toggle navigation">☰</button>
          <span className="font-semibold">HRMS Admin</span>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            <NotificationBell />
          </div>
        </header>
        <main className="flex-1 overflow-auto">
          <div className="hidden lg:flex justify-end items-center gap-1 px-6 pt-4">
            <ThemeToggle />
            <NotificationBell />
          </div>
          <div className="p-4 lg:p-6 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
