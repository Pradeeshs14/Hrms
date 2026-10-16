# HRMS – Human Resource Management System

Secure & scalable HRMS built with **Python (FastAPI) + SQL (SQLite/PostgreSQL) + React (Vite + Tailwind)**.

Phase 2 adds four enterprise modules on top of the core HR suite:

| Module | What it does |
|---|---|
| 🗓 **Holidays & Calendar** | Company / regional / optional holidays, auto-excluded from attendance, leave and payroll; month & year calendar for every employee |
| 🔔 **In-app Notification Centre** | Per-user notifications with read/unread tracking, category preferences and department-wide Admin broadcasts (email notifications unchanged) |
| 🕒 **Shifts & Work Schedules** | General / night / flexible / remote shifts, effective-dated assignment to employees or departments, shift-aware late, early-exit and overtime, shift-wise reports |
| 💰 **Advanced Payroll & Compensation** | Configurable salary components, effective-dated compensation revisions, component-level payslip breakdown, manual bonus/deduction adjustments, overtime pay and lock / unlock / recalculate |

---

## Features

### Core (phase 1)
- JWT authentication + role-based access (Admin / HR / Employee)
- Employee onboarding, profiles, document upload, deactivate
- Attendance: check-in / check-out, working hours, admin override, monthly summary
- Leave: apply, approve/reject, balance tracking, LOP support
- Payroll: monthly calculation with LOP deduction, lock, salary slip PDF
- Email notification simulation (onboarding, leave, payroll)
- Admin & Employee dashboards, CSV exports, audit logs for critical actions

### Holiday & Calendar Management
- Three holiday types — **Company** (everyone), **Regional** (only matching `employee.region`), **Optional** (visible in the calendar, does **not** block attendance)
- Full CRUD with validation (region required for regional holidays, duplicate protection, audited)
- Every employee sees a **month view** and a **year view** calendar with weekend, holiday and optional markers plus the working-day count for the month
- Holidays are **automatically excluded** from:
  - attendance summaries (working days, absence, LOP),
  - leave day counting (`5 working days from Mon–Fri` is what gets charged, weekends/holidays are free),
  - payroll working-day count and LOP pro-rating
- Creating a holiday notifies every user through the in-app notification centre
- Working-days endpoint (`GET /holidays/working-days`) is region-aware and reusable by any client

### In-App Notification Centre
- Per-user notification rows with `title`, `message`, `category`, `priority`, `link`, `is_read`, `read_at`
- Categories: **Leave, Payroll, Attendance, Announcement, Holiday, Shift, System**
- Bell icon in both layouts with a live unread badge, quick panel and 30-second refresh
- Full page: filter by category, unread-only view, mark read / unread / delete, mark-all-read
- **Preferences**: each user can enable/disable categories; announcements are mandatory so company-wide messages always land
- **Admin/HR broadcast** to a whole department, the entire organisation or a role set — one notification row per recipient so read-state is per user
- Automatically raised by: leave applied/approved/rejected, payslip generated, salary credited, late check-in, early check-out, overtime logged, attendance correction, holiday announced, shift change, compensation revision, onboarding, deactivation, payroll unlock

### Shift & Work Schedule Management
- Shift definitions: name, code, start/end time, grace minutes, standard hours, night / flexible / remote flags, default-for-new-joiners, active flag
- **Night shifts** are detected automatically (end time earlier than start time) and the shift window rolls past midnight
- **Assignment history**: effective-dated `employee_shifts` rows with automatic closing of the previous assignment (full history preserved and visible)
- **Department defaults**: one shift per department, used whenever the employee has no own assignment
- Resolution order: *employee assignment → department default → global default shift*
- **Shift-aware attendance**: check-in after `start + grace` marks late with the minute count, check-out before `end − grace` marks early exit, hours beyond `standard_hours` become overtime (paid at 1.5×)
- Flexible shifts deliberately skip late / early-exit tracking
- **Admin override** can set times, status, overtime and the shift used for the calculation (audited)
- Shift-wise attendance report with per-shift present / late / early-exit / overtime / hours totals and CSV export

### Advanced Payroll & Compensation
- **Salary component catalogue**: earnings and deductions with `Fixed`, `PercentOfBasic` or `PercentOfGross` rules, statutory caps (PF ceiling), taxable / variable / statutory flags and display order
- Seeded catalogue: Basic Pay, HRA (40 % of basic), Special Allowance, Performance Bonus (variable), Provident Fund (12 % capped at ₹1,800), Professional Tax, TDS
- **Effective-dated revisions** (`salary_revisions` + lines) keep a permanent compensation history — nothing is overwritten, and an existing revision on the same date is rewritten instead of duplicated
- Revising compensation notifies the employee and keeps the legacy `employees.basic_salary / hra / allowances` columns in sync
- **Payslip breakdown**: every payslip stores an immutable snapshot of each earning/deduction line with its source (`Structure`, `Attendance` or `Adjustment`)
- Payroll is driven by real data: working days (holidays excluded), present/half days, approved paid leave, loss of pay, overtime hours at 1.5× hourly, statutory deductions, LOP deduction
- **Manual adjustments**: bonuses and deductions with label + reason, applied instantly and folded into the totals
- **Lock → Unlock → Recalculate**: HR/Admin lock a run, only Admin can unlock (audited, notifies the payroll team), locked payslips reject adjustments and recalculation
- Simulated salary credit with a transaction reference; historical payroll stays queryable by month, year, employee or status
- Salary slip PDF renders the real component breakdown, plus working days, holidays, paid leave, LOP, overtime, gross, deductions and net

