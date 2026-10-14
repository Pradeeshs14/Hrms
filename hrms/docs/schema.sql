-- HRMS Database Schema
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
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
    basic_salary NUMERIC(12,2) NOT NULL,
    hra NUMERIC(12,2) DEFAULT 0,
    allowances NUMERIC(12,2) DEFAULT 0,
    phone VARCHAR(20),
    address TEXT,
    documents JSON,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in DATETIME,
    check_out DATETIME,
    working_hours NUMERIC(5,2),
    status VARCHAR(20) DEFAULT 'Present',
    is_override BOOLEAN DEFAULT 0,
    override_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, date)
);
CREATE TABLE leave_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    max_days_per_year INTEGER DEFAULT 12,
    is_paid BOOLEAN DEFAULT 1
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
    days NUMERIC(4,1) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'Pending',
    approved_by INTEGER REFERENCES users(id),
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE payroll (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    working_days INTEGER,
    present_days NUMERIC(5,1),
    lop_days NUMERIC(5,1) DEFAULT 0,
    basic NUMERIC(12,2),
    hra NUMERIC(12,2),
    allowances NUMERIC(12,2),
    deductions NUMERIC(12,2) DEFAULT 0,
    net_salary NUMERIC(12,2),
    status VARCHAR(20) DEFAULT 'Generated',
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    locked_at DATETIME,
    UNIQUE(employee_id, month, year)
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
