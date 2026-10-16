import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Badge } from './ui'
import { dateTime } from '../lib/format'

const CATEGORY_TONE = {
  Leave: 'amber',
  Payroll: 'green',
  Attendance: 'red',
  Announcement: 'purple',
  Holiday: 'blue',
  Shift: 'blue',
}

export default function NotificationBell({ dark = false }) {
  const { user } = useAuth()
  const inbox = user?.role === 'Employee' ? '/employee/notifications' : '/admin/notifications'
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)
  const boxRef = useRef(null)

  const load = () => {
    api.get('/notifications', { params: { limit: 8 } }).then((r) => setItems(r.data)).catch(console.error)
    api.get('/notifications/unread-count').then((r) => setUnread(r.data.unread)).catch(console.error)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 30000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const onClick = (event) => {
      if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read`)
    load()
  }

  const markAll = async () => {
    await api.post('/notifications/read-all')
    load()
  }

  return (
    <div className="relative" ref={boxRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        className={`relative p-2 rounded-lg ${dark ? 'text-primary-100 hover:bg-primary-800' : 'text-slate-600 hover:bg-slate-100'}`}
      >
        <span className="text-lg leading-none">🔔</span>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white text-slate-800 rounded-xl shadow-xl border border-slate-200 z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <span className="font-semibold text-sm">Notifications</span>
            <button onClick={markAll} className="text-xs text-primary-600 hover:underline">Mark all read</button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 && <p className="px-4 py-6 text-sm text-slate-400 text-center">Nothing yet</p>}
            {items.map((n) => (
              <button
                key={n.id}
                onClick={() => markRead(n.id)}
                className={`w-full text-left px-4 py-3 border-b border-slate-50 last:border-0 hover:bg-slate-50 ${n.is_read ? '' : 'bg-primary-50/40'}`}
              >
                <div className="flex items-center gap-2">
                  <Badge tone={CATEGORY_TONE[n.category] || 'slate'}>{n.category}</Badge>
                  {n.priority === 'High' && <Badge tone="red">High</Badge>}
                  {!n.is_read && <span className="w-2 h-2 rounded-full bg-primary-500 ml-auto" />}
                </div>
                <p className="text-sm font-medium mt-1.5">{n.title}</p>
                <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                <p className="text-[11px] text-slate-400 mt-1">{dateTime(n.created_at)}</p>
              </button>
            ))}
          </div>
          <Link
            to={inbox}
            onClick={() => setOpen(false)}
            className="block text-center text-sm text-primary-600 py-3 border-t hover:bg-slate-50 rounded-b-xl"
          >
            View notification centre
          </Link>
        </div>
      )}
    </div>
  )
}
