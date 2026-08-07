/**
 * escalationEngine.js — Phase 1
 *
 * Automatic and manual escalation logic.
 * Called by the scheduled SLA checker and by the manual escalate endpoint.
 *
 * Escalation Levels
 * ─────────────────
 *   Level 1 → Department Supervisor
 *   Level 2 → Municipal Commissioner
 *
 * Auto-escalation fires when:
 *   - SLA deadline has passed
 *   - Complaint is NOT already RESOLVED or ESCALATED at Level 2
 */

const Complaint   = require('../models/Complaint');
const Escalation  = require('../models/Escalation');
const { computeSLAStatus } = require('./slaEngine');
const auditService         = require('./auditService');
const notificationEngine   = require('./notificationEngine');

const ESCALATION_TARGETS = {
  1: 'Department Supervisor',
  2: 'Municipal Commissioner'
};

/**
 * Escalate a single complaint one level up.
 *
 * @param {object} complaint      - Mongoose Complaint document
 * @param {string} reason         - Reason for escalation
 * @param {string} triggeredBy    - 'SYSTEM_AUTO' | 'MANUAL_OPERATOR'
 * @returns {Promise<object>}     - { escalated: bool, escalationRecord }
 */
async function escalateComplaint(complaint, reason, triggeredBy = 'SYSTEM_AUTO') {
  const previousStatus = complaint.lifecycleStatus;
  const currentLevel   = complaint.escalation?.level || 0;
  const newLevel       = Math.min(currentLevel + 1, 2);
  const target         = ESCALATION_TARGETS[newLevel];

  // Update complaint document
  complaint.lifecycleStatus       = 'ESCALATED';
  complaint.status                = 'ESCALATED';
  complaint.escalation.isEscalated = true;
  complaint.escalation.level      = newLevel;
  complaint.escalation.escalatedAt = new Date();
  complaint.escalation.reason     = reason;
  complaint.escalation.target     = target;
  complaint.sla.status            = 'BREACHED';

  await complaint.save();

  // Create escalation record
  const escalationRecord = await Escalation.create({
    complaintId:      complaint._id,
    referenceNumber:  complaint.referenceNumber || null,
    previousStatus,
    reason,
    escalationLevel:  newLevel,
    escalationTarget: target,
    triggeredBy
  });

  // Audit log
  await auditService.log(
    complaint._id.toString(),
    'COMPLAINT_ESCALATED',
    triggeredBy === 'SYSTEM_AUTO' ? 'SYSTEM' : 'OPERATOR_DESK',
    `Escalated to Level ${newLevel} (${target}). Reason: ${reason}`
  );

  // Simulated notification
  await notificationEngine.notify(complaint, 'COMPLAINT_ESCALATED', { target });

  return { escalated: true, escalationRecord };
}

/**
 * Scan all active complaints for SLA breaches and auto-escalate.
 * Called on a schedule from server.js.
 *
 * @returns {Promise<{ checked: number, escalated: number }>}
 */
async function runEscalationScan() {
  const now = new Date();

  // Only look at complaints that have an SLA deadline and aren't done/escalated at max level
  const candidates = await Complaint.find({
    'sla.deadline': { $lt: now, $ne: null },
    lifecycleStatus: { $nin: ['RESOLVED', 'ESCALATED'] }
  });

  let escalatedCount = 0;

  for (const complaint of candidates) {
    const slaStatus = computeSLAStatus(complaint.sla, complaint.lifecycleStatus);

    if (slaStatus === 'BREACHED') {
      // Check if already at max escalation level
      if (complaint.escalation?.isEscalated && complaint.escalation?.level >= 2) {
        continue; // Already at maximum escalation
      }

      await escalateComplaint(
        complaint,
        `SLA deadline breached. Allotted: ${complaint.sla.hoursAllotted}h. Priority: ${complaint.priority}.`,
        'SYSTEM_AUTO'
      );
      escalatedCount++;
    }
  }

  // Also emit SLA_WARNING notifications for complaints approaching deadline
  const warningCandidates = await Complaint.find({
    'sla.deadline': { $ne: null },
    'sla.status': { $in: ['ACTIVE', 'WARNING'] },
    lifecycleStatus: { $nin: ['RESOLVED', 'ESCALATED'] }
  });

  for (const complaint of warningCandidates) {
    const newStatus = computeSLAStatus(complaint.sla, complaint.lifecycleStatus);

    if (newStatus !== complaint.sla.status) {
      complaint.sla.status = newStatus;
      await complaint.save();

      if (newStatus === 'WARNING') {
        await notificationEngine.notify(complaint, 'SLA_WARNING');
        await auditService.log(
          complaint._id.toString(),
          'SLA_WARNING',
          'SYSTEM',
          `SLA entering warning zone. Deadline: ${complaint.sla.deadline.toISOString()}`
        );
      }
    }
  }

  console.log(`[EscalationEngine] Scan complete. Checked: ${candidates.length + warningCandidates.length}, Escalated: ${escalatedCount}`);
  return { checked: candidates.length, escalated: escalatedCount };
}

module.exports = { escalateComplaint, runEscalationScan, ESCALATION_TARGETS };
