require('dotenv').config();
const express = require('express');
const path = require('path');
const mongoose = require('mongoose');

// Mongoose Models
const User = require('./models/User');
const Complaint = require('./models/Complaint');
const FieldCrew = require('./models/FieldCrew');
const AuditLog = require('./models/AuditLog');

const { getAddressFromCoords, getCoordsFromAddress } = require('./geocoder');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// MongoDB Connection Setup
mongoose.connect(process.env.MONGODB_URI)
  .then(() => {
    console.log('Successfully connected to MongoDB Atlas!');
    seedDatabase();
  })
  .catch(err => console.error('MongoDB connection error:', err));

// Seed default accounts if database is fresh
async function seedDatabase() {
  try {
    const userCount = await User.countDocuments();
    if (userCount === 0) {
      await User.create([
        {
          name: 'Municipal Admin Operator',
          email: 'operator_admin@civicpulse.gov',
          passwordHash: 'Password123!',
          role: 'OPERATOR',
          department: 'Executive Administration',
          ward: 'All Wards'
        },
        {
          name: 'Er. S. Deshmukh',
          email: 'aee.ward12@civicpulse.gov',
          passwordHash: 'opsmanager2026',
          role: 'MUNICIPAL_OFFICER',
          department: 'Water Supply & Engineering',
          ward: 'Ward 12'
        },
        {
          name: 'Er. R. Mehta',
          email: 'road.maint@civicpulse.gov',
          passwordHash: 'opsmanager2026',
          role: 'MUNICIPAL_OFFICER',
          department: 'Pothole / Road Repair',
          ward: 'District 3'
        },
        {
          name: 'Ramesh Kumar',
          email: 'ramesh.k@gmail.com',
          passwordHash: 'password123',
          role: 'RESIDENT',
          department: 'Public',
          ward: 'Ward 12'
        },
        {
          name: 'Ananya Verma',
          email: 'ananya.v@gmail.com',
          passwordHash: 'password123',
          role: 'RESIDENT',
          department: 'Public',
          ward: 'Ward 12'
        }
      ]);
      console.log('Seeded default users in MongoDB.');
    }

    const crewCount = await FieldCrew.countDocuments();
    if (crewCount === 0) {
      await FieldCrew.create([
        {
          crewName: 'Ward 12 Water Repair Unit',
          department: 'Water Supply',
          assignedWard: 'Ward 12',
          status: 'On Duty',
          activeTickets: 2
        },
        {
          crewName: 'District 3 Heavy Asphalt Rig',
          department: 'Pothole / Road Repair',
          assignedWard: 'District 3',
          status: 'On Duty',
          activeTickets: 1
        },
        {
          crewName: 'Ward 12 Electrical Repair Truck',
          department: 'Streetlight Outage',
          assignedWard: 'Ward 12',
          status: 'Available',
          activeTickets: 0
        }
      ]);
      console.log('Seeded default field crews in MongoDB.');
    }
  } catch (err) {
    console.error('Seeding MongoDB database failed:', err);
  }
}

