# CodeRush 2.0 | Team Project Repository

## Project Information

- **Team Name:** Wannabe Vidharbh's
- **Project Title:** Community Redressal Planner
- **Track/Theme:** SDG-01

---

## Project Description

**Community Redressal Planner** is a multilingual, privacy-aware civic redressal system that transforms resident complaints into deduplicated, prioritized, accountable workflows with transparent status updates, escalation paths, and measurable service-level outcomes.

### Core Objectives & Design

- **Resident Agency & Accessibility:** Enables residents to report infrastructure, sanitation, safety, and local service gaps in multiple languages with automatic redaction of personal data to prevent public doxxing.
- **Smart Triage & Routing:** Extracts entities (location, urgency, category) using AI, clusters duplicate complaints semantically, and routes tasks to appropriate municipal departments without replacing human oversight.
- **Operational Transparency:** Provides operations teams with interactive geographic hotspot maps, SLA risk tracking, audit logs, and human override capabilities to ensure fairness across all neighborhoods.

---

## Technical Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend Framework** | Next.js 15 (React + TypeScript) | Resident portal and officer dashboard UI |
| **UI Components** | shadcn/ui | Modern, accessible UI components |
| **Styling** | Tailwind CSS | Responsive and fast UI development |
| **Forms** | React Hook Form | Complaint submission and validation |
| **Icons** | Lucide React | Clean, consistent iconography |
| **Maps** | Leaflet.js + OpenStreetMap | Complaint locations, hotspots, and jurisdiction maps |
| **Charts & Analytics** | Chart.js | Complaint trends, SLA metrics, and department performance |
| **Backend Framework** | FastAPI | REST APIs and AI service integration |
| **Language** | Python 3.12 | Backend logic and AI processing |
| **Authentication** | Supabase Auth (Google OAuth) | Resident and officer authentication |
| **Database** | PostgreSQL (Supabase) | Store users, complaints, statuses, and audit logs |
| **File Storage** | Supabase Storage | Store uploaded complaint images and audio |
| **ORM** | SQLAlchemy | Database interaction |
| **API Validation** | Pydantic | Request and response validation |
| **LLM** | Gemini 2.5 Flash | Complaint understanding, entity extraction, routing explanation, multilingual support |
| **Embeddings** | BAAI/bge-small-en-v1.5 | Generate semantic embeddings for duplicate detection |
| **Vector Database** | Qdrant | Store and search complaint embeddings for duplicate clustering |
| **Speech-to-Text** | Whisper | Convert voice complaints into text |
| **Image Processing** | OpenCV | Basic image preprocessing (optional) |
| **AI Framework** | LangChain | Build AI workflow for extraction, routing, and explanations |
| **Notifications** | Resend / EmailJS | Email notifications for complaint updates (optional) |
| **Deployment (Frontend)** | Vercel | Host the Next.js application |
| **Deployment (Backend)** | Render | Deploy FastAPI backend |
| **Version Control** | Git + GitHub | Collaboration and source code management |
| **API Testing** | Postman | Test backend APIs |
| **Documentation** | Swagger UI (FastAPI) | Automatically generated API documentation |

---

## Setup and Installation

1. Clone & Install
git clone https://github.com/ylulla1221/coderush2.0_wannabevidharbh-s.git

cd coderush2.0_wannabevidharbh-s

# Install the Node/Express backend dependencies

npm install
2. Configure Environment
Create a .env file in the project root:

# ── MongoDB ──────────────────────────────

MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/civicpulse

# ── Server ───────────────────────────────

PORT=3000

# ── AI Service: LLM (BharatCode / OpenAI-compatible) ──

BHARATCODE_API_KEY=your_api_key

LLM_BASE_URL=https://your-llm-endpoint/v1

LLM_MODEL=your-model-name

LLM_TEMPERATURE=0.1

LLM_MAX_TOKENS=1024

LLM_TIMEOUT=120

# ── AI Service: Embeddings + Qdrant ──────

EMBEDDING_MODEL=BAAI/bge-base-en-v1.5

QDRANT_URL=https://your-qdrant-endpoint

QDRANT_API_KEY=your_qdrant_key

QDRANT_COLLECTION=civicflow_complaints

On first run, the Express server auto-seeds default users (operator, officers, residents) and field crews if the database is empty.
3. Start the Express Backend (API + Frontend)
# Production

npm start

# Development (auto-reload with nodemon)

npm run dev

Once running:

🌐 App (Resident + Dashboard) → http://localhost:3000
🔌 API base → http://localhost:3000/api

The vanilla-JS frontend in frontend/public is served statically by Express — no separate frontend build step is required.
4. Start the AI Pipeline Service (FastAPI)
cd backend

# Install Python dependencies (create a venv first if you prefer)

pip install fastapi uvicorn pydantic httpx python-dotenv \

            sentence-transformers qdrant-client

# Run the AI API

uvicorn app.main:app --reload --port 8000

❤️ Health check → http://localhost:8000/
🧠 Pipeline endpoint → POST http://localhost:8000/pipeline

curl -X POST http://localhost:8000/pipeline \

  -H "Content-Type: application/json" \

  -d '{"complaint_text":"Large pothole near YCCE College in Nagpur","location":"Nagpur"}'
5. Run the AI Test Suite
cd backend

pytest tests/
