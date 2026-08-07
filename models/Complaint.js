const mongoose = require('mongoose');

const complaintSchema = new mongoose.Schema({
  title: String,
  category: String,
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
  }
});

// Spatial index for geolocation queries
complaintSchema.index({ location: '2dsphere' });

module.exports = mongoose.model('Complaint', complaintSchema);
