import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Badge, Button, Card, Field, Input, Modal, PageTitle, Select, Spinner, Tabs, Textarea } from '../components/ui'
import { dateTime } from '../lib/format'

const CATEGORY_TONE = {
  Leave: 'amber',
  Payroll: 'green',
  Attendance: 'red',
  Announcement: 'purple',
  Holiday: 'blue',
  Shift: 'blue',
}

export default function NotificationsPage() {
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState('inbox')
  const [items, setItems] = useState([])
  const [filter, setFilter] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [counts, setCounts] = useState({ unread: 0, total: 0 })
  const [preferences, setPreferences] = useState([])
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [broadcastOpen, setBroadcastOpen] = useState(false)
  const [departments, setDepartments] = useState([])
  const [form, setForm] = useState({ title: '', message: '', department: '', priority: 'Normal' })

  const loadInbox = () => {
    const params = { limit: 100 }
    if (unreadOnly) params.unread_only = true
    if (filter) params.category = filter
    return Promise.all([
      api.get('/notifications', { params }),
      api.get('/notifications/unread-count'),
    ]).then(([list, count]) => {
      setItems(list.data)
      setCounts(count.data)
    })
  }

  useEffect(() => {
    setLoading(true)
    loadInbox().catch(console.error).finally(() => setLoading(false))
  }, [filter, unreadOnly])

  useEffect(() => {
    api.get('/notifications/preferences').then((r) => setPreferences(r.data)).catch(console.error)
    if (isAdmin) {
      api.get('/reports/dashboard').then((r) => setDepartments(r.data.departments || [])).catch(console.error)
    }
  }, [isAdmin])

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read`)
    loadInbox()
  }

  const markAllRead = async () => {
    const r = await api.post('/notifications/read-all')
    setMsg(r.data.message)
    loadInbox()
  }

  const remove = async (id) => {
    await api.delete(`/notifications/${id}`)
    loadInbox()
  }

  const togglePreference = async (category, enabled) => {
    const r = await api.put('/notifications/preferences', { preferences: [{ category, enabled }] })
    setPreferences(r.data)
  }

  const sendBroadcast = async () => {
    try {
      const payload = { ...form, department: form.department || null }
      const r = await api.post('/notifications/broadcast', payload)
      setMsg(`Announcement delivered to ${r.data.recipients} recipient(s)`)
      setBroadcastOpen(false)
      setForm({ title: '', message: '', department: '', priority: 'Normal' })
      loadInbox()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Broadcast failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Notification Centre"
        subtitle={`${counts.unread} unread of ${counts.total} notifications`}
        actions={isAdmin && (
          <Button onClick={() => setBroadcastOpen(true)}>Send announcement</Button>
        )}
      />
      <Alert>{msg}</Alert>

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'inbox', label: 'Inbox' },
          { key: 'preferences', label: 'Preferences' },
        ]}
      />

      {tab === 'inbox' && (
        <>
          <div className="flex flex-wrap gap-3 items-end mb-4">
            <Field label="Category">
              <Select value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="">All categories</option>
                {['Leave', 'Payroll', 'Attendance', 'Announcement', 'Holiday', 'Shift', 'System'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </Field>
            <label className="flex items-center gap-2 text-sm pb-2">
              <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
              Unread only
            </label>
            <Button variant="ghost" className="mb-0.5" onClick={markAllRead}>Mark all as read</Button>
          </div>

          {loading ? <Spinner /> : (
            <div className="space-y-2">
              {items.length === 0 && (
                <Card className="p-8 text-center text-slate-400 text-sm">No notifications match this filter</Card>
              )}
              {items.map((n) => (
                <Card key={n.id} className={`p-4 ${n.is_read ? '' : 'border-l-4 border-l-primary-500'}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={CATEGORY_TONE[n.category] || 'slate'}>{n.category}</Badge>
                    {n.priority === 'High' && <Badge tone="red">High priority</Badge>}
                    {!n.is_read && <Badge tone="blue">Unread</Badge>}
                    <span className="ml-auto text-xs text-slate-400">{dateTime(n.created_at)}</span>
                  </div>
                  <p className="font-semibold mt-2">{n.title}</p>
                  <p className="text-sm text-slate-600 mt-1">{n.message}</p>
                  <div className="flex flex-wrap gap-3 mt-3 text-xs font-medium">
                    {!n.is_read && (
                      <button onClick={() => markRead(n.id)} className="text-primary-600 hover:underline">Mark read</button>
                    )}
                    {n.link && <Link to={n.link} className="text-slate-500 hover:underline">Open</Link>}
                    <button onClick={() => remove(n.id)} className="text-red-500 hover:underline">Delete</button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'preferences' && (
        <Card className="p-5 max-w-2xl">
          <h3 className="font-semibold">Alert preferences</h3>
          <p className="text-sm text-slate-500 mt-1">
            Choose which in-app notifications you want to receive. Announcements from Admin/HR are always delivered.
          </p>
          <div className="mt-4 divide-y divide-slate-100">
            {preferences.map((p) => (
              <div key={p.category} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-sm">{p.category}</p>
                  {p.mandatory && <p className="text-xs text-slate-400">Mandatory - cannot be disabled</p>}
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    disabled={p.mandatory}
                    checked={p.enabled}
                    onChange={(e) => togglePreference(p.category, e.target.checked)}
                  />
                  {p.enabled ? 'Enabled' : 'Disabled'}
                </label>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Modal
        open={broadcastOpen}
        title="Send announcement"
        onClose={() => setBroadcastOpen(false)}
        footer={<>
          <Button variant="ghost" onClick={() => setBroadcastOpen(false)}>Cancel</Button>
          <Button onClick={sendBroadcast} disabled={!form.title || !form.message}>Send</Button>
        </>}
      >
        <Field label="Title">
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Message">
          <Textarea rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
        </Field>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Audience" hint="Leave empty to notify the whole organisation">
            <Select value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
              <option value="">Whole organisation</option>
              {departments.map((d) => <option key={d.name} value={d.name}>{d.name} ({d.count})</option>)}
            </Select>
          </Field>
          <Field label="Priority">
            <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="Normal">Normal</option>
              <option value="High">High</option>
            </Select>
          </Field>
        </div>
      </Modal>
    </div>
  )
}
