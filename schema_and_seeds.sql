-- ====================================================================
-- CivicPulse Municipal Redressal Hub - Relational SQL Migration & Seeds
-- Database Compatibility: PostgreSQL 14+ / MySQL 8.0+ / SQLite 3
-- ====================================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('RESIDENT', 'MUNICIPAL_OFFICER', 'OPERATOR')),
    department VARCHAR(100) DEFAULT 'Public',
    ward VARCHAR(50) DEFAULT 'Ward 12',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. COMPLAINTS TABLE
CREATE TABLE IF NOT EXISTS complaints (
    id VARCHAR(50) PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    address VARCHAR(255) NOT NULL,
    reporter_name VARCHAR(100),
    reporter_contact VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'Moderate',
    status VARCHAR(50) DEFAULT 'Submitted',
    date DATE DEFAULT CURRENT_DATE,
    location_confidence DECIMAL(3,2) DEFAULT 0.85,
    sla_breached BOOLEAN DEFAULT FALSE,
    assigned_officer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. FIELD CREWS TABLE
CREATE TABLE IF NOT EXISTS field_crews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    crew_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    assigned_ward VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'Available',
    active_tickets INT DEFAULT 0
);

-- 4. AUDIT LOGS TABLE
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_id VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    performed_by VARCHAR(100) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ====================================================================
-- SEED DATA
-- ====================================================================

-- Default Operator Admin Account (Exclusive permission to create Municipal Officers)
-- Username/Email: operator_admin (operator_admin@civicpulse.gov)
-- Password: Password123!
INSERT INTO users (id, name, email, password_hash, role, department, ward) 
VALUES (1, 'Municipal Admin Operator', 'operator_admin@civicpulse.gov', 'Password123!', 'OPERATOR', 'Executive Administration', 'All Wards')
ON DUPLICATE KEY UPDATE name=name;

-- Seed Municipal Operations Officers
INSERT INTO users (id, name, email, password_hash, role, department, ward) 
VALUES 
(2, 'Er. S. Deshmukh', 'aee.ward12@civicpulse.gov', 'opsmanager2026', 'MUNICIPAL_OFFICER', 'Water Supply & Engineering', 'Ward 12'),
(3, 'Er. R. Mehta', 'road.maint@civicpulse.gov', 'opsmanager2026', 'MUNICIPAL_OFFICER', 'Pothole / Road Repair', 'District 3')
ON DUPLICATE KEY UPDATE name=name;

-- Seed Default Resident Users
INSERT INTO users (id, name, email, password_hash, role, department, ward) 
VALUES 
(4, 'Ramesh Kumar', 'ramesh.k@gmail.com', 'password123', 'RESIDENT', 'Public', 'Ward 12'),
(5, 'Ananya Verma', 'ananya.v@gmail.com', 'password123', 'RESIDENT', 'Public', 'Ward 12')
ON DUPLICATE KEY UPDATE name=name;

-- Seed Field Repair Crews
INSERT INTO field_crews (id, crew_name, department, assigned_ward, status, active_tickets) VALUES
(1, 'Ward 12 Water Repair Unit', 'Water Supply', 'Ward 12', 'On Duty', 2),
(2, 'District 3 Heavy Asphalt Rig', 'Pothole / Road Repair', 'District 3', 'On Duty', 1),
(3, 'Ward 12 Electrical Repair Truck', 'Streetlight Outage', 'Ward 12', 'Available', 0)
ON DUPLICATE KEY UPDATE crew_name=crew_name;
