# CivicPulse Municipal Redressal Hub - Running Instructions

This guide provides instructions on how to install, set up, and run the CivicPulse Municipal Redressal Hub locally.

## Prerequisites
Before running the application, make sure you have **Node.js** (v16 or higher) installed on your system.

## Setup and Running Steps

### 1. Install Dependencies
If you are running the project for the first time or after pulling new changes, install the required packages:
```bash
npm install
```

### 2. Initialize the Database (Optional)
The project comes pre-seeded with a database `civicpulse.db`. If you ever need to reset or reinitialize the database with default schema and seed data, run:
```bash
npm run init-db
```

### 3. Start the Server
To start the backend server, run:
```bash
npm start
```
*Note: Do not run `npm run dev` as there is no development/dev script configured in this project.*

### 4. Access the Application
Once the server is running, open your web browser and navigate to:
* **http://localhost:3000/login.html** - To login / sign up.
* **http://localhost:3000** - Main application interface (requires logging in).

## Available Scripts

In the project directory, you can run:

| Command | Action |
|---|---|
| `npm start` | Runs the server using `server.js` |
| `npm run init-db` | Runs `init_db.js` to reinitialize the SQLite database |
