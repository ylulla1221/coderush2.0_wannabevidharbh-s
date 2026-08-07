const express = require('express');
const path = require('path');
const { db, getAsync, allAsync, runAsync } = require('./db');
const { getAddressFromCoords, getCoordsFromAddress } = require('./geocoder');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// AUTHENTICATION API
app.post('/api/auth/signup', async (req, res) => {
  const { name, email, password, ward } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'Missing name, email, or password' });
  }

  try {
    // Check if email already registered
    const existing = await getAsync('SELECT * FROM users WHERE email = ?', [email]);
    if (existing) {
      return res.status(400).json({ error: 'Email already registered. Please login.' });
    }

    const result = await runAsync(`
      INSERT INTO users (name, email, password_hash, role, department, ward)
      VALUES (?, ?, ?, 'RESIDENT', 'Public', ?)
    `, [name, email, password, ward || 'Ward 12']);

    res.status(201).json({
      success: true,
      user: {
        id: result.id,
        name,
        email,
        role: 'RESIDENT',
        ward: ward || 'Ward 12'
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required' });
  }

  try {
    const user = await getAsync('SELECT * FROM users WHERE email = ?', [email]);
    if (!user) {
      return res.status(400).json({ error: 'Incorrect email or password' });
    }

    // Direct match check (password is stored in plaintext in seeds for simplicity)
    if (user.password_hash !== password) {
      return res.status(400).json({ error: 'Incorrect email or password' });
    }

    res.json({
      success: true,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        department: user.department,
        ward: user.ward
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 1. GET /api/complaints
app.get('/api/complaints', async (req, res) => {
  try {
    const rows = await allAsync('SELECT * FROM complaints ORDER BY created_at DESC');
    // Map database snake_case fields to camelCase expected by the frontend
    const mapped = rows.map(r => ({
      id: r.id,
      category: r.category,
      description: r.description,
      lat: r.lat,
      lng: r.lng,
      address: r.address,
      reporterName: r.reporter_name,
      reporterContact: r.reporter_contact,
      priority: r.priority,
      status: r.status,
      date: r.date,
      locationConfidence: r.location_confidence,
      slaBreached: !!r.sla_breached,
      assignedOfficer: r.assigned_officer,
      createdAt: r.created_at
    }));
    res.json(mapped);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 2. POST /api/complaints
app.post('/api/complaints', async (req, res) => {
  const {
    id, category, description, lat, lng, address,
    reporterName, reporterContact, priority, status, date,
    locationConfidence
  } = req.body;

  if (!id || !category || !description || !address) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  try {
    await runAsync(`
      INSERT INTO complaints (
        id, category, description, lat, lng, address, 
        reporter_name, reporter_contact, priority, status, date, 
        location_confidence, sla_breached
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    `, [
      id, category, description, lat || null, lng || null, address,
      reporterName || null, reporterContact || null, priority || 'Moderate',
      status || 'Submitted', date || new Date().toISOString().split('T')[0],
      locationConfidence || 0.85
    ]);

    // Insert an initial audit log entry
    await runAsync(`
      INSERT INTO audit_logs (ticket_id, action, performed_by, details)
      VALUES (?, 'COMPLAINT_CREATED', 'CITIZEN_PORTAL', ?)
    `, [id, `Complaint intake via standard/AI form. Location Confidence: ${locationConfidence || 0.85}`]);

    res.status(201).json({ success: true, id });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. PUT /api/complaints/:id/status
app.put('/api/complaints/:id/status', async (req, res) => {
  const { id } = req.params;
  const { status, assignedOfficer, auditAction, auditDetails, performedBy } = req.body;

  try {
    const c = await getAsync('SELECT * FROM complaints WHERE id = ?', [id]);
    if (!c) {
      return res.status(404).json({ error: 'Complaint not found' });
    }

    const newStatus = status || c.status;
    const newOfficer = assignedOfficer !== undefined ? assignedOfficer : c.assigned_officer;
    const slaBreached = (newStatus === 'Resolved') ? 0 : c.sla_breached;

    await runAsync(
      'UPDATE complaints SET status = ?, assigned_officer = ?, sla_breached = ? WHERE id = ?',
      [newStatus, newOfficer, slaBreached, id]
    );

    // Insert audit log
    await runAsync(
      'INSERT INTO audit_logs (ticket_id, action, performed_by, details) VALUES (?, ?, ?, ?)',
      [id, auditAction || 'STATUS_UPDATED', performedBy || 'MUNICIPAL_OFFICER', auditDetails || `Status updated to ${newStatus}`]
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. PUT /api/complaints/:id/override (SLA Manual Override)
app.put('/api/complaints/:id/override', async (req, res) => {
  const { id } = req.params;
  try {
    await runAsync(`
      UPDATE complaints 
      SET status = 'In Investigation', priority = 'Urgent', assigned_officer = 'Level 2 Manager (ASSISTANT_EXECUTIVE_ENGINEER)', sla_breached = 0 
      WHERE id = ?
    `, [id]);

    await runAsync(`
      INSERT INTO audit_logs (ticket_id, action, performed_by, details)
      VALUES (?, 'MANUAL_EXECUTIVE_OVERRIDE_EXECUTED', 'OPERATOR_ADMIN', 'Priority locked to Urgent. Re-assigned to Level 2 Manager.')
    `, [id]);

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 5. POST /api/complaints/bulk-dispatch
app.post('/api/complaints/bulk-dispatch', async (req, res) => {
  const { ticketIds } = req.body;
  if (!ticketIds || !Array.isArray(ticketIds) || ticketIds.length === 0) {
    return res.status(400).json({ error: 'Invalid ticket IDs list' });
  }

  try {
    const placeholders = ticketIds.map(() => '?').join(',');
    await runAsync(`
      UPDATE complaints 
      SET status = 'Assigned', assigned_officer = 'Ward 12 Emergency Repair Rig' 
      WHERE id IN (${placeholders})
    `, ticketIds);

    for (const tid of ticketIds) {
      await runAsync(`
        INSERT INTO audit_logs (ticket_id, action, performed_by, details)
        VALUES (?, 'BULK_CREW_DISPATCHED', 'OPERATOR_ADMIN', 'Dispatched to Ward 12 Emergency Repair Rig')
      `, [tid]);
    }

    res.json({ success: true, count: ticketIds.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 6. GET /api/crews
app.get('/api/crews', async (req, res) => {
  try {
    const rows = await allAsync('SELECT * FROM field_crews');
    const mapped = rows.map(r => ({
      id: r.id,
      crewName: r.crew_name,
      department: r.department,
      assignedWard: r.assigned_ward,
      status: r.status,
      activeTickets: r.active_tickets
    }));
    res.json(mapped);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 7. GET /api/officers
app.get('/api/officers', async (req, res) => {
  try {
    const rows = await allAsync("SELECT id, name, email, department, ward, created_at FROM users WHERE role = 'MUNICIPAL_OFFICER'");
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 8. POST /api/officers
app.post('/api/officers', async (req, res) => {
  const { name, email, password, department, ward } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'Missing name, email, or password' });
  }

  try {
    const result = await runAsync(`
      INSERT INTO users (name, email, password_hash, role, department, ward)
      VALUES (?, ?, ?, 'MUNICIPAL_OFFICER', ?, ?)
    `, [name, email, password, department || 'General', ward || 'Ward 12']);

    res.status(201).json({ success: true, id: result.id });
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      res.status(400).json({ error: 'Email already exists' });
    } else {
      res.status(500).json({ error: err.message });
    }
  }
});

// 9. GET /api/audit-logs
app.get('/api/audit-logs', async (req, res) => {
  try {
    const rows = await allAsync('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 10. POST /api/sql (Real raw SQL execution for the explorer!)
app.post('/api/sql', async (req, res) => {
  const { sql } = req.body;
  if (!sql || typeof sql !== 'string') {
    return res.status(400).json({ error: 'Missing SQL statement' });
  }

  const startTime = Date.now();
  const lowerSql = sql.trim().toLowerCase();

  try {
    if (lowerSql.startsWith('select') || lowerSql.startsWith('pragma') || lowerSql.startsWith('explain')) {
      // Query statements return rows
      const rows = await allAsync(sql);
      const executionTime = Date.now() - startTime;
      const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
      res.json({
        type: 'select',
        columns,
        rows,
        affectedRows: 0,
        executionTimeMs: executionTime
      });
    } else {
      // Update/Insert/Delete statements return meta
      const result = await runAsync(sql);
      const executionTime = Date.now() - startTime;
      res.json({
        type: 'write',
        columns: [],
        rows: [],
        affectedRows: result.changes,
        executionTimeMs: executionTime
      });
    }
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 11. GET /api/sql/dump
app.get('/api/sql/dump', async (req, res) => {
  try {
    let sqlDump = `-- ==========================================================\n`;
    sqlDump += `-- CivicPulse Municipal Redressal Relational Database Dump\n`;
    sqlDump += `-- Created At: ${new Date().toISOString()}\n`;
    sqlDump += `-- SQLite Database Schema & Seed Data\n`;
    sqlDump += `-- ==========================================================\n\n`;

    // 1. Users DDL & DML
    sqlDump += `-- Users Table\n`;
    sqlDump += `DROP TABLE IF EXISTS users;\n`;
    sqlDump += `CREATE TABLE users (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  name VARCHAR(100) NOT NULL,\n  email VARCHAR(100) NOT NULL UNIQUE,\n  password_hash VARCHAR(255) NOT NULL,\n  role VARCHAR(50) NOT NULL,\n  department VARCHAR(100),\n  ward VARCHAR(50),\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n`;
    
    const users = await allAsync('SELECT * FROM users');
    users.forEach(u => {
      sqlDump += `INSERT INTO users (id, name, email, password_hash, role, department, ward, created_at) VALUES (${u.id}, '${u.name.replace(/'/g, "''")}', '${u.email.replace(/'/g, "''")}', '${u.password_hash.replace(/'/g, "''")}', '${u.role}', '${u.department ? u.department.replace(/'/g, "''") : ''}', '${u.ward}', '${u.created_at}');\n`;
    });

    // 2. Complaints DDL & DML
    sqlDump += `\n-- Complaints Table\n`;
    sqlDump += `DROP TABLE IF EXISTS complaints;\n`;
    sqlDump += `CREATE TABLE complaints (\n  id VARCHAR(50) PRIMARY KEY,\n  category VARCHAR(100) NOT NULL,\n  description TEXT NOT NULL,\n  lat DECIMAL(10, 8),\n  lng DECIMAL(11, 8),\n  address VARCHAR(255) NOT NULL,\n  reporter_name VARCHAR(100),\n  reporter_contact VARCHAR(50),\n  priority VARCHAR(20),\n  status VARCHAR(50),\n  date DATE,\n  location_confidence DECIMAL(3,2),\n  sla_breached BOOLEAN,\n  assigned_officer VARCHAR(100),\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n`;
    
    const complaints = await allAsync('SELECT * FROM complaints');
    complaints.forEach(c => {
      sqlDump += `INSERT INTO complaints (id, category, description, lat, lng, address, reporter_name, reporter_contact, priority, status, date, location_confidence, sla_breached, assigned_officer, created_at) VALUES ('${c.id}', '${c.category}', '${c.description.replace(/'/g, "''")}', ${c.lat}, ${c.lng}, '${c.address.replace(/'/g, "''")}', '${c.reporter_name ? c.reporter_name.replace(/'/g, "''") : ''}', '${c.reporter_contact || ''}', '${c.priority}', '${c.status}', '${c.date}', ${c.location_confidence}, ${c.sla_breached}, '${c.assigned_officer ? c.assigned_officer.replace(/'/g, "''") : ''}', '${c.created_at}');\n`;
    });

    // 3. Field Crews DDL & DML
    sqlDump += `\n-- Field Crews Table\n`;
    sqlDump += `DROP TABLE IF EXISTS field_crews;\n`;
    sqlDump += `CREATE TABLE field_crews (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  crew_name VARCHAR(100) NOT NULL,\n  department VARCHAR(100) NOT NULL,\n  assigned_ward VARCHAR(50) NOT NULL,\n  status VARCHAR(50),\n  active_tickets INT\n);\n\n`;
    
    const crews = await allAsync('SELECT * FROM field_crews');
    crews.forEach(f => {
      sqlDump += `INSERT INTO field_crews (id, crew_name, department, assigned_ward, status, active_tickets) VALUES (${f.id}, '${f.crew_name.replace(/'/g, "''")}', '${f.department.replace(/'/g, "''")}', '${f.assigned_ward}', '${f.status}', ${f.active_tickets});\n`;
    });

    // 4. Audit Logs DDL & DML
    sqlDump += `\n-- Audit Logs Table\n`;
    sqlDump += `DROP TABLE IF EXISTS audit_logs;\n`;
    sqlDump += `CREATE TABLE audit_logs (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  ticket_id VARCHAR(50) NOT NULL,\n  action VARCHAR(100) NOT NULL,\n  performed_by VARCHAR(100) NOT NULL,\n  details TEXT,\n  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n`;
    
    const logs = await allAsync('SELECT * FROM audit_logs');
    logs.forEach(l => {
      sqlDump += `INSERT INTO audit_logs (id, ticket_id, action, performed_by, details, timestamp) VALUES (${l.id}, '${l.ticket_id}', '${l.action}', '${l.performed_by}', '${l.details ? l.details.replace(/'/g, "''") : ''}', '${l.timestamp}');\n`;
    });

    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Content-Disposition', 'attachment; filename=civic_redressal_db.sql');
    res.send(sqlDump);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 12. GET /api/stats
app.get('/api/stats', async (req, res) => {
  try {
    const complaints = await allAsync('SELECT * FROM complaints');
    const crews = await allAsync('SELECT * FROM field_crews');
    
    const totalActive = complaints.filter(c => c.status !== 'Resolved').length;
    const urgentQueue = complaints.filter(c => c.priority === 'Urgent' && c.status !== 'Resolved').length;
    const slaBreachedCount = complaints.filter(c => c.sla_breached && c.status !== 'Resolved').length;
    const activeCrews = crews.filter(cr => cr.status === 'On Duty').length;
    const totalCrews = crews.length;

    // SLA Compliance = Percentage of non-breached resolved or pending tickets
    const totalTickets = complaints.length;
    const breachedTotal = complaints.filter(c => c.sla_breached).length;
    const slaCompliance = totalTickets > 0 ? Math.round(((totalTickets - breachedTotal) / totalTickets) * 100) : 100;

    // Status counts
    const statusCounts = {
      Submitted: complaints.filter(c => c.status === 'Submitted').length,
      Assigned: complaints.filter(c => c.status === 'Assigned').length,
      'In Investigation': complaints.filter(c => c.status === 'In Investigation' || c.status === 'SLA Escalated').length,
      Resolved: complaints.filter(c => c.status === 'Resolved').length
    };

    // Priority counts
    const priorityCounts = {
      Urgent: complaints.filter(c => c.priority === 'Urgent').length,
      Moderate: complaints.filter(c => c.priority === 'Moderate').length,
      Low: complaints.filter(c => c.priority === 'Low').length
    };

    res.json({
      totalActive,
      urgentQueue,
      slaBreachedCount,
      activeCrews,
      totalCrews,
      slaCompliance,
      statusCounts,
      priorityCounts,
      totalComplaints: totalTickets
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 13. GET /api/issues (Fetch all issues)
app.get('/api/issues', async (req, res) => {
  try {
    const rows = await allAsync('SELECT * FROM issues ORDER BY created_at DESC');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 14. POST /api/issues (Create a new issue)
app.post('/api/issues', async (req, res) => {
  const { title, description, latitude, longitude } = req.body;
  if (!title || !description || latitude === undefined || longitude === undefined) {
    return res.status(400).json({ error: 'Missing title, description, latitude, or longitude' });
  }

  try {
    const result = await runAsync(`
      INSERT INTO issues (title, description, latitude, longitude)
      VALUES (?, ?, ?, ?)
    `, [title, description, latitude, longitude]);

    res.status(201).json({
      success: true,
      issue: {
        id: result.id,
        title,
        description,
        latitude,
        longitude
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 15. GET /api/geocode/reverse (Reverse geocoding endpoint)
app.get('/api/geocode/reverse', async (req, res) => {
  const { lat, lng } = req.query;
  if (!lat || !lng) {
    return res.status(400).json({ error: 'Missing lat or lng parameter' });
  }

  try {
    const address = await getAddressFromCoords(lat, lng);
    res.json({ address });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 16. GET /api/geocode/search (Forward geocoding endpoint)
app.get('/api/geocode/search', async (req, res) => {
  const { q } = req.query;
  if (!q) {
    return res.status(400).json({ error: 'Missing q (query) parameter' });
  }

  try {
    const coords = await getCoordsFromAddress(q);
    res.json(coords);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Start Server
app.listen(PORT, () => {
  console.log(`CivicPulse backend server running on port ${PORT}`);
});
