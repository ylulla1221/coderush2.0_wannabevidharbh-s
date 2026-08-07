const mongoose = require('mongoose');

const auditLogSchema = new mongoose.Schema({
  ticketId: { type: String, required: true },
  action: { type: String, required: true },
  performedBy: { type: String, required: true },
  details: { type: String },
  timestamp: { type: Date, default: Date.now }
});

module.exports = mongoose.model('AuditLog', auditLogSchema);
