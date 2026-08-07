/**
 * notificationEngine.js — Phase 1
 *
 * Simulated notification engine. No SMS, no email, no external APIs.
 * All notifications are stored in MongoDB for later retrieval.
 *
 * Events
 * ──────
 *   COMPLAINT_SUBMITTED  → after complaint is created
 *   COMPLAINT_ASSIGNED   → after officer assignment
 *   SLA_WARNING          → when SLA enters WARNING zone
 *   COMPLAINT_ESCALATED  → when complaint is escalated
 *   COMPLAINT_RESOLVED   → when complaint is resolved
 *   STATUS_CHANGED       → generic status transition
 */

const Notification = require('../models/Notification');

/**
 * Compose a human-readable notification message for each event type.
 */
function composeMessage(event, complaint, extra = {}) {
  const ref  = complaint.referenceNumber || complaint._id.toString().slice(-6).toUpperCase();
  const dept = complaint.assignedDepartment || 'the assigned department';

  switch (event) {
    case 'COMPLAINT_SUBMITTED':
      return `Your complaint (Ref: ${ref}) has been submitted and is being processed by the AI system.`;

    case 'COMPLAINT_ASSIGNED':
      return `Your complaint (Ref: ${ref}) has been assigned to ${extra.officerName || dept}. Work will begin shortly.`;

    case 'SLA_WARNING':
      return `Attention: Complaint (Ref: ${ref}) is approaching its SLA deadline. Immediate action required.`;

    case 'COMPLAINT_ESCALATED':
      return `Complaint (Ref: ${ref}) has been escalated to ${extra.target || 'Department Supervisor'} due to SLA breach.`;

    case 'COMPLAINT_RESOLVED':
      return `Your complaint (Ref: ${ref}) has been resolved. Thank you for reporting this civic issue.`;

    case 'STATUS_CHANGED':
      return `Complaint (Ref: ${ref}) status updated to: ${extra.newStatus || 'updated'}.`;

    default:
      return `Update on your complaint (Ref: ${ref}).`;
  }
}

/**
 * Create and persist a notification.
 *
 * @param {object} complaint  - Mongoose complaint document
 * @param {string} event      - Notification event key
 * @param {object} extra      - Optional extra data (officerName, target, newStatus)
 * @returns {Promise<Document>}
 */
async function notify(complaint, event, extra = {}) {
  try {
    const message = composeMessage(event, complaint, extra);

    return await Notification.create({
      complaintId:      complaint._id,
      referenceNumber:  complaint.referenceNumber || null,
      event,
      message,
      recipientName:    complaint.reporter?.name    || null,
      recipientContact: complaint.reporter?.contact || null,
      metadata:         extra
    });
  } catch (err) {
    console.error(`[notificationEngine] Failed to create notification: ${err.message}`);
  }
}

/**
 * Get all notifications for a complaint.
 *
 * @param {string} complaintId
 * @returns {Promise<Array>}
 */
async function getNotifications(complaintId) {
  return Notification
    .find({ complaintId })
    .sort({ createdAt: 1 })
    .lean();
}

module.exports = { notify, getNotifications };