---

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# Optional: copy .env.example to .env and edit
python seed.py                # recreates the database with demo data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: <http://localhost:8000/docs>

`seed.py` creates the schema, then loads 7 users, 5 shifts, 12 holidays, 7 salary components,
leave types & balances, ~275 attendance records across 60 days (with late arrivals, early exits
and overtime) and a set of notifications.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

---

## Sample credentials

| Role     | Email                | Password   |
|----------|----------------------|------------|
| Admin    | admin@gmail.com      | Admin@123  |
| HR       | hr@gmail.com         | Hr@12345   |
| Employee | abi@gmail.com        | Emp@12345  |
| Employee | pradeesh@gmail.com   | Emp@12345  |
| Employee | linga@gmail.com      | Emp@12345  |
| Employee | rohith@gmail.com     | Emp@12345  |
| Employee | sugan@gmail.com      | Emp@12345  |

Seeded demo shape: Abi Kumar (Engineering, General shift), Pradeesh Rajan (Engineering, Remote),
Linga Murugan (Sales, Morning), Rohith Suresh (Marketing, **Night**), Sugan Vasanth (Finance,
General), Priya Sharma (HR, Flexible, Karnataka region), System Admin (Management, General).
Regions drive the regional-holiday logic — Pongal applies to Tamil Nadu staff only.

The login page deliberately shows **no credentials**: this table (and `backend/seed.py`) is the
reference, and the email / password fields always start empty.

---

## Business rules

**Working days** — Monday–Friday, minus Company holidays and minus Regional holidays that match the
employee's region. Optional holidays never reduce the working-day count.

**Leave** — charged on working days only; a Friday-to-Monday request charges 2 days. Paid types draw
down the balance on approval, Loss of Pay does not.

**Loss of pay** — `approved unpaid leave days + working days with no attendance and no leave`, counted
only up to today and only from the joining date. `LOP deduction = (structure gross ÷ working days) × LOP days`.

**Overtime** — `(gross ÷ working days ÷ shift standard hours) × overtime hours × 1.5`, where overtime
hours are the minutes worked beyond the shift's standard hours.

**Provident fund** — 12 % of basic pay, capped at the component's `max_amount` (₹1,800 in the seed).

**Shift resolution** — employee assignment → department default → global default shift; for a date
outside every assignment window the previous assignment is ignored and the fallback chain applies.

**Notification preferences** — a disabled category silently skips delivery; announcements cannot be
disabled and broadcasts create one row per recipient.

---

## Project structure

```
hrms/
├── backend/                     # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/                 # routers: auth, employees, attendance, leave, payroll,
│   │   │                        #          reports, holidays, notifications, shifts, compensation
│   │   ├── models/              # user, employee, attendance, leave, payroll, audit,
│   │   │                        # holiday, notification, shift, compensation
│   │   ├── schemas/             # pydantic request/response models
│   │   ├── services/            # payroll, compensation, shift, holiday, notification, PDF, email
│   │   ├── core/security.py     # bcrypt + JWT helpers
│   │   ├── config.py, database.py, main.py
│   ├── seed.py                  # demo dataset
│   ├── requirements.txt
│   └── hrms.db                  # pre-seeded SQLite database
├── frontend/                    # React + Vite + Tailwind
│   └── src/
│       ├── api/client.js        # axios instance + token/401 handling
│       ├── components/          # ui primitives, NotificationBell, HolidayCalendar, ThemeToggle
│       ├── lib/format.js        # currency / date / month helpers
│       ├── context/             # auth context, theme context (light / dark)
│       └── pages/
│           ├── admin/           # Dashboard, Employees, Attendance, Leave, Shifts,
│           │                    # Holidays, Calendar, Payroll, Compensation, Reports, Notifications
│           └── employee/        # Dashboard, Attendance, Leave, Calendar, Salary,
│                                # Notifications, Profile
├── docs/
│   ├── schema.sql               # full database schema (20 tables)
│   ├── hrms-dump.sql            # full dump — schema + data, ready for restore
│   ├── postman_collection.json  # 91 requests / 10 folders, auto token capture
│   └── screenshots/             # phase-1 UI screenshots (login, dashboards, employees, leave)
└── sample_data/                 # sample salary slip PDF
```

---

## Database

Default: SQLite (`backend/hrms.db`, created by `python seed.py`).
For PostgreSQL set `DATABASE_URL=postgresql://user:pass@localhost/hrms`.

