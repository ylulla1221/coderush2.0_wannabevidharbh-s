/**
 * auditService.js — Phase 1
 *
 * Thin wrapper around the existing AuditLog model.
 * All existing audit log writes in server.js continue to work unchanged.
 * New Phase 1 code calls this helper for consistency.
 */

const AuditLog = require('../models/AuditLog');

/**
 * Write an audit entry.
 *
 * @param {string} ticketId    - Complaint MongoDB _id (as string)
 * @param {string} action      - Action key e.g. 'COMPLAINT_SUBMITTED'
 * @param {string} actor       - Who performed the action e.g. 'CITIZEN_PORTAL', 'SYSTEM', officer name
 * @param {string} details     - Human-readable description
 * @returns {Promise<Document>} The created AuditLog document
 */
async function log(ticketId, action, actor, details) {
  try {
    return await AuditLog.create({ ticketId, action, performedBy: actor, details });
  } catch (err) {
    console.error(`[auditService] Failed to write audit log: ${err.message}`);
  }
}

/**
 * Retrieve ordered audit trail for a specific complaint.
 *
 * @param {string} ticketId
 * @returns {Promise<Array>} Array of audit entries sorted by timestamp ascending
 */
async function getTimeline(ticketId) {
  return AuditLog
    .find({ ticketId })
    .sort({ timestamp: 1 })
    .lean();
}

module.exports = { log, getTimeline };
