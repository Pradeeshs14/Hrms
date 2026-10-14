import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('admin@gmail.com')
  const [password, setPassword] = useState('Admin@123')
  const [error, setError] = useState('')
  const { login, loading } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const u = await login(email, password)
      navigate(u.role === 'Employee' ? '/employee' : '/admin')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-800 to-primary-600 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-800">HRMS</h1>
          <p className="text-slate-500 mt-1">Human Resource Management System</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-2.5 rounded-lg transition disabled:opacity-50">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="mt-6 text-xs text-slate-500 bg-slate-50 rounded-lg p-3">
          <p className="font-semibold mb-1">Demo accounts:</p>
          <p>Admin: admin@gmail.com / Admin@123</p>
          <p>HR: hr@gmail.com / Hr@12345</p>
          <p>Employees: abi / pradeesh / linga / rohith / sugan @gmail.com / Emp@12345</p>
        </div>
      </div>
    </div>
  )
}
