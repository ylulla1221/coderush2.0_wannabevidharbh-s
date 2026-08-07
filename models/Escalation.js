// Escalation Model — Phase 1
// Records every escalation event for a complaint.
const mongoose = require('mongoose');

const ESCALATION_TARGETS = {
  1: 'Department Supervisor',
  2: 'Municipal Commissioner'
};

const escalationSchema = new mongoose.Schema({
  complaintId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Complaint',
    required: true,
    index: true
  },

  // Human-readable complaint reference
  referenceNumber: { type: String, default: null },

  // What status the complaint was in before escalation
  previousStatus: { type: String, required: true },

  // Escalation metadata
  reason:          { type: String, required: true },
  escalationLevel: { type: Number, required: true, default: 1 },
  escalationTarget: {
    type: String,
    default: function () {
      return ESCALATION_TARGETS[this.escalationLevel] || 'Department Supervisor';
    }
  },

  // Whether this was triggered automatically by SLA breach or manually
  triggeredBy: {
    type: String,
    enum: ['SYSTEM_AUTO', 'MANUAL_OPERATOR'],
    default: 'SYSTEM_AUTO'
  },

  escalatedAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Escalation', escalationSchema);
module.exports.ESCALATION_TARGETS = ESCALATION_TARGETS;
