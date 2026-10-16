export const MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']

export const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export const currency = (value) =>
  `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export const number = (value) => Number(value || 0).toLocaleString('en-IN')

export const monthName = (month) => MONTHS[month] || ''

export const periodLabel = (month, year) => `${monthName(month)} ${year}`

export const time = (value) =>
  value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'

export const dateStr = (value) =>
  value ? new Date(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'

export const dateTime = (value) => (value ? `${dateStr(value)} ${time(value)}` : '-')

export const todayISO = () => new Date().toISOString().slice(0, 10)

export const currentMonth = () => new Date().getMonth() + 1

export const currentYear = () => new Date().getFullYear()

export const hours = (value) => `${Number(value || 0).toFixed(2)} h`

export const download = (blob, filename) => {
  const url = window.URL.createObjectURL(new Blob([blob]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}
