# HRMS – Human Resource Management System

Secure & scalable HRMS built with **Python (FastAPI) + SQL (SQLite/PostgreSQL) + React (Vite + Tailwind)**.

## Features

- JWT authentication + Role-based access (Admin / HR / Employee)
- Employee onboarding, profiles, document upload, deactivate
- Attendance: check-in / check-out, working hours, admin override, monthly summary
- Leave: apply, approve/reject, balance tracking, LOP support
- Payroll: monthly calculation with LOP deduction, lock, salary slip PDF
- Email notification simulation (onboarding, leave, payroll)
- Admin & Employee dashboards
- Reports export (CSV): attendance, leave, payroll
- Audit logs for critical actions

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
# Optional: copy .env.example to .env and edit
python seed.py          # creates DB + sample users
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

## Sample Credentials

| Role     | Email              | Password   |
|----------|--------------------|------------|
| Admin    | admin@gmail.com    | Admin@123  |
| HR       | hr@gmail.com       | Hr@12345   |
| Employee | abi@gmail.com      | Emp@12345  |
| Employee | pradeesh@gmail.com | Emp@12345  |
| Employee | linga@gmail.com    | Emp@12345  |
| Employee | rohith@gmail.com   | Emp@12345  |
| Employee | sugan@gmail.com    | Emp@12345  |


## Project Structure

```
hrms/
├── backend/          # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/      # routers
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/ # payroll, PDF, email
│   │   └── ...
│   ├── seed.py
│   ├── requirements.txt
│   └── hrms.db       # pre-seeded SQLite (optional)
├── frontend/         # React + Vite + Tailwind
├── docs/             # schema, Postman collection
└── sample_data/      # sample salary slip PDF
```

## Database

Default: SQLite (`hrms.db`).  
For PostgreSQL set `DATABASE_URL=postgresql://user:pass@localhost/hrms`.

See `docs/schema.sql` for full schema.

## API Overview

| Module      | Endpoints |
|-------------|-----------|
| Auth        | POST /api/auth/login, GET /me, POST /refresh |
| Employees   | CRUD /api/employees, documents upload |
| Attendance  | check-in, check-out, me, today, override, summary |
| Leave       | types, balances, apply, requests, action |
| Payroll     | generate, list, me, lock, slip (PDF) |
| Reports     | dashboard, attendance/leave/payroll export CSV |


## UI Screenshots

Screenshots are in `docs/screenshots/`:

| File | Description |
|------|-------------|
| `login.png` | Login page |
| `admin-dashboard.png` | Admin dashboard (stats + departments) |
| `admin-employees.png` | Employee list (Abi, Pradeesh, Linga, Rohith, Sugan) |
| `admin-leave.png` | Leave approval panel |
| `employee-dashboard.png` | Employee home (check-in, leave balance) |

## Notes

- Passwords stored with **bcrypt** (no plain text).
- JWT access + refresh tokens.
- Salary slip generated with ReportLab (PDF).
- Emails are **simulated** and logged (configure SMTP in `.env` for real send).
- File uploads restricted to pdf/jpg/png/doc (max 5MB).

## Deliverables Included

- Full source (frontend + backend)
- Pre-seeded SQLite database
- `docs/schema.sql`
- `docs/postman_collection.json` (import into Postman)
- Sample credentials above
- Sample salary slip can be generated via Admin → Payroll → Generate → Download PDF

---

Built for demonstration / assignment use. Change `SECRET_KEY` before any production deployment.