// 1. GET /api/complaints (Read all complaints)
app.get('/api/complaints', async (req, res) => {
  try {
    const complaints = await Complaint.find().sort({ createdAt: -1 });
    const mapped = complaints.map(c => ({
      id: c._id.toString(),
      category: c.category,
      description: c.description,
      lat: c.location.coordinates[1],
      lng: c.location.coordinates[0],
      address: c.address,
      reporterName: c.reporter?.name || 'Resident',
      reporterContact: c.reporter?.contact || '',
      priority: c.priority,
      status: c.status,
      date: c.createdAt.toISOString().split('T')[0],
      locationConfidence: 0.85
    }));
    res.json(mapped);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 2. POST /api/complaints (Create complaint)
app.post('/api/complaints', async (req, res) => {
  let {
    category, description, lat, lng, address,
    reporterName, reporterContact, priority, status, title
  } = req.body;

  if (!category || !description || !address) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  const isSeattle = lat === 47.6062 && lng === -122.3321;
  const isMissing = !lat || !lng || isNaN(parseFloat(lat)) || isNaN(parseFloat(lng));
  if (isMissing || isSeattle) {
    try {
      const coords = await getCoordsFromAddress(address);
      lat = coords.lat;
      lng = coords.lon;
    } catch (err) {
      console.error('Auto geocoding failed for complaint:', err.message);
      lat = 18.5204;
      lng = 73.8567;
    }
  }

  try {
    const newComplaint = await Complaint.create({
      title: title || `${category} at ${address}`,
      category,
      description,
      landmark: address.split(',')[0],
      city: address.split(',')[1]?.trim() || 'Nagpur',
      priority: (priority || 'MODERATE').toUpperCase(),
      location: {
        type: 'Point',
        coordinates: [parseFloat(lng), parseFloat(lat)]
      },
      address,
      reporter: {
        name: reporterName || 'Resident',
        contact: reporterContact || 'contact@municipal.gov'
      },
      status: status || 'PENDING'
    });

    await AuditLog.create({
      ticketId: newComplaint._id.toString(),
      action: 'COMPLAINT_CREATED',
      performedBy: 'CITIZEN_PORTAL',
      details: `Complaint intake via standard/AI form. Auto-geocoded coordinates: ${lat}, ${lng}`
    });

    res.status(201).json({ success: true, id: newComplaint._id.toString(), lat, lng });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. PUT /api/complaints/:id/status
app.put('/api/complaints/:id/status', async (req, res) => {
  const { id } = req.params;
  const { status, assignedOfficer, details } = req.body;

  try {
    const complaint = await Complaint.findById(id);
    if (!complaint) {
      return res.status(404).json({ error: 'Complaint not found' });
    }

    complaint.status = status;
    await complaint.save();

    await AuditLog.create({
      ticketId: id,
      action: 'STATUS_UPDATED',
      performedBy: assignedOfficer || 'SYSTEM',
      details: details || `Status changed to ${status}`
    });

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. PUT /api/complaints/:id/override (SLA Manual Override)
app.put('/api/complaints/:id/override', async (req, res) => {
  const { id } = req.params;
  try {
    const complaint = await Complaint.findById(id);
    if (!complaint) {
      return res.status(404).json({ error: 'Complaint not found' });
    }
    complaint.status = 'IN_INVESTIGATION';
    await complaint.save();

    await AuditLog.create({
      ticketId: id,
      action: 'SLA_OVERRIDDEN',
      performedBy: 'OPERATOR_DESK',
      details: 'Manual SLA breach override applied.'
    });

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 5. POST /api/complaints/bulk-dispatch
app.post('/api/complaints/bulk-dispatch', async (req, res) => {
  const { ticketIds } = req.body;
  if (!ticketIds || !Array.isArray(ticketIds)) {
    return res.status(400).json({ error: 'Missing ticketIds array' });
  }

  try {
    await Complaint.updateMany(
      { _id: { $in: ticketIds } },
      { $set: { status: 'DISPATCHED' } }
    );

    for (const tid of ticketIds) {
      await AuditLog.create({
        ticketId: tid,
        action: 'CREW_DISPATCHED',
        performedBy: 'OPERATOR_DESK',
        details: 'Dispatched default crew to site.'
      });
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 6. GET /api/crews
app.get('/api/crews', async (req, res) => {
  try {
    const crews = await FieldCrew.find();
    res.json(crews.map(c => ({
      id: c._id.toString(),
      crewName: c.crewName,
      department: c.department,
      assignedWard: c.assignedWard,
      status: c.status,
      activeTickets: c.activeTickets
    })));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 7. GET /api/officers
app.get('/api/officers', async (req, res) => {
  try {
    const officers = await User.find({ role: 'MUNICIPAL_OFFICER' });
    res.json(officers.map(o => ({
      id: o._id.toString(),
      name: o.name,
      email: o.email,
      department: o.department,
      ward: o.ward,
      createdAt: o.createdAt
    })));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 8. POST /api/officers
app.post('/api/officers', async (req, res) => {
  const { name, email, password, department, ward } = req.body;
  try {
    const newOfficer = await User.create({
      name,
      email,
      passwordHash: password,
      role: 'MUNICIPAL_OFFICER',
      department,
      ward
    });
    res.status(201).json({ success: true, id: newOfficer._id.toString() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 9. GET /api/audit-logs
app.get('/api/audit-logs', async (req, res) => {
  try {
    const logs = await AuditLog.find().sort({ timestamp: -1 }).limit(100);
    res.json(logs.map(l => ({
      id: l._id.toString(),
      ticketId: l.ticketId,
      action: l.action,
      performedBy: l.performedBy,
      details: l.details,
      timestamp: l.timestamp
    })));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 10. AUTHENTICATION API
app.post('/api/auth/signup', async (req, res) => {
  const { name, email, password, role, department, ward } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'Missing name, email, or password' });
  }

  try {
    const existing = await User.findOne({ email });
    if (existing) {
      return res.status(400).json({ error: 'User already exists' });
    }

    const newUser = await User.create({
      name,
      email,
      passwordHash: password,
      role: role || 'RESIDENT',
      department: department || 'Public',
      ward: ward || 'Ward 12'
    });

    res.status(201).json({
      success: true,
      user: {
        id: newUser._id.toString(),
        name: newUser.name,
        email: newUser.email,
        role: newUser.role,
        department: newUser.department,
        ward: newUser.ward
      }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Missing email or password' });
  }

  try {
    const user = await User.findOne({ email });
    if (!user || user.passwordHash !== password) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    res.json({
      success: true,
      user: {
        id: user._id.toString(),
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

// 11. GET /api/stats (Dashboard statistics)
app.get('/api/stats', async (req, res) => {
  try {
    const complaints = await Complaint.find();
    const crews = await FieldCrew.find();

    const totalActive = complaints.filter(c => c.status !== 'RESOLVED' && c.status !== 'Resolved').length;
    const urgentQueue = complaints.filter(c => c.priority === 'CRITICAL' || c.priority === 'HIGH' || c.priority === 'Urgent').length;
    const totalTickets = complaints.length;

    const counts = {
      Submitted: complaints.filter(c => c.status === 'PENDING' || c.status === 'Submitted').length,
      Assigned: complaints.filter(c => c.status === 'IN_INVESTIGATION' || c.status === 'Assigned').length,
      'In Investigation': complaints.filter(c => c.status === 'DISPATCHED' || c.status === 'In Investigation').length,
      Resolved: complaints.filter(c => c.status === 'RESOLVED' || c.status === 'Resolved').length
    };

    const priorityDistribution = {
      Urgent: complaints.filter(c => c.priority === 'CRITICAL' || c.priority === 'Urgent' || c.priority === 'HIGH').length,
      Moderate: complaints.filter(c => c.priority === 'MODERATE' || c.priority === 'Moderate').length,
      Low: complaints.filter(c => c.priority === 'LOW' || c.priority === 'Low').length
    };

    res.json({
      totalActive,
      urgentQueue,
      slaBreachedCount: 0,
      metrics: {
        totalTickets,
        breachedTotal: 0
      },
      counts,
      priorityDistribution,
      activeCrews: crews.length
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 12. POST /api/sql (SQL Explorer compatibility handler)
app.post('/api/sql', async (req, res) => {
  const { sql } = req.body;
  if (!sql) return res.status(400).json({ error: 'Missing query parameters' });

  try {
    if (sql.toLowerCase().includes('complaints')) {
      const complaints = await Complaint.find();
      const mapped = complaints.map(c => ({
        id: c._id.toString(),
        category: c.category,
        status: c.status,
        address: c.address,
        priority: c.priority
      }));
      res.json(mapped);
    } else {
      res.json([{ status: 'Success', message: 'MongoDB schema query returned successfully' }]);
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 13. POST /api/sql/dump
app.get('/api/sql/dump', async (req, res) => {
  try {
    const complaints = await Complaint.find();
    res.attachment('civicpulse_dump.json').json(complaints);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

// 14. GET /api/issues (Fetch all issues resolved as map markers)
app.get('/api/issues', async (req, res) => {
  try {
    const complaints = await Complaint.find().sort({ createdAt: -1 });
    res.json(complaints.map(c => ({
      id: c._id.toString(),
      title: c.title || `${c.category} Issue`,
      description: c.description,
      latitude: c.location.coordinates[1],
      longitude: c.location.coordinates[0],
      created_at: c.createdAt
    })));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 15. POST /api/issues (Create new issue)
app.post('/api/issues', async (req, res) => {
  let { title, description, latitude, longitude, extracted_location } = req.body;
  if (!title || !description) {
    return res.status(400).json({ error: 'Missing title or description' });
  }

  // Geocode missing or invalid coordinates
  if (latitude === undefined || longitude === undefined || latitude === null || longitude === null || isNaN(parseFloat(latitude)) || isNaN(parseFloat(longitude))) {
    const searchLoc = extracted_location || title;
    try {
      const coords = await getCoordsFromAddress(searchLoc);
      latitude = coords.lat;
      longitude = coords.lon;
    } catch (err) {
      console.error('Auto geocoding failed for issue:', err.message);
      latitude = 18.5204;
      longitude = 73.8567;
    }
  }

  try {
    const newComplaint = await Complaint.create({
      title,
      category: 'Road Repair / Pothole',
      description,
      landmark: title.split(',')[0],
      city: 'Nagpur',
      priority: 'MODERATE',
      location: {
        type: 'Point',
        coordinates: [parseFloat(longitude), parseFloat(latitude)] // [lng, lat]
      },
      address: extracted_location || title,
      reporter: {
        name: 'Resident',
        contact: 'contact@municipal.gov'
      },
      status: 'PENDING'
    });

    res.status(201).json({
      success: true,
      issue: {
        id: newComplaint._id.toString(),
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

// 16. GET /api/geocode/reverse (Reverse geocoding endpoint)
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

// 17. GET /api/geocode/search (Forward geocoding endpoint)
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

// 18. POST /api/chat (AI Chatbot NLP assistant)
app.post('/api/chat', (req, res) => {
  const { message, draft } = req.body;
  if (!message) {
    return res.status(400).json({ error: 'Missing message query' });
  }

  const lower = message.toLowerCase();
  
  const currentDraft = {
    category: draft?.category || null,
    priority: draft?.priority || 'MODERATE',
    landmark: draft?.landmark || null,
    city: draft?.city || null,
    formal_description: draft?.formal_description || null,
    reporter_name: draft?.reporter_name || null,
    contact: draft?.contact || null,
    lastAskedField: draft?.lastAskedField || null
  };

  if (lower.includes('water') || lower.includes('pipe') || lower.includes('leak') || lower.includes('sewage') || lower.includes('flood') || lower.includes('drain')) {
    currentDraft.category = 'Water Supply';
    currentDraft.priority = 'URGENT';
  } else if (lower.includes('pothole') || lower.includes('road') || lower.includes('crack') || lower.includes('street repair') || lower.includes('asphalt') || lower.includes('ycce')) {
    currentDraft.category = 'Road Repair / Pothole';
    currentDraft.priority = 'MODERATE';
  } else if (lower.includes('streetlight') || lower.includes('lamp') || lower.includes('dark') || lower.includes('light bulb') || lower.includes('blackout')) {
    currentDraft.category = 'Streetlight Outage';
    currentDraft.priority = 'LOW';
  } else if (lower.includes('garbage') || lower.includes('trash') || lower.includes('waste') || lower.includes('bin') || lower.includes('sanitation') || lower.includes('smell')) {
    currentDraft.category = 'Sanitation & Waste';
    currentDraft.priority = 'MODERATE';
  } else if (lower.includes('graffiti') || lower.includes('paint') || lower.includes('spray') || lower.includes('vandalism')) {
    currentDraft.category = 'Graffiti';
    currentDraft.priority = 'LOW';
  } else if (lower.includes('dumping') || lower.includes('debris') || lower.includes('illegal dump')) {
    currentDraft.category = 'Illegal Dumping';
    currentDraft.priority = 'MODERATE';
  }

  if (lower.includes('nagpur')) {
    currentDraft.city = 'Nagpur';
  } else {
    const cityMatches = message.match(/\bin\s+([A-Z][a-z]+)\b/);
    if (cityMatches && cityMatches[1]) {
      currentDraft.city = cityMatches[1];
    }
  }

  if (lower.includes('ycce clg') || lower.includes('ycce college') || lower.includes('ycce')) {
    currentDraft.landmark = 'YCCE College';
  } else {
    const landmarkMatches = message.match(/(?:at|near|on|in front of|opposite|in)\s+([A-Za-z0-9\s]+?)(?:\s+in\s+[A-Z]|\.|\n|$)/i);
    if (landmarkMatches && landmarkMatches[1]) {
      const lm = landmarkMatches[1].trim();
      if (lm.toLowerCase() !== currentDraft.city?.toLowerCase()) {
        currentDraft.landmark = lm;
      }
    }
  }

  const nameMatches = message.match(/(?:my name is|this is|i am|reporter is)\s+([A-Za-z\s]+)/i);
  if (nameMatches && nameMatches[1]) {
    currentDraft.reporter_name = nameMatches[1].trim();
  } else if (currentDraft.lastAskedField === 'reporter_name') {
    const cleanName = message.replace(/[.,]/g, '').trim();
    if (cleanName.length > 2 && cleanName.split(' ').length <= 3 && !['yes', 'okay', 'sure', 'ok'].includes(cleanName.toLowerCase())) {
      currentDraft.reporter_name = cleanName;
    }
  }

  const emailMatch = message.match(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/);
  const phoneMatch = message.match(/\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b/);
  if (emailMatch) {
    currentDraft.contact = emailMatch[0];
  } else if (phoneMatch) {
    currentDraft.contact = phoneMatch[0];
  } else if (currentDraft.lastAskedField === 'contact') {
    const cleanContact = message.replace(/[.,]/g, '').trim();
    if (cleanContact.length > 4 && !['yes', 'okay', 'ok'].includes(cleanContact.toLowerCase())) {
      currentDraft.contact = cleanContact;
    }
  }

  if (currentDraft.category && (currentDraft.landmark || currentDraft.city)) {
    const issueTerm = currentDraft.category === 'Road Repair / Pothole' ? 'large pothole' : 'issue';
    const locStr = [currentDraft.landmark, currentDraft.city].filter(Boolean).join(' in ');
    currentDraft.formal_description = `A ${issueTerm} has been reported near ${locStr}, posing a hazard to traffic.`;
  }

  const missing_fields = [];
  if (!currentDraft.category) missing_fields.push('category');
  if (!currentDraft.landmark && !currentDraft.city) missing_fields.push('location');
  if (!currentDraft.reporter_name) missing_fields.push('reporter_name');
  if (!currentDraft.contact) missing_fields.push('contact');

  let reply = '';
  if (missing_fields.includes('category')) {
    currentDraft.lastAskedField = 'category';
    reply = "I see. Could you clarify what category of issue this is? (e.g. Water Supply, Road Repair / Pothole)";
  } else if (missing_fields.includes('location')) {
    currentDraft.lastAskedField = 'location';
    reply = `I've noted the issue as ${currentDraft.category}. Could you please specify where this issue is located?`;
  } else if (missing_fields.includes('reporter_name')) {
    currentDraft.lastAskedField = 'reporter_name';
    const locStr = [currentDraft.landmark, currentDraft.city].filter(Boolean).join(' in ');
    reply = `I've logged the pothole location near ${locStr}. Could you please provide your name?`;
  } else if (missing_fields.includes('contact')) {
    currentDraft.lastAskedField = 'contact';
    reply = `Got it, ${currentDraft.reporter_name}. What is your contact info (email or phone) for status updates?`;
  } else {
    currentDraft.lastAskedField = null;
    reply = `Perfect! I have collected all the details. Please click 'Submit Report' to log the complaint.`;
  }

  const extracted_location = [currentDraft.landmark, currentDraft.city, "Maharashtra"].filter(Boolean).join(', ');

  res.json({
    category: currentDraft.category,
    priority: currentDraft.priority?.toUpperCase(),
    landmark: currentDraft.landmark,
    city: currentDraft.city,
    formal_description: currentDraft.formal_description,
    reporter_name: currentDraft.reporter_name,
    contact: currentDraft.contact,
    extracted_location,
    missing_fields,
    reply,
    lastAskedField: currentDraft.lastAskedField
  });
});

// Start Server
app.listen(PORT, () => {
  console.log(`CivicPulse backend server running on port ${PORT}`);
});
