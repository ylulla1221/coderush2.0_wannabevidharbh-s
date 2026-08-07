/**
 * slaEngine.js — Phase 1
 *
 * Modular SLA calculation and status computation.
 * Called immediately after a complaint is created and routed.
 *
 * SLA Mapping
 * ───────────
 *   CRITICAL → 4 hours
 *   HIGH     → 12 hours
 *   MODERATE → 48 hours  (2 days)
 *   LOW      → 120 hours (5 days)
 *
 * SLA Statuses
 * ────────────
 *   ACTIVE    → within deadline, > WARNING_THRESHOLD remaining
 *   WARNING   → within deadline but < WARNING_THRESHOLD (20%) remaining
 *   BREACHED  → past deadline and not resolved
 *   COMPLETED → resolved before deadline
 */

// Hours per priority level
const SLA_HOURS = {
  CRITICAL: 4,
  HIGH:     12,
  MODERATE: 48,
  LOW:      120
};

// When remaining fraction drops below this, status becomes WARNING
const WARNING_THRESHOLD = 0.20;

/**
 * Compute the SLA deadline and initial status for a new complaint.
 *
 * @param {string} priority  - 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'
 * @param {Date}   createdAt - Complaint creation timestamp
 * @returns {{ hoursAllotted: number, deadline: Date, status: string }}
 */
function assignSLA(priority, createdAt = new Date()) {
  const normalised = (priority || 'MODERATE').toUpperCase();
  const hours = SLA_HOURS[normalised] ?? SLA_HOURS.MODERATE;

  const deadline = new Date(createdAt.getTime() + hours * 60 * 60 * 1000);

  return {
    hoursAllotted: hours,
    deadline,
    status: 'ACTIVE'
  };
}

/**
 * Recompute the live SLA status based on current time.
 *
 * @param {object} sla         - Complaint's sla sub-document
 * @param {string} lifecycleStatus - Current lifecycle status
 * @returns {string} New SLA status string
 */
function computeSLAStatus(sla, lifecycleStatus) {
  if (!sla || !sla.deadline) return 'ACTIVE';

  // Already completed — keep as COMPLETED
  if (sla.status === 'COMPLETED' || lifecycleStatus === 'RESOLVED') {
    return 'COMPLETED';
  }

  const now     = Date.now();
  const created = sla.deadline.getTime() - sla.hoursAllotted * 60 * 60 * 1000;
  const total   = sla.deadline.getTime() - created;
  const remaining = sla.deadline.getTime() - now;

  if (remaining <= 0) return 'BREACHED';

  const fractionLeft = remaining / total;
  if (fractionLeft < WARNING_THRESHOLD) return 'WARNING';

  return 'ACTIVE';
}

/**
 * Build a human-readable remaining time string.
 *
 * @param {Date} deadline
 * @returns {string} e.g. "3h 42m remaining" or "BREACHED 2h 10m ago"
 */
function getRemainingTimeString(deadline) {
  if (!deadline) return 'No SLA assigned';

  const diffMs = new Date(deadline).getTime() - Date.now();
  const absMs  = Math.abs(diffMs);

  const hours   = Math.floor(absMs / (1000 * 60 * 60));
  const minutes = Math.floor((absMs % (1000 * 60 * 60)) / (1000 * 60));

  const label = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  return diffMs >= 0
    ? `${label} remaining`
    : `BREACHED ${label} ago`;
}

/**
 * Generate the full SLA display object for API responses.
 *
 * @param {object} complaint - Mongoose complaint document
 * @returns {object}
 */
function getSLADisplay(complaint) {
  const sla = complaint.sla || {};
  const liveStatus = computeSLAStatus(sla, complaint.lifecycleStatus);

  return {
    hoursAllotted:  sla.hoursAllotted || null,
    deadline:       sla.deadline      || null,
    status:         liveStatus,
    remainingTime:  getRemainingTimeString(sla.deadline),
    createdAt:      complaint.createdAt
  };
}

module.exports = { assignSLA, computeSLAStatus, getRemainingTimeString, getSLADisplay, SLA_HOURS };
