-- HRMS Database Schema
-- SQLite / PostgreSQL compatible. Created by SQLAlchemy models in backend/app/models.
-- Phase 2 additions: holidays, notifications, shifts and advanced compensation.

-- ============================================================ core / identity
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,                      -- Admin | HR | Employee
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    employee_code VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    designation VARCHAR(100),
    joining_date DATE NOT NULL,
    basic_salary NUMERIC(12,2) NOT NULL,            -- kept in sync with the latest revision
    hra NUMERIC(12,2) DEFAULT 0,
    allowances NUMERIC(12,2) DEFAULT 0,
    phone VARCHAR(20),
    address TEXT,
    region VARCHAR(80),                             -- regional-holiday applicability
    documents JSON,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ========================================================== holidays & calendar
CREATE TABLE holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    date DATE NOT NULL,
    holiday_type VARCHAR(20) NOT NULL DEFAULT 'Company',  -- Company | Regional | Optional
    region VARCHAR(80),                              -- required for Regional holidays
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, date, region)
);
CREATE INDEX idx_holidays_date ON holidays(date);

-- ================================================== shifts & work schedules
CREATE TABLE shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(80) UNIQUE NOT NULL,
    code VARCHAR(30) UNIQUE NOT NULL,
    start_time VARCHAR(5) NOT NULL,                 -- "HH:MM"
    end_time VARCHAR(5) NOT NULL,                   -- earlier than start => crosses midnight
    grace_minutes INTEGER DEFAULT 10,               -- late / early-exit tolerance
    standard_hours NUMERIC(4,1) DEFAULT 8,          -- hours beyond this are overtime
    is_night BOOLEAN DEFAULT 0,
    is_flexible BOOLEAN DEFAULT 0,                  -- no late / early-exit tracking
    is_remote BOOLEAN DEFAULT 0,
    is_default BOOLEAN DEFAULT 0,                   -- fallback for unassigned staff
    is_active BOOLEAN DEFAULT 1,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Effective-dated shift history per employee (employee assignment wins)
CREATE TABLE employee_shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    shift_id INTEGER NOT NULL REFERENCES shifts(id),
    effective_from DATE NOT NULL,
    effective_to DATE,
    notes TEXT,
    assigned_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_employee_shifts_employee ON employee_shifts(employee_id, effective_from);

-- Department default shift (used when the employee has no own assignment)
CREATE TABLE department_shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department VARCHAR(100) UNIQUE NOT NULL,
    shift_id INTEGER NOT NULL REFERENCES shifts(id),
    effective_from DATE NOT NULL,
    assigned_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================== attendance
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in DATETIME,
    check_out DATETIME,
    working_hours NUMERIC(5,2),
    status VARCHAR(20) DEFAULT 'Present',           -- Present | Half-day | Absent | Leave
    shift_id INTEGER REFERENCES shifts(id),         -- shift in force on this date
    is_late BOOLEAN DEFAULT 0,
    late_minutes INTEGER DEFAULT 0,
    is_early_exit BOOLEAN DEFAULT 0,
    early_exit_minutes INTEGER DEFAULT 0,
    overtime_hours NUMERIC(5,2) DEFAULT 0,
    is_override BOOLEAN DEFAULT 0,
    override_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, date)
);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_shift ON attendance(shift_id);

-- ======================================================================= leave
CREATE TABLE leave_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    max_days_per_year INTEGER DEFAULT 12,
    is_paid BOOLEAN DEFAULT 1                          -- 0 => Loss of Pay
);

CREATE TABLE leave_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    balance NUMERIC(5,1) NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    UNIQUE(employee_id, leave_type_id, year)
);

CREATE TABLE leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days NUMERIC(4,1) NOT NULL,                        -- working days only (holidays excluded)
    reason TEXT,
    status VARCHAR(20) DEFAULT 'Pending',              -- Pending | Approved | Rejected
    approved_by INTEGER REFERENCES users(id),
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================== compensation catalogue
CREATE TABLE salary_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(80) UNIQUE NOT NULL,
    code VARCHAR(30) UNIQUE NOT NULL,
    component_type VARCHAR(20) NOT NULL DEFAULT 'Earning',   -- Earning | Deduction
    calc_type VARCHAR(20) NOT NULL DEFAULT 'Fixed',          -- Fixed | PercentOfBasic | PercentOfGross
    default_value NUMERIC(12,2) DEFAULT 0,                   -- amount or percentage
    max_amount NUMERIC(12,2),                                -- statutory cap (e.g. PF ceiling)
    is_taxable BOOLEAN DEFAULT 1,
    is_statutory BOOLEAN DEFAULT 0,                          -- PF, professional tax, ...
    is_variable BOOLEAN DEFAULT 0,                           -- bonus / incentive
    is_basic BOOLEAN DEFAULT 0,                              -- drives the revision's basic pay
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Effective-dated compensation revision (history is preserved, never overwritten)
CREATE TABLE salary_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    effective_from DATE NOT NULL,
    basic_salary NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_ctc NUMERIC(12,2) NOT NULL DEFAULT 0,       -- annual gross earnings
    notes TEXT,
    revised_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_salary_revisions_employee ON salary_revisions(employee_id, effective_from);

