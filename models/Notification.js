// Notification Model — Phase 1
// Simulated notification store. No email/SMS — internal log only.
const mongoose = require('mongoose');

const notificationSchema = new mongoose.Schema({
  complaintId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Complaint',
    required: true,
    index: true
  },

  referenceNumber: { type: String, default: null },

  // Notification event type
  event: {
    type: String,
    enum: [
      'COMPLAINT_SUBMITTED',
      'COMPLAINT_ASSIGNED',
      'SLA_WARNING',
      'COMPLAINT_ESCALATED',
      'COMPLAINT_RESOLVED',
      'STATUS_CHANGED'
    ],
    required: true
  },

  // Human-readable notification message
  message: { type: String, required: true },

  // Who this would be sent to
  recipientName:    { type: String, default: null },
  recipientContact: { type: String, default: null },

  // Additional data payload
  metadata: { type: mongoose.Schema.Types.Mixed, default: {} },

  read: { type: Boolean, default: false },

  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Notification', notificationSchema);
