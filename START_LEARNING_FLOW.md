# What Happens When You Press "Start Learning"

## Complete User Journey

### Phase 1: Authentication (First Time Only)

**User Action:** User visits the app for the first time

1. **Registration Page** (`/register`)
   - User enters: Email, Name, Grade (5-10), Syllabus (CBSE/State)
   - Clicks "Create Account"
   - Frontend sends: `POST /auth/register` with user data
   - Backend creates user in database with UUID as ID
   - Backend returns: `{ token: user_id, user: {...} }`
   - Frontend stores token in localStorage
   - Frontend stores user data in localStorage
   - User is redirected to `/dashboard`

2. **Login Page** (`/login`) - For returning users
   - User enters: Email
   - Clicks "Sign In"
   - Frontend sends: `POST /auth/login` with email
   - Backend finds user in database
   - Backend returns: `{ token: user_id, user: {...} }`
   - Frontend stores token in localStorage
   - User is redirected to `/dashboard`

### Phase 2: Dashboard

**User Action:** User sees dashboard and clicks "Start Learning 💬" button

1. **Dashboard Page** (`/dashboard`)
   - Shows welcome message: "Welcome back, [Name]! 👋"
   - Shows progress summary (topics covered, streak, achievements)
   - Shows "Science Buddy" card with "Start Learning 💬" button
   - User clicks the button
   - Frontend navigates to `/chapters`

### Phase 3: Chapter Selection

**User Action:** User is now on the Chapter Index page

1. **ChapterIndex Page** (`/chapters`)
   - Page loads
   - Component mounts and useEffect runs
   - Frontend calls: `GET /content/chapters/{grade}`
   - Example: `GET /content/chapters/8` (for Grade 8 student)
   - Frontend includes auth token in header: `Authorization: Bearer {user_id}`

2. **Backend Processing**
   - Backend receives request
   - Validates auth token (extracts user ID)
   - Queries database: `SELECT DISTINCT chapter FROM documents WHERE grade = 8`
   - Finds 18 chapters for Grade 8:
     - CELL — STRUCTURE AND FUNCTIONS
     - CHEMICAL EFFECTS OF ELECTRIC CURRENT
     - COAL AND PETROLEUM
     - COMBUSTION AND FLAME
     - CONSERVATION OF PLANTS AND ANIMALS
     - CROP PRODUCTION AND MANAGEMENT
     - FORCE AND PRESSURE
     - FRICTION
     - LIGHT
     - MATERIALS — METALS AND NON-METALS
     - MICROORGANISMS — FRIEND AND FOE
     - POLLUTION OF AIR AND WATER
     - REACHING THE AGE OF ADOLESCENCE
     - REPRODUCTION IN ANIMALS
     - SOME NATURAL PHENOMENA
     - SOUND
     - STARS AND THE SOLAR SYSTEM
     - SYNTHETIC FIBRES AND PLASTICS
   - Backend returns: `{ grade: 8, chapters: [...] }`

3. **Frontend Display**
   - ChapterIndex receives chapter list
   - Displays header: "📚 Grade 8 Chapters"
   - Displays chapter buttons in a list
   - Each button shows:
     - Chapter number (1, 2, 3, ...)
     - Chapter name
     - Icon: ✓ (if visited before) or → (if new)
   - User can now select a chapter

### Phase 4: Chapter Selection & Session Creation

**User Action:** User clicks on a chapter button (e.g., "FORCE AND PRESSURE")

1. **Frontend Processing**
   - `handleChapterSelect("FORCE AND PRESSURE")` is called
   - Frontend checks localStorage for existing session
   - Key: `sessionMap_{user_id}`
   - Value: `{ "FORCE AND PRESSURE": "session_id_123", ... }`

2. **If New Chapter (First Time)**
   - No session found in localStorage
   - Frontend calls: `POST /chat/session`
   - Backend creates new session in database
   - Backend returns: `{ session_id: "0f75fb3f-e02e-4084-8c33-545f1f49324c" }`
   - Frontend stores session ID in localStorage
   - Frontend navigates to: `/chat?chapter=FORCE%20AND%20PRESSURE&session=0f75fb3f-e02e-4084-8c33-545f1f49324c`

3. **If Returning to Chapter (Visited Before)**
   - Session found in localStorage
   - Frontend retrieves session ID
   - Frontend navigates to: `/chat?chapter=FORCE%20AND%20PRESSURE&session={existing_session_id}`

### Phase 5: Chat Page Initialization

**User Action:** Chat page loads

