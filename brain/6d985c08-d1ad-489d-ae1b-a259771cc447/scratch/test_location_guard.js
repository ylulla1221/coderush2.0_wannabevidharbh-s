// scratch/test_location_guard.js
const mongoose = require('mongoose');
require('dotenv').config({ path: 'c:/Users/Gaurav Tiple/Wannabevidharbh_SDG1/.env' });

console.log('URI:', process.env.MONGODB_URI);

async function runTest() {
  mongoose.connection.on('error', err => console.error('Mongoose connection error event:', err));
  mongoose.connection.on('connected', () => console.log('Mongoose connected event'));
  
  await mongoose.connect(process.env.MONGODB_URI);
  console.log('Connected to MongoDB, readyState:', mongoose.connection.readyState);

  const Complaint = require('c:/Users/Gaurav Tiple/Wannabevidharbh_SDG1/models/Complaint');
  const complaints = await Complaint.find().limit(5);
  console.log(`Found ${complaints.length} complaints.`);
  
  await mongoose.disconnect();
}

runTest().catch(console.error);
