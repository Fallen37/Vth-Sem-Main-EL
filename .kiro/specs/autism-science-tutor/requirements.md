# Requirements Document

## Introduction

An AI-powered science tutor designed specifically for autistic students aged 10-16 (Indian grades 5-10). The system uses Retrieval-Augmented Generation (RAG) to provide personalized, curriculum-aligned science education with extensive accommodations for diverse learning needs, including non-verbal students and those requiring guardian assistance.

## Glossary

- **Tutor_AI**: The RAG-based conversational AI system that delivers science education
- **Student**: An autistic learner aged 10-16 using the system
- **Guardian**: A parent, teacher, or caregiver who assists a student during sessions
- **Learning_Profile**: Stored preferences and behavioral patterns for a student
- **Content_Store**: Vector database containing embedded educational materials
- **Session**: A single interaction period between a student and the Tutor_AI
- **Comprehension_Check**: Interactive feedback mechanism to gauge student understanding
- **Calm_Mode**: A sensory-reduced interface state for overwhelmed students
- **Avatar**: Visual representation of the AI tutor or student in the interface

## Requirements

### Requirement 1: RAG-Based Knowledge System

**User Story:** As a student, I want the AI to answer my science questions using my actual textbooks and curriculum materials, so that I learn content relevant to my exams.

#### Acceptance Criteria

1. WHEN educational materials are uploaded, THE Content_Store SHALL convert them into embeddings and store them for retrieval
2. WHEN a student asks a question, THE Tutor_AI SHALL retrieve relevant content from the Content_Store and generate a contextual response
3. THE Tutor_AI SHALL support Indian CBSE and State syllabus content for grades 5-10
4. WHEN retrieved content is insufficient, THE Tutor_AI SHALL indicate uncertainty rather than hallucinate information

### Requirement 2: Adaptive Learning Profile

**User Story:** As a student, I want the AI to remember my preferences and learning patterns, so that it adapts to how I learn best over time.

#### Acceptance Criteria

1. THE Learning_Profile SHALL track student preferences including output mode, interaction speed, and comprehension patterns
2. WHILE a student interacts with the system, THE Tutor_AI SHALL continuously update the Learning_Profile based on observed behavior
3. WHEN a new session begins, THE Tutor_AI SHALL apply stored preferences from the Learning_Profile automatically
4. THE Learning_Profile SHALL store preferred explanation styles (examples, diagrams, step-by-step)

### Requirement 3: Multimodal Input

**User Story:** As a student, I want to communicate with the AI through text, voice, or pictures, so that I can use whatever method is easiest for me.

#### Acceptance Criteria

1. THE Tutor_AI SHALL accept text input from the student
2. THE Tutor_AI SHALL accept voice input and transcribe it for processing
3. THE Tutor_AI SHALL accept image input (photos of textbook pages, handwritten questions, diagrams)
4. WHEN multiple input modes are available, THE Student SHALL be able to switch between them freely

### Requirement 4: Multimodal Output

**User Story:** As a student, I want to receive explanations in different formats, so that I can understand concepts in the way that works best for me.

#### Acceptance Criteria

1. THE Tutor_AI SHALL provide text-based explanations
2. THE Tutor_AI SHALL provide voice/audio explanations
3. THE Tutor_AI SHALL generate or retrieve relevant diagrams and visual aids
4. WHEN explaining a concept, THE Tutor_AI SHALL offer output mode options (more examples, diagram, slower pace, simpler words)
5. THE Student SHALL be able to change output mode at any time during a session

### Requirement 5: Non-Verbal Student Support

**User Story:** As a non-verbal student, I want to interact with the AI using minimal actions like button clicks, so that I can learn without needing to type or speak.

#### Acceptance Criteria

1. THE Tutor_AI SHALL provide clickable button options for common responses
2. WHEN explaining a concept, THE Tutor_AI SHALL display comprehension buttons (Understood, Partially Understood, Not Understood)
3. WHEN a student indicates partial or no understanding, THE Tutor_AI SHALL break the explanation into selectable parts
4. THE Student SHALL be able to click on specific parts of an explanation to request deeper coverage
5. THE Tutor_AI SHALL provide suggested prompts and response options to minimize required input