CREATE TABLE salary_revision_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL REFERENCES salary_revisions(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES salary_components(id),
    label VARCHAR(80) NOT NULL,                       -- snapshot of the component name
    component_type VARCHAR(20) NOT NULL,
    calc_type VARCHAR(20) NOT NULL,                   -- per-employee rule (may override the component)
    value NUMERIC(12,2) NOT NULL DEFAULT 0,           -- amount or percentage as entered
    amount NUMERIC(12,2) NOT NULL DEFAULT 0,          -- resolved monthly amount
    UNIQUE(revision_id, component_id)
);

-- ====================================================================== payroll
CREATE TABLE payroll (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    working_days INTEGER,
    holiday_days INTEGER DEFAULT 0,
    present_days NUMERIC(5,1),
    paid_leave_days NUMERIC(5,1) DEFAULT 0,
    absent_days NUMERIC(5,1) DEFAULT 0,
    lop_days NUMERIC(5,1) DEFAULT 0,
    overtime_hours NUMERIC(6,2) DEFAULT 0,
    basic NUMERIC(12,2),
    hra NUMERIC(12,2),
    allowances NUMERIC(12,2),
    overtime_pay NUMERIC(12,2) DEFAULT 0,
    bonus NUMERIC(12,2) DEFAULT 0,
    variable_pay NUMERIC(12,2) DEFAULT 0,
    gross_earnings NUMERIC(12,2) DEFAULT 0,
    lop_deduction NUMERIC(12,2) DEFAULT 0,
    pf_deduction NUMERIC(12,2) DEFAULT 0,
    statutory_deductions NUMERIC(12,2) DEFAULT 0,
    other_deductions NUMERIC(12,2) DEFAULT 0,
    deductions NUMERIC(12,2) DEFAULT 0,               -- total deductions
    total_deductions NUMERIC(12,2) DEFAULT 0,
    net_salary NUMERIC(12,2),
    status VARCHAR(20) DEFAULT 'Generated',           -- Generated | Locked | Credited
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    locked_at DATETIME,
    locked_by INTEGER REFERENCES users(id),
    revision_id INTEGER REFERENCES salary_revisions(id),
    UNIQUE(employee_id, month, year)
);

-- Immutable per-payslip snapshot of every earning and deduction line
CREATE TABLE payroll_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_id INTEGER NOT NULL REFERENCES payroll(id) ON DELETE CASCADE,
    component_id INTEGER REFERENCES salary_components(id),
    code VARCHAR(30),                                 -- BASIC, PF, OVERTIME, LOP, ADJUSTMENT, ...
    name VARCHAR(80) NOT NULL,
    component_type VARCHAR(20) NOT NULL,
    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    source VARCHAR(20) NOT NULL DEFAULT 'Structure',  -- Structure | Attendance | Adjustment
    display_order INTEGER DEFAULT 0
);
CREATE INDEX idx_payroll_components_payroll ON payroll_components(payroll_id);

-- Manual bonus / deduction applied to a generated payslip
CREATE TABLE payroll_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_id INTEGER NOT NULL REFERENCES payroll(id) ON DELETE CASCADE,
    label VARCHAR(120) NOT NULL,
    kind VARCHAR(20) NOT NULL,                        -- Bonus | Deduction
    amount NUMERIC(12,2) NOT NULL,
    reason TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =================================================== notifications & audit
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(30) NOT NULL DEFAULT 'System',   -- Leave | Payroll | Attendance | Announcement | Holiday | Shift | System
    link VARCHAR(180),
    priority VARCHAR(10) NOT NULL DEFAULT 'Normal',   -- Normal | High
    is_read BOOLEAN DEFAULT 0,
    read_at DATETIME,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);

CREATE TABLE notification_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, category)
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email VARCHAR(255),
    subject VARCHAR(255),
    template VARCHAR(100),
    status VARCHAR(20),
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
