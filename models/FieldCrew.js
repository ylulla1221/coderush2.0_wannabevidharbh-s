const mongoose = require('mongoose');

const fieldCrewSchema = new mongoose.Schema({
  crewName: { type: String, required: true },
  department: { type: String, required: true },
  assignedWard: { type: String, required: true },
  status: { type: String, default: 'Available' },
  activeTickets: { type: Number, default: 0 }
});

module.exports = mongoose.model('FieldCrew', fieldCrewSchema);