1. **Chat Page** (`/chat?chapter=...&session=...`)
   - Component mounts
   - useEffect runs
   - Frontend extracts query parameters:
     - `chapter = "FORCE AND PRESSURE"`
     - `sessionId = "0f75fb3f-e02e-4084-8c33-545f1f49324c"`

2. **Load Previous Messages (If Resuming)**
   - Frontend calls: `GET /chat/session/{sessionId}/messages`
   - Backend queries database for all messages in session
   - Backend returns: `{ messages: [...] }`
   - If messages exist:
     - Frontend displays all previous messages
     - Chat resumes from where user left off
     - Skip to Phase 6

3. **Initialize New Session (If First Time)**
   - No previous messages found
   - Frontend calls: `GET /content/chapters/{grade}/{chapter}`
   - Example: `GET /content/chapters/8/FORCE%20AND%20PRESSURE`
   - Backend queries database for topics in this chapter
   - Backend returns: `{ grade: 8, chapter: "FORCE AND PRESSURE", topics: [] }`
   - Note: Topics are empty because PDFs don't have topic extraction yet

4. **Display Welcome Message**
   - Frontend creates welcome message from AI:
     ```
     "Great! Let's explore 'FORCE AND PRESSURE'. I've identified 0 key topics in this chapter. 
     We'll go through them one by one. Let me start with the first topic: Introduction
     
     Let me explain this to you..."
     ```
   - Frontend displays message in chat

5. **Request AI Explanation**
   - Frontend calls: `POST /chat/message`
   - Sends: 
     ```json
     {
       "session_id": "0f75fb3f-e02e-4084-8c33-545f1f49324c",
       "content": "Please explain the topic 'Force and Pressure' from the chapter 'FORCE AND PRESSURE' in a way suitable for a Grade 8 student. Start with the basics and build up. Use examples from the textbook if possible.",
       "input_type": "TEXT"
     }
     ```

### Phase 6: AI Processing & Response

**Backend Processing:**

1. **RAG (Retrieval-Augmented Generation)**
   - Backend receives message
   - Extracts query: "Please explain Force and Pressure..."
   - Converts query to embeddings using sentence-transformers
   - Searches FAISS vector store for similar content
   - Finds relevant chunks from "FORCE AND PRESSURE.pdf"
   - Example chunks:
     - "Force is a push or pull that can change the motion of an object"
     - "Pressure is the force applied per unit area"
     - "SI unit of force is Newton (N)"
     - "SI unit of pressure is Pascal (Pa)"

2. **LLM Generation**
   - Backend sends to Google Gemini API:
     ```
     Context from textbook:
     [Retrieved chunks about force and pressure]
     
     User query: Please explain Force and Pressure for Grade 8 student
     
     Generate a clear, step-by-step explanation suitable for a Grade 8 student.
     ```
   - Google Gemini generates response:
     ```
     "Hello there! I'm here to help you understand 'Force and Pressure' in a clear, 
     step-by-step way. We'll use your textbook content and make sure everything is easy to follow.
     
     Let's start with **Force**:
     - Force is a push or pull that can change the motion of an object
     - The SI unit of force is Newton (N)
     - Examples: pushing a ball, pulling a rope, gravity pulling objects down
     
     Now let's talk about **Pressure**:
     - Pressure is the force applied per unit area
     - The SI unit of pressure is Pascal (Pa)
     - Formula: Pressure = Force / Area
     - Examples: A sharp knife cuts better than a dull one because it applies force over a smaller area
     
     Do you understand these concepts so far?"
     ```

3. **Save to Database**
   - Backend saves user message to database
   - Backend saves AI response to database
   - Both linked to session ID

4. **Return Response**
   - Backend returns: `{ message: "Hello there! I'm here to help..." }`

### Phase 7: Chat Interaction

**Frontend Display:**

1. **Display AI Response**
   - Frontend receives AI message
   - Creates message object:
     ```json
     {
       "id": "msg_123",
       "role": "ai",
       "content": "Hello there! I'm here to help...",
       "timestamp": "2026-01-19T20:30:00Z",
       "emotion": "neutral"
     }
     ```
   - Displays message in chat bubble with AI avatar (🤖)

2. **Display Response Buttons**
   - Frontend displays three buttons:
     - "I Understand" (👍) - User understood the topic
     - "I'm Confused" (😕) - User needs simpler explanation
     - "Tell Me More" (🔍) - User wants more details