### Requirement 6: Avatar System

**User Story:** As a student, I want to see a friendly avatar representing the AI, so that the experience feels more engaging and less like a basic chatbot.

#### Acceptance Criteria

1. THE Tutor_AI SHALL display an avatar representing the AI tutor
2. THE Student SHALL have an avatar representing themselves in the interface
3. THE Avatar SHALL provide visual feedback during interactions (listening, thinking, explaining states)

### Requirement 7: Comprehension Feedback Loop

**User Story:** As a student, I want to tell the AI how well I understood something, so that it can adjust its teaching approach.

#### Acceptance Criteria

1. WHEN the Tutor_AI completes an explanation, THE System SHALL prompt for comprehension feedback
2. WHEN a student selects "Not Understood", THE Tutor_AI SHALL offer to break down the concept into smaller parts
3. WHEN a student selects a specific part they struggled with, THE Tutor_AI SHALL provide an in-depth explanation of that part
4. THE Tutor_AI SHALL adjust explanation complexity based on comprehension feedback patterns

### Requirement 8: Sensory-Friendly Interface

**User Story:** As a student who is sensitive to sensory overload, I want a calm and clean interface, so that I can focus on learning without distraction.

#### Acceptance Criteria

1. THE System SHALL provide a minimalist interface with muted colors
2. THE System SHALL provide a dark mode option
3. THE System SHALL avoid sudden animations, flashing elements, or loud sounds
4. THE Student SHALL be able to customize interface elements (font size, contrast, spacing)

### Requirement 9: Calm Mode and Breaks

**User Story:** As a student who may become overwhelmed, I want quick access to calming features, so that I can take a break and regulate myself.

#### Acceptance Criteria

1. THE System SHALL provide a visible "Take a Break" button accessible at all times
2. WHEN the student activates break mode, THE System SHALL pause the learning session
3. THE System SHALL offer a guided breathing exercise option
4. THE System SHALL offer calming background music during breaks
5. THE System SHALL provide an "I need help" emergency button for panic situations
6. WHEN the emergency button is pressed, THE System SHALL display calming content and optionally alert the guardian

### Requirement 10: Guardian Assistance Mode

**User Story:** As a guardian, I want to provide input on behalf of or alongside my student, so that I can help them when they need support.

#### Acceptance Criteria

1. THE System SHALL provide a separate input section for guardian contributions
2. THE System SHALL log guardian inputs separately from student inputs
3. THE System SHALL track the ratio of guardian assistance to student independence over time
4. WHEN a guardian provides input, THE Tutor_AI SHALL acknowledge the source in its response context
5. THE Guardian SHALL be able to view session history and student progress

### Requirement 11: Progress Tracking

**User Story:** As a student, I want to see my learning progress in a friendly way, so that I feel motivated without feeling pressured.

#### Acceptance Criteria

1. THE System SHALL track topics covered and comprehension levels
2. THE System SHALL display progress using child-friendly visualizations (not clinical charts)
3. THE System SHALL celebrate achievements with positive, non-overwhelming feedback
4. THE System SHALL identify topics that need review based on comprehension patterns
5. THE Guardian SHALL be able to view detailed progress reports

### Requirement 12: Curriculum Alignment

**User Story:** As a student, I want to learn science topics that match my school syllabus, so that the AI helps me with my actual schoolwork.

#### Acceptance Criteria

1. THE Content_Store SHALL be organized by grade level (5-10) and syllabus type (CBSE, State)
2. WHEN a student's grade and syllabus are set, THE Tutor_AI SHALL prioritize content from that curriculum
3. THE Tutor_AI SHALL be able to map questions to specific chapters and topics in the curriculum
4. THE System SHALL support uploading additional curriculum materials (textbooks, past papers, notes)
