import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function EmployeesPage() {
  const [list, setList] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    email: '', password: '', employee_code: '', first_name: '', last_name: '',
    department: '', designation: '', joining_date: '', basic_salary: '', hra: '0', allowances: '0'
  })
  const [msg, setMsg] = useState('')

  const load = () => api.get('/employees').then(r => setList(r.data.items)).catch(console.error)
  useEffect(() => { load() }, [])

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/employees', { ...form, basic_salary: Number(form.basic_salary), hra: Number(form.hra), allowances: Number(form.allowances) })
      setMsg('Employee created')
      setShowForm(false)
      load()
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Error')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Employees</h2>
        <button onClick={() => setShowForm(!showForm)} className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700">
          {showForm ? 'Cancel' : '+ Add Employee'}
        </button>
      </div>
      {msg && <div className="mb-4 text-sm text-green-700 bg-green-50 px-3 py-2 rounded">{msg}</div>}
      {showForm && (
        <form onSubmit={submit} className="bg-white p-5 rounded-xl border mb-6 grid grid-cols-2 gap-3">
          {['email','password','employee_code','first_name','last_name','department','designation','region','joining_date','basic_salary','hra','allowances'].map(k => (
            <div key={k}>
              <label className="text-xs text-slate-500 capitalize">{k.replace('_',' ')}</label>
              <input type={k === 'joining_date' ? 'date' : k === 'password' ? 'password' : 'text'} required={['email','password','employee_code','first_name','last_name','joining_date','basic_salary'].includes(k)}
                value={form[k]} onChange={e => setForm({...form, [k]: e.target.value})}
                className="w-full border rounded-lg px-2 py-1.5 text-sm" />
            </div>
          ))}
          <div className="col-span-2">
            <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm">Create</button>
          </div>
        </form>
      )}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Designation</th>
              <th className="px-4 py-3">Region</th>
              <th className="px-4 py-3">Salary</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map(e => (
              <tr key={e.id} className="border-t">
                <td className="px-4 py-3 font-medium">{e.employee_code}</td>
                <td className="px-4 py-3">{e.first_name} {e.last_name}</td>
                <td className="px-4 py-3">{e.department}</td>
                <td className="px-4 py-3">{e.designation}</td>
                <td className="px-4 py-3">{e.region || '-'}</td>
                <td className="px-4 py-3">₹{Number(e.basic_salary).toLocaleString()}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${e.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {e.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
