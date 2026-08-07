# CivicPulse Municipal Redressal Hub - Running Instructions

This guide provides instructions on how to install, set up, and run the CivicPulse Municipal Redressal Hub locally.

## Prerequisites
Before running the application, make sure you have:
- **Node.js** (v16 or higher) installed on your system.
- **MongoDB** running locally on port `27017` or configured via remote URI.

## Setup and Running Steps

### 1. Install Dependencies
If you are running the project for the first time or after pulling new changes, install the required packages:
```bash
npm install
```

### 2. Configure Environment (Optional)
By default, the application connects to a local MongoDB instance at `mongodb://localhost:27017/civicpulse`. To point to a custom instance, set the `MONGODB_URI` environment variable.

### 3. Start the Server
To start the backend server, run:
```bash
npm start
```
The database will automatically seed with default resident, operator, and field crew profiles on the first run.

### 4. Access the Application
Once the server is running, navigate to:
* **http://localhost:3000/login.html** - Login/Registration page.
* **http://localhost:3000** - Resident Portal & Operations Desk.

## Available Scripts

In the project directory, you can run:

| Command | Action |
|---|---|
| `npm start` | Launches the server and connects to MongoDB |
