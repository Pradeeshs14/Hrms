export default function ReportsPage() {
  const year = new Date().getFullYear()
  const month = new Date().getMonth() + 1
  const token = localStorage.getItem('access_token')
  const base = 'http://localhost:8000/api/reports'

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Reports & Export</h2>
      <div className="grid gap-4 max-w-lg">
        <a href={`${base}/attendance/export?month=${month}&year=${year}`}
          className="block bg-white border rounded-xl p-5 hover:border-primary-400 transition"
          onClick={(e) => {
            e.preventDefault()
            fetch(`${base}/attendance/export?month=${month}&year=${year}`, { headers: { Authorization: `Bearer ${token}` } })
              .then(r => r.blob()).then(b => {
                const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `attendance_${year}_${month}.csv`; a.click()
              })
          }}>
          <h3 className="font-semibold">Attendance Report (CSV)</h3>
          <p className="text-sm text-slate-500 mt-1">Export attendance for current month</p>
        </a>
        <a href="#"
          className="block bg-white border rounded-xl p-5 hover:border-primary-400 transition"
          onClick={(e) => {
            e.preventDefault()
            fetch(`${base}/leave/export?year=${year}`, { headers: { Authorization: `Bearer ${token}` } })
              .then(r => r.blob()).then(b => {
                const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'leave_report.csv'; a.click()
              })
          }}>
          <h3 className="font-semibold">Leave Report (CSV)</h3>
          <p className="text-sm text-slate-500 mt-1">Export all leave requests for current year</p>
        </a>
        <a href="#"
          className="block bg-white border rounded-xl p-5 hover:border-primary-400 transition"
          onClick={(e) => {
            e.preventDefault()
            fetch(`${base}/payroll/export?month=${month}&year=${year}`, { headers: { Authorization: `Bearer ${token}` } })
              .then(r => r.blob()).then(b => {
                const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `payroll_${year}_${month}.csv`; a.click()
              })
          }}>
          <h3 className="font-semibold">Payroll Summary (CSV)</h3>
          <p className="text-sm text-slate-500 mt-1">Export payroll for current month</p>
        </a>
      </div>
    </div>
  )
}
