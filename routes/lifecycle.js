/**
 * routes/lifecycle.js — Phase 1
 *
 * REST API endpoints for Complaint Lifecycle, SLA, Escalation, and Tracking.
 */

const express = require('express');
const router = express.Router();
const Complaint = require('../models/Complaint');
const Escalation = require('../models/Escalation');
const User = require('../models/User');

const auditService = require('../services/auditService');
const { getSLADisplay } = require('../services/slaEngine');
const { escalateComplaint, runEscalationScan } = require('../services/escalationEngine');
const notificationEngine = require('../services/notificationEngine');

// 1. GET /api/complaints/:id/status (Full status & SLA view)
router.get('/complaints/:id/status', async (req, res) => {
  try {
    const complaint = await Complaint.findById(req.params.id);
    if (!complaint) return res.status(404).json({ error: 'Complaint not found' });

    const timeline = await auditService.getTimeline(complaint._id.toString());
    const sla = getSLADisplay(complaint);
    let escalationDetails = null;

    if (complaint.escalation?.isEscalated) {
      escalationDetails = await Escalation.findOne({ complaintId: complaint._id }).sort({ escalatedAt: -1 });
    }

    res.json({
      id: complaint._id.toString(),
      referenceNumber: complaint.referenceNumber,
      lifecycleStatus: complaint.lifecycleStatus,
      priority: complaint.priority,
      assignedDepartment: complaint.assignedDepartment,
      assignedOfficerName: complaint.assignedOfficerName,
      sla,
      escalation: escalationDetails,
      timeline
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 2. GET /api/complaints/:id/timeline (Audit trail only)
router.get('/complaints/:id/timeline', async (req, res) => {
  try {
    const timeline = await auditService.getTimeline(req.params.id);
    res.json(timeline);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 3. POST /api/complaints/:id/assign
router.post('/complaints/:id/assign', async (req, res) => {
  const { officerId, officerName } = req.body;
  
  try {
    const complaint = await Complaint.findById(req.params.id);
    if (!complaint) return res.status(404).json({ error: 'Complaint not found' });

    complaint.lifecycleStatus = 'ASSIGNED';
    complaint.assignedOfficerId = officerId || null;
    complaint.assignedOfficerName = officerName || 'Auto-Assigned Officer';
    
    await complaint.save();

    await auditService.log(
      complaint._id.toString(),
      'COMPLAINT_ASSIGNED',
      'SYSTEM',
      `Assigned to officer: ${complaint.assignedOfficerName}`
    );

    await notificationEngine.notify(complaint, 'COMPLAINT_ASSIGNED', { officerName: complaint.assignedOfficerName });

    res.json({ success: true, lifecycleStatus: complaint.lifecycleStatus });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 4. POST /api/complaints/:id/start
router.post('/complaints/:id/start', async (req, res) => {
  try {
    const complaint = await Complaint.findById(req.params.id);
    if (!complaint) return res.status(404).json({ error: 'Complaint not found' });

    complaint.lifecycleStatus = 'IN_PROGRESS';
    complaint.status = 'IN_PROGRESS'; // sync legacy status
    await complaint.save();

    await auditService.log(
      complaint._id.toString(),
      'WORK_STARTED',
      complaint.assignedOfficerName || 'OFFICER',
      'Work started on the complaint'
    );

    await notificationEngine.notify(complaint, 'STATUS_CHANGED', { newStatus: 'In Progress' });

    res.json({ success: true, lifecycleStatus: complaint.lifecycleStatus });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 5. POST /api/complaints/:id/resolve
router.post('/complaints/:id/resolve', async (req, res) => {
  const { resolutionNotes } = req.body;

  try {
    const complaint = await Complaint.findById(req.params.id);
    if (!complaint) return res.status(404).json({ error: 'Complaint not found' });

    complaint.lifecycleStatus = 'RESOLVED';
    complaint.status = 'RESOLVED';
    
    // Mark SLA completed if active/warning
    if (complaint.sla && complaint.sla.status !== 'BREACHED') {
       complaint.sla.status = 'COMPLETED';
    }
    
    await complaint.save();

    await auditService.log(
      complaint._id.toString(),
      'COMPLAINT_RESOLVED',
      complaint.assignedOfficerName || 'OFFICER',
      resolutionNotes || 'Complaint resolved successfully.'
    );

    await notificationEngine.notify(complaint, 'COMPLAINT_RESOLVED');

    res.json({ success: true, lifecycleStatus: complaint.lifecycleStatus, slaStatus: complaint.sla.status });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 6. POST /api/complaints/:id/escalate (Manual)
router.post('/complaints/:id/escalate', async (req, res) => {
  const { reason } = req.body;

  try {
    const complaint = await Complaint.findById(req.params.id);
    if (!complaint) return res.status(404).json({ error: 'Complaint not found' });

    if (complaint.lifecycleStatus === 'RESOLVED') {
      return res.status(400).json({ error: 'Cannot escalate a resolved complaint.' });
    }

    const result = await escalateComplaint(complaint, reason || 'Manual operator escalation', 'MANUAL_OPERATOR');

    res.json({ success: true, escalation: result.escalationRecord });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 7. GET /api/notifications
router.get('/notifications', async (req, res) => {
  const { complaintId } = req.query;
  try {
    const notifications = complaintId 
      ? await notificationEngine.getNotifications(complaintId)
      : await notificationEngine.getNotifications(); // Note: getNotifications() needs tweak for all, or use Notification.find() directly
      
    // Quick fix if complaintId is not provided, fetch recent 50
    const Notification = require('../models/Notification');
    const result = complaintId 
        ? await Notification.find({ complaintId }).sort({ createdAt: -1 }).lean()
        : await Notification.find().sort({ createdAt: -1 }).limit(50).lean();

    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 8. GET /api/track/:referenceNumber
router.get('/track/:referenceNumber', async (req, res) => {
  try {
    const complaint = await Complaint.findOne({ referenceNumber: req.params.referenceNumber });
    if (!complaint) return res.status(404).json({ error: 'Complaint not found. Check reference number.' });

    const timeline = await auditService.getTimeline(complaint._id.toString());
    const sla = getSLADisplay(complaint);

    res.json({
      referenceNumber: complaint.referenceNumber,
      title: complaint.title,
      category: complaint.category,
      lifecycleStatus: complaint.lifecycleStatus,
      priority: complaint.priority,
      assignedDepartment: complaint.assignedDepartment,
      expectedResolutionTime: sla.deadline,
      slaStatus: sla.status,
      timeline
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// 9. POST /api/admin/escalation-check (Manual trigger for testing)
router.post('/admin/escalation-check', async (req, res) => {
  try {
    const result = await runEscalationScan();
    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
