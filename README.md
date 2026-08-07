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

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/community-redressal-planner.git

cd community-redressal-planner
```

### 2. Install Dependencies

#### Frontend

```bash
cd frontend

npm install
```

#### Backend

```bash
cd ../backend

pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in both the `frontend` and `backend` directories.

Refer to `.env.example` for all required variables.

Example backend `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
GEMINI_API_KEY=your_gemini_key
QDRANT_URL=your_qdrant_url
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 4. Start the Development Server

#### Frontend

```bash
npm run dev
```

#### Backend

```bash
python main.py
```

or

```bash
uvicorn main:app --reload
```
