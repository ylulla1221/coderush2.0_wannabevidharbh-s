const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

const dbPath = path.join(__dirname, 'civicpulse.db');

// Delete existing database for a clean start if running init script manually
if (fs.existsSync(dbPath)) {
  try {
    fs.unlinkSync(dbPath);
    console.log('Removed existing database.');
  } catch (err) {
    console.log('Database file exists and is locked. Proceeding without deleting it.');
  }
}

const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error opening database:', err);
    process.exit(1);
  }
  console.log('Database connected.');
});

db.serialize(() => {
  // 1. Create Tables
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name VARCHAR(100) NOT NULL,
      email VARCHAR(100) NOT NULL UNIQUE,
      password_hash VARCHAR(255) NOT NULL,
      role VARCHAR(50) NOT NULL CHECK (role IN ('RESIDENT', 'MUNICIPAL_OFFICER', 'OPERATOR')),
      department VARCHAR(100) DEFAULT 'Public',
      ward VARCHAR(50) DEFAULT 'Ward 12',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  db.run(`
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
      sla_breached BOOLEAN DEFAULT 0,
      assigned_officer VARCHAR(100),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS field_crews (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      crew_name VARCHAR(100) NOT NULL,
      department VARCHAR(100) NOT NULL,
      assigned_ward VARCHAR(50) NOT NULL,
      status VARCHAR(50) DEFAULT 'Available',
      active_tickets INT DEFAULT 0
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ticket_id VARCHAR(50) NOT NULL,
      action VARCHAR(100) NOT NULL,
      performed_by VARCHAR(100) NOT NULL,
      details TEXT,
      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title VARCHAR(255) NOT NULL,
      description TEXT NOT NULL,
      latitude DECIMAL(10, 8) NOT NULL,
      longitude DECIMAL(11, 8) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  console.log('Tables created successfully.');

  // 2. Seed Users
  const stmtUser = db.prepare(`
    INSERT INTO users (id, name, email, password_hash, role, department, ward)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  stmtUser.run(1, 'Municipal Admin Operator', 'operator_admin@civicpulse.gov', 'Password123!', 'OPERATOR', 'Executive Administration', 'All Wards');
  stmtUser.run(2, 'Er. S. Deshmukh', 'aee.ward12@civicpulse.gov', 'opsmanager2026', 'MUNICIPAL_OFFICER', 'Water Supply & Engineering', 'Ward 12');
  stmtUser.run(3, 'Er. R. Mehta', 'road.maint@civicpulse.gov', 'opsmanager2026', 'MUNICIPAL_OFFICER', 'Pothole / Road Repair', 'District 3');
  stmtUser.run(4, 'Ramesh Kumar', 'ramesh.k@gmail.com', 'password123', 'RESIDENT', 'Public', 'Ward 12');
  stmtUser.run(5, 'Ananya Verma', 'ananya.v@gmail.com', 'password123', 'RESIDENT', 'Public', 'Ward 12');
  stmtUser.finalize();

  // 3. Seed Field Crews
  const stmtCrew = db.prepare(`
    INSERT INTO field_crews (id, crew_name, department, assigned_ward, status, active_tickets)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  stmtCrew.run(1, 'Ward 12 Water Repair Unit', 'Water Supply', 'Ward 12', 'On Duty', 2);
  stmtCrew.run(2, 'District 3 Heavy Asphalt Rig', 'Pothole / Road Repair', 'District 3', 'On Duty', 1);
  stmtCrew.run(3, 'Ward 12 Electrical Repair Truck', 'Streetlight Outage', 'Ward 12', 'Available', 0);
  stmtCrew.finalize();

  // 4. Seed Complaints
  const stmtComplaint = db.prepare(`
    INSERT INTO complaints (id, category, description, lat, lng, address, reporter_name, reporter_contact, priority, status, date, location_confidence, sla_breached, assigned_officer)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  stmtComplaint.run(
    'CR-9901', 'Water Supply', 'Paani nahi aa raha 2 din se ward 12 main', 
    41.8850, -87.6350, 'Ward 12 (Landmark Pending)', 'Ramesh Kumar', '+91 98765 43210', 
    'Moderate', 'Submitted', '2026-08-07', 0.55, 0, null
  );
  stmtComplaint.run(
    'INC-2026-0412', 'Water Supply', 'Big pipe leaking near St. Jude school main road', 
    41.8795, -87.6255, 'St. Jude School Main Road, Ward 12, Chicago, IL', 'Ananya Verma', '+91 99887 76655', 
    'Urgent', 'Assigned', '2026-08-07', 0.89, 0, 'Ward 12 Water Repair Unit'
  );
  stmtComplaint.run(
    'CR-2026-08912', 'Water Supply', 'Sewage line blockage overflowing on Market St near Ward 12 junction', 
    41.8820, -87.6310, 'Market St & Ward 12 Junction, Chicago, IL', 'Vikram Singh', '+91 91234 56789', 
    'Urgent', 'SLA Escalated', '2026-08-07', 0.85, 1, 'Level 2 Manager (ASSISTANT_EXECUTIVE_ENGINEER)'
  );
  stmtComplaint.run(
    'CP-8921', 'Pothole / Road Repair', 'A very large, dangerous pothole has developed in the center lane of 5th Avenue, just north of the Main St intersection. Multiple vehicles have had to swerve suddenly to avoid damage.', 
    41.8781, -87.6298, '5th Ave & Main St, Chicago, IL', 'Nehal Patel', '+1 (555) 019-2834', 
    'Urgent', 'Assigned', '2026-08-05', 0.95, 0, 'District 3 Heavy Asphalt Rig'
  );
  stmtComplaint.run(
    'CP-4731', 'Streetlight Outage', 'The street light pole directly opposite the Oak Street Library is completely dead. The area is extremely dark at night, making residents feel unsafe.', 
    41.8818, -87.6278, 'Oak St & Clark Ave, Chicago, IL', 'Sarah Jenkins', 'sjenkins@email.com', 
    'Moderate', 'In Investigation', '2026-08-02', 0.85, 0, null
  );
  stmtComplaint.run(
    'CP-1204', 'Graffiti', 'Large graffiti tag painted on the brick wall of the public library on the east side facing the parking lot. Needs removal before the weekend.', 
    41.8835, -87.6321, 'Public Library Side Wall, Chicago, IL', 'Michael Chang', '+1 (555) 014-9982', 
    'Low', 'Resolved', '2026-07-31', 0.90, 0, null
  );
  stmtComplaint.run(
    'CP-9905', 'Illegal Dumping', 'Several old tires, mattresses, and bags of trash dumped at the entrance of Miller Park. It blocks a portion of the pedestrian pathway.', 
    41.8756, -87.6244, 'Miller Park Gate 2, Chicago, IL', 'David Ross', 'dross99@gmail.com', 
    'Urgent', 'Submitted', '2026-08-06', 0.85, 0, null
  );
  stmtComplaint.finalize();

  // 5. Seed Audit Logs
  const stmtAudit = db.prepare(`
    INSERT INTO audit_logs (id, ticket_id, action, performed_by, timestamp, details)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  stmtAudit.run(501, 'CR-9901', 'PII_SCRUBBED_CLARIFICATION_SENT', 'SYSTEM_NLP_ENGINE', '2026-08-07 09:12:00', 'Location score 0.55');
  stmtAudit.run(502, 'INC-2026-0412', 'CLUSTER_LINKED_N8_ESCALATED', 'SPATIAL_CLUSTER_ENGINE', '2026-08-07 09:45:00', 'Centroid score 0.89');
  stmtAudit.run(503, 'CR-2026-08912', 'ESCALATION_TRIGGER_AUTOMATED', 'SLA_MONITOR_SERVICE', '2026-08-07 10:15:00', 'Re-routed to ASSISTANT_EXECUTIVE_ENGINEER');
  stmtAudit.finalize();

  // 6. Seed Issues (Pune)
  const stmtIssue = db.prepare(`
    INSERT INTO issues (title, description, latitude, longitude)
    VALUES (?, ?, ?, ?)
  `);
  stmtIssue.run('Water Logging at FC Road', 'Severe water logging near Goodluck Cafe after heavy rains.', 18.5218, 73.8486);
  stmtIssue.run('Pothole near Shaniwar Wada', 'Dangerous pothole at the main intersection causing traffic congestion.', 18.5204, 73.8567);
  stmtIssue.run('Garbage Pile near JM Road', 'Overflowing community bin spreading foul smell.', 18.5255, 73.8441);
  stmtIssue.finalize();

  console.log('Seeded database successfully.');
});

db.close();
