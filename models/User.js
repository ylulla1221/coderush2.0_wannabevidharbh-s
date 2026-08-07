// User Model - RBAC roles: OPERATOR | MUNICIPAL_OFFICER | RESIDENT
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  passwordHash: { type: String, required: true },
  role: {
    type: String,
    enum: ['RESIDENT', 'MUNICIPAL_OFFICER', 'OPERATOR'],
    required: true
  },
  department: { type: String, default: 'Public' },
  ward: { type: String, default: 'Ward 12' },
  createdAt: { type: Date, default: Date.now }
});

module.exports = mongoose.model('User', userSchema);

