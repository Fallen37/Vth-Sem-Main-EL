# 🌟 Autism Science Tutor

An AI-powered science tutor designed specifically for autistic students aged 10-16 (Indian grades 5-10). The system uses Retrieval-Augmented Generation (RAG) to provide personalized, curriculum-aligned science education with extensive accommodations for diverse learning needs, including non-verbal students and those requiring guardian assistance.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-19.2-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Frontend Pages](#frontend-pages)
- [Backend Services](#backend-services)
- [Database Models](#database-models)
- [Testing](#testing)
- [Accessibility Features](#accessibility-features)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The Autism Science Tutor is a comprehensive educational platform that adapts to each student's unique learning needs. It combines:

- **RAG-based AI tutoring** using curriculum-aligned content
- **Multimodal interaction** (text, voice, images)
- **Adaptive learning profiles** that evolve with the student
- **Sensory-friendly interface** with calm mode and break features
- **Guardian assistance** for students who need support
- **Progress tracking** with child-friendly visualizations

### Target Audience

- **Primary Users**: Autistic students aged 10-16 (grades 5-10)
- **Secondary Users**: Parents, guardians, and teachers
- **Supported Curricula**: Indian CBSE and State Board syllabi

---

## Key Features

### 🤖 AI-Powered Tutoring
- RAG-based knowledge retrieval from uploaded curriculum materials
- Context-aware responses aligned with student's grade and syllabus
- Uncertainty indication when content is insufficient
- Suggested follow-up questions

### 📚 Multimodal Learning
- **Input**: Text, voice, images (textbook photos, handwritten questions)
- **Output**: Text explanations, audio narration, visual diagrams
- Seamless switching between modes during sessions

### 👤 Adaptive Profiles
- Tracks preferred output modes and explanation styles
- Remembers interaction speed preferences
- Adapts complexity based on comprehension patterns
- Persists preferences across sessions

### 🎯 Non-Verbal Support
- Clickable button options for common responses
- Comprehension feedback buttons (Understood/Partial/Not Understood)
- Explanation breakdown into selectable parts
- Minimal input required for full interaction

### 🎭 Avatar System
- Animated AI tutor avatar with state feedback
- States: Idle, Listening, Thinking, Explaining
- Student avatar representation
- Visual engagement without overwhelming

### 🧘 Calm Mode & Breaks
- Always-visible "Take a Break" button
- Guided breathing exercises
- Calming background music
- Emergency "I need help" button with guardian alerts

### 👨‍👩‍👧 Guardian Features
- Separate input section for guardian assistance
- Independence tracking over time
- Session history and progress reports
- Emergency alert notifications

### 📊 Progress Tracking
- Child-friendly progress visualizations
- Achievement system with positive reinforcement
- Topic strength and growth area identification
- Review recommendations based on comprehension

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   Web    │  │  Avatar  │  │ Multimodal│  │ Multimodal│       │
│  │Interface │  │  System  │  │  Input   │  │  Output  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
┌───────┴─────────────┴─────────────┴─────────────┴───────────────┐
│                         API Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ REST API │  │WebSocket │  │   Auth   │                       │
│  │ Gateway  │  │  Server  │  │          │                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
└───────┼─────────────┼─────────────┼─────────────────────────────┘
        │             │             │
┌───────┴─────────────┴─────────────┴─────────────────────────────┐
│                       Core Services                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   Chat   │  │   RAG    │  │ Profile  │  │ Progress │        │
│  │Orchestrator│ │  Engine  │  │ Service  │  │ Tracker  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Guardian │  │  Calm    │  │  Avatar  │                       │
│  │ Service  │  │  Mode    │  │ Service  │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
        │             │             │
┌───────┴─────────────┴─────────────┴─────────────────────────────┐
│                        Data Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Vector   │  │   User   │  │ Content  │                       │
│  │ Database │  │ Database │  │ Metadata │                       │
│  │(ChromaDB)│  │ (SQLite) │  │          │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Python 3.10+** | Core language |
| **FastAPI** | REST API framework |
| **SQLAlchemy 2.0** | ORM and database management |
| **SQLite + aiosqlite** | User and session database |
| **ChromaDB** | Vector database for RAG |
| **Sentence Transformers** | Local embedding generation |
| **OpenAI API** | LLM for response generation |
| **Pydantic** | Data validation and settings |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework |
| **TypeScript 5.9** | Type-safe JavaScript |
| **Vite** | Build tool and dev server |
| **React Router** | Client-side routing |
| **Axios** | HTTP client |
| **CSS3** | Styling with animations |

### Testing
| Technology | Purpose |
|------------|---------|
| **pytest** | Test framework |
| **pytest-asyncio** | Async test support |
| **Hypothesis** | Property-based testing |
| **httpx** | Async HTTP testing |

---

## Project Structure

```
autism-science-tutor/
├── .kiro/
│   └── specs/
│       └── autism-science-tutor/
│           ├── requirements.md      # EARS-pattern requirements
│           ├── design.md            # Technical design document
│           └── tasks.md             # Implementation task list
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # Application configuration
│
├── data/
│   └── tutor.db                     # SQLite database
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # API client with all endpoints
│   │   ├── context/
│   │   │   └── AuthContext.tsx      # Authentication state management
│   │   ├── pages/
│   │   │   ├── Login.tsx            # Login page
│   │   │   ├── Register.tsx         # Registration with success flow
│   │   │   ├── ProfileSetup.tsx     # 4-step preference wizard
│   │   │   ├── Dashboard.tsx        # Main dashboard with progress
│   │   │   ├── Chat.tsx             # Chat interface with avatars
│   │   │   ├── Auth.css             # Auth pages styling
│   │   │   ├── Dashboard.css        # Dashboard styling
│   │   │   └── Chat.css             # Chat interface styling
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript type definitions
│   │   ├── App.tsx                  # Main app with routing
│   │   ├── App.css                  # Global app styles
│   │   ├── index.css                # Base styles
│   │   └── main.tsx                 # React entry point
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── src/
│   ├── api/
│   │   ├── __init__.py              # Router exports
│   │   ├── auth.py                  # Authentication endpoints
│   │   ├── chat.py                  # Chat/message endpoints
│   │   ├── profile.py               # Learning profile endpoints
│   │   ├── content.py               # Content management endpoints
│   │   ├── progress.py              # Progress tracking endpoints
│   │   ├── guardian.py              # Guardian feature endpoints
│   │   ├── calm.py                  # Calm mode endpoints
│   │   ├── websocket.py             # WebSocket handlers
│   │   └── deps.py                  # Dependency injection
│   │
│   ├── app/
│   │   └── main.py                  # FastAPI application entry
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py              # Database initialization
│   │   ├── enums.py                 # Shared enumerations
│   │   ├── user.py                  # User model
│   │   ├── learning_profile.py      # Learning profile model
│   │   ├── session.py               # Session model
│   │   ├── document.py              # Document model
│   │   └── progress.py              # Progress model
│   │
│   └── services/
│       ├── __init__.py
│       ├── content_ingestion.py     # Document processing pipeline
│       ├── rag_engine.py            # RAG query and retrieval
│       ├── chat_orchestrator.py     # Conversation management
│       ├── profile_service.py       # Profile management
│       ├── progress_tracker.py      # Progress tracking
│       ├── guardian_service.py      # Guardian features
│       ├── calm_mode.py             # Calm mode features
│       ├── avatar_service.py        # Avatar state management
│       ├── multimodal_input.py      # Input processing
│       ├── multimodal_output.py     # Output generation
│       └── interface_preferences.py # UI preference management
│
├── tests/
│   ├── __init__.py
│   ├── test_content_ingestion.py    # Content service unit tests
│   ├── test_rag_engine.py           # RAG engine unit tests
│   ├── test_chat_orchestrator.py    # Chat service unit tests
│   ├── test_profile_service.py      # Profile service unit tests
│   ├── test_progress_tracker.py     # Progress service unit tests
│   ├── test_interface_preferences.py
│   ├── test_property_*.py           # Property-based tests (14 files)
│   └── ...
│
├── .env.example                     # Environment variables template
├── .gitignore
├── pyproject.toml                   # Python project configuration
└── README.md                        # This file
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- npm or yarn

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd autism-science-tutor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Application
APP_NAME="Autism Science Tutor"
APP_VERSION="0.1.0"
DEBUG=true
ENVIRONMENT=development

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/tutor.db

# ChromaDB (Vector Database)
CHROMA_PERSIST_DIRECTORY=./data/chroma
CHROMA_COLLECTION_NAME=curriculum_content

# OpenAI (optional - for advanced LLM features)
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Local Embeddings (default)
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
USE_LOCAL_EMBEDDINGS=true

# RAG Configuration
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=5
RAG_CONFIDENCE_THRESHOLD=0.6

# Session
SESSION_TIMEOUT_MINUTES=60

# Progress
REVIEW_COMPREHENSION_THRESHOLD=0.6
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./data/tutor.db` |
| `USE_LOCAL_EMBEDDINGS` | Use local sentence transformers | `true` |
| `RAG_SIMILARITY_THRESHOLD` | Minimum similarity for retrieval | `0.7` |
| `RAG_TOP_K` | Number of chunks to retrieve | `5` |
| `SESSION_TIMEOUT_MINUTES` | Session expiry time | `60` |

---

## Running the Application

### Quick Start (Recommended)

After installation, simply run:

```bash
python run.py
```

Then open **http://localhost:8080** in your browser. Both frontend and backend are served together!

### Development Mode (Separate Servers)

If you want hot-reloading for frontend development:

**Terminal 1 - Backend:**
```bash
python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Building the Frontend

If you make changes to the frontend, rebuild it:

```bash
cd frontend
npm run build
```

Then restart `python run.py` to see changes.

### Access Points

| Mode | Frontend | Backend API | API Docs |
|------|----------|-------------|----------|
| **Quick Start** | http://localhost:8080 | http://localhost:8080 | http://localhost:8080/docs |
| **Development** | http://localhost:5173 | http://localhost:8001 | http://localhost:8001/docs |

---

## API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login with email |
| GET | `/auth/me` | Get current user |

### Chat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/session` | Create new chat session |
| POST | `/chat/message` | Send message to AI tutor |
| POST | `/chat/comprehension` | Submit comprehension feedback |
| GET | `/chat/comprehension-options` | Get feedback button options |
| GET | `/chat/output-mode-options` | Get output mode options |

### Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/profile` | Get learning profile |
| PUT | `/profile` | Update learning profile |
| GET | `/profile/session-preferences` | Get session initialization preferences |

### Progress Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/progress/summary` | Get progress summary |
| GET | `/progress/achievements` | Get all achievements |
| GET | `/progress/review-topics` | Get topics needing review |
| POST | `/progress/record` | Record topic progress |

### Content Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/content/upload` | Upload educational document |
| GET | `/content/documents` | List documents with filters |
| GET | `/content/summary` | Get curriculum summary |
| POST | `/content/query` | Query content by curriculum |

### Guardian Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/guardian/link` | Link guardian to student |
| GET | `/guardian/students` | Get linked students |
| GET | `/guardian/independence/{student_id}` | Get independence metrics |

### Calm Mode Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calm/break` | Activate break mode |
| POST | `/calm/breathing` | Start breathing exercise |
| POST | `/calm/emergency` | Trigger emergency alert |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/chat/{user_id}` | Real-time chat connection |
| `/ws/avatar/{user_id}` | Avatar state updates |

---

## Frontend Pages

### Login Page (`/login`)
- Email-based authentication
- Link to registration
- Clean, calm design

### Register Page (`/register`)
- Name, email, role selection
- Grade and syllabus for students
- Success confirmation with login redirect

### Profile Setup (`/profile-setup`)
4-step wizard:
1. **Output Mode**: Text, audio, visual preferences
2. **Explanation Style**: Examples, diagrams, step-by-step
3. **Interaction Speed**: Slow, medium, fast
4. **Interface**: Dark mode, font size, reduced motion

### Dashboard (`/dashboard`)
- Welcome message with user name
- Animated avatar card (main CTA to chat)
- Progress overview with circular progress ring
- Streak counter
- Strength and growth areas
- Recent achievements
- Learning materials by subject
- Quick action cards
- Calm mode button

### Chat Interface (`/chat`)
- Large animated tutor avatar with states
- Student avatar with name
- Quick topic buttons
- Message history with timestamps
- Typing indicator
- Text input with send button
- Back to dashboard navigation
- Calm mode quick access

---

## Backend Services

### Content Ingestion Service
Handles document upload and processing:
- Supports PDF, DOCX, TXT, images
- Extracts text using appropriate parsers
- Chunks content for embedding
- Stores in ChromaDB with metadata

### RAG Engine
Core retrieval and generation:
- Embeds queries using sentence transformers
- Retrieves relevant chunks from vector DB
- Filters by grade and syllabus
- Generates contextual responses

### Chat Orchestrator
Manages conversation flow:
- Processes multimodal input
- Coordinates with RAG engine
- Handles comprehension feedback
- Manages explanation breakdowns
- Tracks session state

### Profile Service
Learning profile management:
- Creates default profiles for new users
- Updates preferences from interactions
- Provides session initialization data
- Tracks comprehension patterns

### Progress Tracker
Progress and achievement tracking:
- Records topic coverage
- Calculates comprehension levels
- Identifies review topics
- Awards achievements
- Generates progress summaries

### Guardian Service
Guardian assistance features:
- Links guardians to students
- Tracks input sources
- Calculates independence ratios
- Provides session history access

### Calm Mode Service
Sensory regulation features:
- Break mode activation
- Breathing exercise patterns
- Emergency alert handling
- Session pause management

### Avatar Service
Avatar state management:
- Tracks tutor and student states
- Emits state change events
- Provides animation configurations
- Supports multiple animation sets

---

## Database Models

### User
```python
- id: UUID (primary key)
- email: String (unique)
- name: String
- role: Enum (STUDENT, GUARDIAN, ADMIN)
- grade: Integer (5-10, for students)
- syllabus: Enum (CBSE, STATE)
- created_at: Timestamp
```

### Learning Profile
```python
- id: UUID (primary key)
- user_id: UUID (foreign key)
- preferred_output_mode: JSON
- preferred_explanation_style: JSON
- interaction_speed: Enum
- interface_preferences: JSON
- comprehension_history: JSON[]
```

### Session
```python
- id: UUID (primary key)
- user_id: UUID (foreign key)
- started_at: Timestamp
- ended_at: Timestamp (optional)
- guardian_input_count: Integer
- student_input_count: Integer
```

### Document
```python
- id: UUID (primary key)
- filename: String
- content_type: Enum
- grade: Integer
- syllabus: Enum
- subject: String
- chapter: String
- chunk_count: Integer
- status: Enum
```

### Progress
```python
- id: UUID (primary key)
- user_id: UUID (foreign key)
- topic_id: String
- topic_name: String
- comprehension_level: Float (0-1)
- times_reviewed: Integer
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_profile_service.py

# Run property-based tests only
pytest tests/test_property_*.py

# Run with verbose output
pytest -v
```

### Test Categories

| Category | Files | Description |
|----------|-------|-------------|
| Unit Tests | `test_*.py` | Specific functionality tests |
| Property Tests | `test_property_*.py` | Hypothesis-based property tests |

### Property-Based Tests

The project uses Hypothesis for property-based testing with 30 correctness properties defined in the design document. Key properties tested:

1. Document embedding round-trip
2. RAG retrieval relevance
3. Curriculum content categorization
4. Learning profile schema completeness
5. Multimodal input acceptance
6. Comprehension feedback flow
7. Guardian input separation
8. Progress recording accuracy

### Test Results

```
207 tests passed, 0 failed
14 of 30 correctness properties implemented (core functionality)
```

---

## Accessibility Features

### Visual Accommodations
- **Dark mode**: Reduces eye strain
- **High contrast**: Improves readability
- **Adjustable font sizes**: Small, medium, large
- **Muted color palette**: Calm, non-overwhelming
- **Reduced motion**: Disables animations

### Interaction Accommodations
- **Button-based responses**: Minimal typing required
- **Comprehension buttons**: Easy feedback mechanism
- **Explanation breakdowns**: Selectable parts
- **Suggested prompts**: Pre-written options
- **Voice input/output**: Alternative to text

### Sensory Accommodations
- **No sudden animations**: Predictable interface
- **No flashing elements**: Seizure-safe
- **Calm mode**: Immediate sensory reduction
- **Break features**: Breathing exercises, music
- **Emergency button**: Quick help access

### WCAG 2.1 AA Compliance
- Keyboard navigation support
- Screen reader compatibility
- Color contrast ratios
- Focus indicators
- Alt text for images

---

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes following code style
4. Write tests for new functionality
5. Run test suite
6. Submit pull request

### Code Style

- **Python**: Black formatter, Ruff linter
- **TypeScript**: ESLint with React rules
- **Commits**: Conventional commit messages

### Running Linters

```bash
# Python
black src/ tests/
ruff check src/ tests/

# TypeScript
cd frontend
npm run lint
```

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgments

- Designed with input from autism education specialists
- Built following EARS requirements patterns
- Tested using property-based testing methodology
- Accessibility features based on WCAG 2.1 guidelines

---

## Support

For issues, questions, or contributions, please open an issue on the repository.

**Made with 💙 for neurodivergent learners**