Full schema: [`docs/schema.sql`](docs/schema.sql) — 20 tables, ~550 rows in the shipped demo database
(7 employees, 5 shifts, 12 holidays, 7 components, 275 attendance records, 2 months of payroll).

Full dump (schema **and** data): [`docs/hrms-dump.sql`](docs/hrms-dump.sql) — the same 20 tables with
all seeded/operational rows as `INSERT` statements. Restore a fresh copy of the demo database with:

```bash
cd backend && sqlite3 hrms.db < ../docs/hrms-dump.sql
```

The dump is a point-in-time snapshot; `python seed.py` rebuilds the demo dataset from scratch.

| Area | Tables |
|---|---|
| Identity | `users`, `employees` |
| Holidays | `holidays` |
| Shifts | `shifts`, `employee_shifts`, `department_shifts` |
| Attendance | `attendance` (shift id, late / early-exit minutes, overtime hours) |
| Leave | `leave_types`, `leave_balances`, `leave_requests` |
| Compensation | `salary_components`, `salary_revisions`, `salary_revision_lines` |
| Payroll | `payroll`, `payroll_components`, `payroll_adjustments` |
| Notifications | `notifications`, `notification_preferences` |
| Audit | `audit_logs`, `email_logs` |

---

## API overview (85 operations)

| Module | Highlights |
|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/refresh` |
| Employees | CRUD `/api/employees`, document upload, deactivate, `GET /api/employees/me` |
| Attendance | check-in, check-out, `me`, `today`, `summary/me`, `summary/{id}`, `override/{id}` |
| Leave | types, balances, apply, `requests/me`, `requests`, `requests/{id}/action` |
| Holidays | CRUD `/api/holidays`, `upcoming`, `applicable`, `calendar`, `calendar/year`, `working-days` |
| Notifications | `GET /api/notifications`, `unread-count`, `{id}/read`, `{id}/unread`, `read-all`, `preferences` (GET/PUT), `broadcast`, `DELETE {id}` |
| Shifts | CRUD `/api/shifts`, `assign/employee`, `assign/department`, `assignments`, `assignments/employee/{id}`, `me`, `reports/attendance`, `reports/attendance/export` |
| Compensation | `components` CRUD, `employees` (CTC list), `employees/{id}`, `employees/{id}/revise`, `employees/{id}/revisions`, `me` |
| Payroll | `generate`, list, `me`, `{id}/breakdown`, `{id}/adjustments` (POST/DELETE), `{id}/recalculate`, `{id}/lock`, `{id}/unlock`, `{id}/credit`, `{id}/slip` |
| Reports | `dashboard`, `me/dashboard`, `shifts/summary`, `holidays/calendar`, CSV exports (attendance, leave, payroll, holidays, compensation) |

---

## Reports & CSV exports

- Attendance — shift, late minutes, early-exit minutes and overtime per record
- Leave — working-day counts with paid/unpaid classification
- Payroll — component-level earnings, statutory deductions, LOP and overtime
- Shift-wise attendance — grouped by shift with late / overtime totals
- Holidays — company / regional / optional list for a year
- Compensation — current structure, gross, deductions and annual CTC per employee

---

## UI screens

| Area | Screens |
|---|---|
| Admin | Dashboard (workforce + shift coverage KPIs), Employees, Attendance (today + monthly summary + override), Leave, **Shifts** (shifts / assignments / shift-wise report), **Holidays** (CRUD + counts), **Calendar** (month & year), Payroll (generate / breakdown / adjustments / lock), **Compensation** (components + structures + revise), Reports, **Alerts** |
| Employee | Dashboard (shift, holidays, pay summary), Attendance (monthly summary + day-by-day), Leave, **Calendar**, **Salary** (payslips + breakdown + structure + revision history), **Alerts**, Profile |

Screenshots of the phase-1 screens live in `docs/screenshots/`.

**Light / dark theme** — a toggle sits in the login card, the admin header and the employee header.
The choice is stored per browser (`localStorage`), applied before first paint so there is no flash,
and falls back to the operating-system preference until the user picks a theme.

---

## Notes

- Passwords stored with **bcrypt** (no plain text).
- JWT access + refresh tokens; every critical action is written to `audit_logs`.
- Salary slips are generated with ReportLab (PDF) from the stored component snapshot.
- Emails are **simulated** and logged (`email_logs`); configure SMTP in `.env` for real sending.
  In-app notifications are stored in the database and need no mail server.
- File uploads restricted to pdf/jpg/png/doc (max 5 MB).
- Change `SECRET_KEY` before any production deployment.

---

## Deliverables

- Full source (frontend + backend)
- Pre-seeded SQLite database with phase-2 demo data
- `docs/schema.sql` — complete 20-table schema
- `docs/hrms-dump.sql` — full database dump (schema + data)
- `docs/postman_collection.json` — 91 requests across 10 folders with automatic token capture
- Sample credentials above
- Sample salary slip: Admin → Payroll → Breakdown/PDF, or `sample_data/`

---

Built for demonstration / assignment use.
