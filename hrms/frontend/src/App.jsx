import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import AdminLayout from './pages/admin/Layout'
import EmployeeLayout from './pages/employee/Layout'
import AdminDashboard from './pages/admin/Dashboard'
import EmployeesPage from './pages/admin/Employees'
import AttendanceAdmin from './pages/admin/Attendance'
import LeaveAdmin from './pages/admin/Leave'
import PayrollAdmin from './pages/admin/Payroll'
import ReportsPage from './pages/admin/Reports'
import EmpDashboard from './pages/employee/Dashboard'
import EmpAttendance from './pages/employee/Attendance'
import EmpLeave from './pages/employee/Leave'
import EmpPayroll from './pages/employee/Payroll'
import EmpProfile from './pages/employee/Profile'

function PrivateRoute({ children, roles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={user.role === 'Employee' ? '/employee' : '/admin'} replace />
  }
  return children
}

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.role === 'Employee' ? '/employee' : '/admin'} /> : <Login />} />
      <Route path="/admin" element={<PrivateRoute roles={['Admin', 'HR']}><AdminLayout /></PrivateRoute>}>
        <Route index element={<AdminDashboard />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="attendance" element={<AttendanceAdmin />} />
        <Route path="leave" element={<LeaveAdmin />} />
        <Route path="payroll" element={<PayrollAdmin />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
      <Route path="/employee" element={<PrivateRoute roles={['Employee', 'Admin', 'HR']}><EmployeeLayout /></PrivateRoute>}>
        <Route index element={<EmpDashboard />} />
        <Route path="attendance" element={<EmpAttendance />} />
        <Route path="leave" element={<EmpLeave />} />
        <Route path="payroll" element={<EmpPayroll />} />
        <Route path="profile" element={<EmpProfile />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? (user.role === 'Employee' ? '/employee' : '/admin') : '/login'} />} />
    </Routes>
  )
}
