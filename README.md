# CodeRush 2.0 | Team Project Repository

## Project Information

- **Team Name:** Wannabe Vidharbh's
- **Project Title:** Community Redressal Planner
- **Track/Theme:** SDG-01

---

# Project Description

**Community Redressal Planner** is a multilingual, privacy-aware civic redressal system that transforms resident complaints into deduplicated, prioritized, accountable workflows with transparent status updates, escalation paths, and measurable service-level outcomes.

## Core Objectives & Design

### Resident Agency & Accessibility
- Enables residents to report infrastructure, sanitation, safety, and local service gaps in multiple languages.
- Automatically redacts personal information to prevent public doxxing.
- Supports text, image, and voice complaint submissions.

### Smart Triage & Routing
- Uses AI to extract:
  - Location
  - Urgency
  - Complaint Category
- Detects duplicate complaints using semantic similarity.
- Routes complaints to the appropriate municipal department.
- Keeps humans in the loop for review and overrides.

### Operational Transparency
- Interactive hotspot maps for complaint visualization.
- SLA monitoring and risk tracking.
- Complete audit logs for accountability.
- Human override capabilities to ensure fairness across neighborhoods.

---

# Technical Stack

| Layer | Technology | Purpose |
|--------|------------|---------|
| **Frontend Framework** | Next.js 15 (React + TypeScript) | Resident portal and officer dashboard |
| **UI Components** | shadcn/ui | Accessible modern UI |
| **Styling** | Tailwind CSS | Responsive styling |
| **Forms** | React Hook Form | Complaint forms and validation |
| **Icons** | Lucide React | Icon library |
| **Maps** | Leaflet.js + OpenStreetMap | Complaint locations & hotspot maps |
| **Charts & Analytics** | Chart.js | Complaint statistics & SLA analytics |
| **Backend Framework** | FastAPI | REST APIs & AI integration |
| **Language** | Python 3.12 | Backend development |
| **Authentication** | Supabase Auth (Google OAuth) | Resident & officer authentication |
| **Database** | PostgreSQL (Supabase) | Complaint and user data |
| **File Storage** | Supabase Storage | Images & voice uploads |
| **ORM** | SQLAlchemy | Database interaction |
| **API Validation** | Pydantic | Request & response validation |
| **LLM** | Gemini 2.5 Flash | Complaint understanding, multilingual support |
| **Embeddings** | BAAI/bge-small-en-v1.5 | Semantic embeddings |
| **Vector Database** | Qdrant | Duplicate complaint detection |
| **Speech-to-Text** | Whisper | Voice complaint transcription |
| **Image Processing** | OpenCV | Optional image preprocessing |
| **AI Framework** | LangChain | AI workflow orchestration |
| **Notifications** | Resend / EmailJS | Complaint update emails |
| **Deployment (Frontend)** | Vercel | Frontend hosting |
| **Deployment (Backend)** | Render | Backend hosting |
| **Version Control** | Git + GitHub | Source code management |
| **API Testing** | Postman | API testing |
| **Documentation** | Swagger UI (FastAPI) | Auto-generated API documentation |

---

# Setup and Installation

## 1. Clone the Repository

```bash
git clone https://github.com/your-org/community-redressal-planner.git

cd community-redressal-planner
```

---

## 2. Install Dependencies

### Frontend

```bash
cd frontend
npm install
```

### Backend

```bash
cd ../backend
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Create a `.env` file inside both the **frontend** and **backend** directories.

Refer to the `.env.example` file.

### Backend `.env` Example

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

GEMINI_API_KEY=your_gemini_key

QDRANT_URL=your_qdrant_url

SUPABASE_URL=your_supabase_url

SUPABASE_KEY=your_supabase_key
```

---

## 4. Start the Development Servers

### Frontend

```bash
npm run dev
```

### Backend

Using Python:

```bash
python main.py
```

Or using Uvicorn:

```bash
uvicorn main:app --reload
```

---

# Project Highlights

- 🌐 Multilingual complaint submission
- 🔒 Privacy-aware personal data redaction
- 🤖 AI-powered complaint classification and routing
- 📍 Interactive GIS complaint mapping
- 🔁 Semantic duplicate detection
- 📊 SLA monitoring and analytics
- 📝 Complete audit logs
- 👨‍💼 Human-in-the-loop review system
- 📧 Email notifications for complaint updates
