// Complaint Model - GeoJSON 2dsphere for spatial queries
const mongoose = require('mongoose');

const complaintSchema = new mongoose.Schema({
  // ─── Existing fields (unchanged) ─────────────────────────────────────────
  title: String,
  category: { type: String, required: true },
  description: String,
  landmark: String,
  city: String,
  priority: {
    type: String,
    enum: ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'],
    default: 'MODERATE'
  },
  location: {
    type: {
      type: String,
      enum: ['Point'],
      default: 'Point'
    },
    coordinates: {
      type: [Number],
      required: true
    } // [longitude, latitude]
  },
  address: String,
  reporter: {
    name: String,
    contact: String
  },
  status: {
    type: String,
    default: 'PENDING'
  },
  createdAt: {
    type: Date,
    default: Date.now
  },

  // ─── Phase 1: Unique reference number ────────────────────────────────────
  referenceNumber: {
    type: String,
    unique: true,
    sparse: true   // allows null for seeded legacy complaints
  },

  // ─── Phase 1: Complaint Lifecycle ────────────────────────────────────────
  lifecycleStatus: {
    type: String,
    enum: ['SUBMITTED', 'AI_PROCESSED', 'ROUTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED'],
    default: 'SUBMITTED'
  },

  // ─── Phase 1: Assignment ─────────────────────────────────────────────────
  assignedDepartment: { type: String, default: null },
  assignedOfficerId:  { type: mongoose.Schema.Types.ObjectId, ref: 'User', default: null },
  assignedOfficerName: { type: String, default: null },

  // ─── Phase 1: SLA Engine ─────────────────────────────────────────────────
  sla: {
    hoursAllotted: { type: Number, default: null },
    deadline:      { type: Date,   default: null },
    status: {
      type: String,
      enum: ['ACTIVE', 'WARNING', 'BREACHED', 'COMPLETED'],
      default: 'ACTIVE'
    }
  },

  // ─── Phase 1: Escalation ─────────────────────────────────────────────────
  escalation: {
    isEscalated:  { type: Boolean, default: false },
    level:        { type: Number,  default: 0 },
    escalatedAt:  { type: Date,    default: null },
    reason:       { type: String,  default: null },
    target:       { type: String,  default: null }
  }
});

// Spatial index for geolocation queries
complaintSchema.index({ location: '2dsphere' });

module.exports = mongoose.model('Complaint', complaintSchema);