3. **User Interaction**
   - User clicks one of the buttons
   - Different actions based on button:

   **If "I Understand":**
   - Move to next topic
   - Repeat Phase 6 with next topic
   - Continue until all topics covered

   **If "I'm Confused":**
   - Frontend calls: `POST /chat/message`
   - Sends: `"I'm confused about 'Force and Pressure'. Can you break it down into simpler parts?"`
   - Backend generates simpler explanation
   - Display new response with updated buttons

   **If "Tell Me More":**
   - Frontend calls: `POST /chat/message`
   - Sends: `"Tell me more about 'Force and Pressure'. Include more examples and details."`
   - Backend generates detailed explanation
   - Display new response with updated buttons

### Phase 8: Chapter Completion

**When All Topics Are Covered:**

1. **Completion Message**
   - Frontend displays:
     ```
     "🎓 Fantastic! You've completed all topics in this chapter! 
     You've learned about:
     1. Force
     2. Pressure
     3. Applications of Force and Pressure
     
     Would you like to review any topic, or move to another chapter?"
     ```

2. **Completion Options**
   - "Review a Topic" (🔄) - Select a topic to review
   - "Next Chapter" (📚) - Go back to chapter index
   - "Go Home" (🏠) - Return to dashboard

3. **User Choice**
   - If "Review a Topic": Show topic selection buttons
   - If "Next Chapter": Navigate back to `/chapters`
   - If "Go Home": Navigate to `/dashboard`

## Data Flow Summary

```
User clicks "Start Learning"
    ↓
Dashboard navigates to /chapters
    ↓
ChapterIndex loads chapters from API
    ↓
User selects chapter
    ↓
Frontend creates session (if new) or retrieves existing session
    ↓
Navigate to /chat with chapter and session ID
    ↓
Chat page loads previous messages (if resuming) or initializes new session
    ↓
Frontend sends message to AI
    ↓
Backend uses RAG to find relevant content
    ↓
Backend calls Google Gemini API to generate explanation
    ↓
Backend saves messages to database
    ↓
Frontend displays AI response with interaction buttons
    ↓
User clicks button (I Understand / I'm Confused / Tell Me More)
    ↓
Process repeats for next topic or action
```

## Key Features

1. **Session Persistence**
   - Each chapter gets its own session
   - Sessions are stored in database
   - Session IDs are stored in localStorage for quick access
   - User can resume a chapter later and see all previous messages

2. **RAG (Retrieval-Augmented Generation)**
   - Uses sentence-transformers to convert text to embeddings
   - Uses FAISS vector store for semantic search
   - Retrieves relevant content from PDFs
   - Passes context to LLM for better responses

3. **Neuro-Inclusive Design**
   - Soft colors and minimal animations
   - Clear visual hierarchy with emojis
   - Button-based responses (no typing required)
   - One topic at a time (not overwhelming)
   - Emotion indicators on AI messages

4. **Progressive Learning**
   - Topics are presented one at a time
   - User must confirm understanding before moving to next topic
   - Option to get simpler explanation or more details
   - Can review topics after completion

## Database Schema

**Users Table**
- id (UUID)
- email
- name
- grade (5-10)
- role (STUDENT, GUARDIAN, ADMIN)
- syllabus (CBSE, STATE)
- created_at
- updated_at

**Sessions Table**
- id (UUID)
- user_id (FK to Users)
- chapter
- created_at
- updated_at

**Messages Table**
- id (UUID)
- session_id (FK to Sessions)
- role (user, ai)
- content
- timestamp

**Documents Table**
- id (UUID)
- filename
- grade
- chapter
- topic
- content
- status (PENDING, PROCESSING, COMPLETED)
- uploaded_at
- processed_at

## API Endpoints Used

1. `POST /auth/register` - Register new user
2. `POST /auth/login` - Login user
3. `GET /content/chapters/{grade}` - Get chapters for grade
4. `GET /content/chapters/{grade}/{chapter}` - Get topics for chapter
5. `POST /chat/session` - Create new chat session
6. `POST /chat/message` - Send message to AI
7. `GET /chat/session/{sessionId}/messages` - Get session messages

## Performance Considerations

- Chapter index loads instantly (just fetches chapter names, not full content)
- Chat messages are cached in localStorage for quick access
- RAG search is fast due to FAISS vector store
- Google Gemini API calls are the main bottleneck (typically 2-5 seconds)
- Database queries are optimized with proper indexing

## Error Handling

- If API call fails, user sees error message
- If AI generation fails, fallback message is shown
- If database is unavailable, user is redirected to error page
- All errors are logged for debugging
