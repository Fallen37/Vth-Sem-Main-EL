# Implementation Plan: Autism Science Tutor

## Overview

This plan implements a RAG-based AI science tutor for autistic students using Python. The implementation follows a modular approach, building core infrastructure first, then layering on accessibility features and guardian integration.

**Tech Stack:**
- Backend: Python with FastAPI
- Vector DB: ChromaDB
- Embeddings: sentence-transformers
- LLM: OpenAI API (or compatible)
- Database: SQLite (dev) / PostgreSQL (prod)
- Frontend: React with TypeScript (separate spec recommended)

## Tasks

- [x] 1. Project Setup and Core Infrastructure
  - [x] 1.1 Initialize Python project with FastAPI, dependencies (chromadb, sentence-transformers, openai, sqlalchemy, pydantic)
    - Create pyproject.toml or requirements.txt
    - Set up project structure: src/, tests/, config/
    - Configure environment variables handling
    - _Requirements: N/A (infrastructure)_

  - [x] 1.2 Create base data models with Pydantic and SQLAlchemy
    - User model with role enum (STUDENT, GUARDIAN, ADMIN)
    - LearningProfile model with all preference fields
    - Session and Message models
    - Document and Progress models
    - _Requirements: 2.1, 2.4, 10.2, 11.1_

  - [ ]* 1.3 Write property test for Learning Profile schema completeness
    - **Property 5: Learning Profile Schema Completeness**
    - **Validates: Requirements 2.1, 2.4**

- [ ] 2. Content Ingestion Pipeline
  - [x] 2.1 Implement ContentIngestionService
    - uploadDocument() - accept file and metadata
    - processDocument() - extract text, chunk, embed
    - Support PDF, DOCX, TXT, image files
    - Store embeddings in ChromaDB with metadata
    - _Requirements: 1.1, 12.4_

  - [x] 2.2 Write property test for document embedding round-trip

    - **Property 1: Document Embedding Round-Trip**
    - **Validates: Requirements 1.1**

  - [x] 2.3 Implement curriculum metadata handling
    - Grade level filtering (5-10)
    - Syllabus type filtering (CBSE, State)
    - Chapter and topic tagging
    - _Requirements: 1.3, 12.1_

  - [ ]* 2.4 Write property test for curriculum content categorization
    - **Property 3: Curriculum Content Categorization**
    - **Validates: Requirements 1.3, 12.1**

  - [ ]* 2.5 Write property test for content upload validation
    - **Property 30: Content Upload Validation**
    - **Validates: Requirements 12.4**

- [x] 3. RAG Engine Implementation
  - [x] 3.1 Implement RAGEngine core
    - retrieveChunks() - query ChromaDB with filters
    - query() - retrieve + generate with LLM
    - Configure similarity threshold for relevance
    - _Requirements: 1.2_

  - [x] 3.2 Write property test for RAG retrieval relevance

    - **Property 2: RAG Retrieval Relevance**
    - **Validates: Requirements 1.2**

  - [x] 3.3 Implement uncertainty handling
    - Detect low confidence scores
    - Generate uncertainty indicators in response
    - Suggest rephrasing when content insufficient
    - _Requirements: 1.4_

  - [ ]* 3.4 Write property test for uncertainty indication
    - **Property 4: Uncertainty Indication**
    - **Validates: Requirements 1.4**

  - [x] 3.5 Implement curriculum prioritization
    - Boost scores for matching grade/syllabus
    - Map questions to chapters/topics
    - Include source references in response
    - _Requirements: 12.2, 12.3_

  - [ ]* 3.6 Write property test for curriculum prioritization
    - **Property 28: Curriculum Prioritization**
    - **Validates: Requirements 12.2**

  - [ ]* 3.7 Write property test for question to curriculum mapping
    - **Property 29: Question to Curriculum Mapping**
    - **Validates: Requirements 12.3**

- [x] 4. Checkpoint - Core RAG System
  - Ensure all tests pass, ask the user if questions arise.

- [-] 5. Profile Service Implementation
  - [x] 5.1 Implement ProfileService
    - getProfile() / updateProfile()
    - recordInteraction() - log behavior patterns
    - getPreferredOutputMode() / getPreferredExplanationStyle()
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.2 Write property test for profile updates from interactions

    - **Property 6: Profile Updates from Interactions**
    - **Validates: Requirements 2.2**

  - [x] 5.3 Write property test for session preference application

    - **Property 7: Session Preference Application**
    - **Validates: Requirements 2.3**

- [x] 6. Chat Orchestrator Implementation
  - [x] 6.1 Implement ChatOrchestrator core
    - processMessage() - route input through RAG
    - Generate ChatResponse with all components
    - Include suggestedResponses for button options
    - _Requirements: 5.1, 5.5_

  - [x] 6.2 Write property test for button options

    - **Property 13: Button Options for Minimal Interaction**
    - **Validates: Requirements 5.1, 5.5**

  - [x] 6.3 Implement comprehension feedback flow
    - getComprehensionOptions() - return standard options
    - handleComprehensionFeedback() - process feedback
    - Generate breakdownParts on non-understanding
    - _Requirements: 5.2, 5.3, 7.1, 7.2_

  - [x] 6.4 Write property test for comprehension buttons

    - **Property 14: Comprehension Buttons After Explanations**
    - **Validates: Requirements 5.2, 7.1**

  - [x] 6.5 Write property test for breakdown on non-understanding

    - **Property 15: Breakdown on Non-Understanding**
    - **Validates: Requirements 5.3, 7.2**

  - [x] 6.6 Implement part selection handling
    - Handle clicks on ExplanationPart
    - Generate detailed explanation for selected part
    - _Requirements: 5.4, 7.3_

  - [x] 6.7 Write property test for part selection detail

    - **Property 16: Part Selection Triggers Detail**
    - **Validates: Requirements 5.4, 7.3**

  - [x] 6.8 Implement complexity adaptation
    - Track comprehension patterns per topic
    - Adjust explanation complexity based on history
    - _Requirements: 7.4_

  - [ ]* 6.9 Write property test for complexity adaptation
    - **Property 18: Complexity Adaptation**
    - **Validates: Requirements 7.4**

  - [x] 6.10 Implement output mode handling
    - getOutputModeOptions() - return available modes
    - changeOutputMode() - update session preference
    - Include options in every explanation response
    - _Requirements: 4.4, 4.5_

  - [ ]* 6.11 Write property test for output mode options
    - **Property 11: Output Mode Options in Responses**
    - **Validates: Requirements 4.4**

  - [ ]* 6.12 Write property test for output mode switching
    - **Property 12: Output Mode Switching**
    - **Validates: Requirements 4.5**

- [x] 7. Checkpoint - Chat System
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Multimodal Input Handler
  - [x] 8.1 Implement MultimodalInputHandler
    - processTextInput() - normalize and extract intent
    - processVoiceInput() - integrate STT service
    - processImageInput() - integrate vision service
    - processButtonClick() - handle button interactions
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 8.2 Write property test for multimodal input acceptance

    - **Property 8: Multimodal Input Acceptance**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [x] 9. Multimodal Output Renderer
  - [x] 9.1 Implement MultimodalOutputRenderer
    - renderText() - format text with style
    - renderAudio() - integrate TTS service
    - renderVisualAid() - generate/retrieve diagrams
    - renderComprehensionButtons() - create button group
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 9.2 Write property test for text output presence

    - **Property 9: Text Output Presence**
    - **Validates: Requirements 4.1**

  - [ ]* 9.3 Write property test for audio generation
    - **Property 10: Audio Generation**
    - **Validates: Requirements 4.2**

- [-] 10. Progress Tracker Implementation
  - [x] 10.1 Implement ProgressTracker
    - recordTopicCoverage() - log topic and comprehension
    - getProgress() - return child-friendly summary
    - getTopicsNeedingReview() - identify weak areas
    - getAchievements() - track milestones
    - _Requirements: 11.1, 11.4_

  - [x] 10.2 Write property test for progress recording

    - **Property 26: Progress Recording**
    - **Validates: Requirements 11.1**

  - [ ]* 10.3 Write property test for review topic identification
    - **Property 27: Review Topic Identification**
    - **Validates: Requirements 11.4**

- [x] 11. Checkpoint - Core Features Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Guardian Service Implementation
  - [x] 12.1 Implement GuardianService
    - linkGuardian() - connect guardian to student
    - recordGuardianInput() - log with source
    - getIndependenceMetrics() - calculate ratio
    - getSessionHistory() - return linked student data
    - sendAlert() - notify guardian
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 12.2 Write property test for guardian input separation

    - **Property 22: Guardian Input Separation**
    - **Validates: Requirements 10.2**

  - [ ]* 12.3 Write property test for independence ratio calculation
    - **Property 23: Independence Ratio Calculation**
    - **Validates: Requirements 10.3**

  - [ ]* 12.4 Write property test for guardian context in processing
    - **Property 24: Guardian Context in Processing**
    - **Validates: Requirements 10.4**

  - [ ]* 12.5 Write property test for guardian access control
    - **Property 25: Guardian Access Control**
    - **Validates: Requirements 10.5, 11.5**

- [x] 13. Calm Mode Service Implementation
  - [x] 13.1 Implement CalmModeService
    - activateBreak() - pause session, return break state
    - startBreathingExercise() - guided breathing patterns
    - playCalm Music() - audio stream for calming
    - triggerEmergencyAlert() - alert guardian, show calming content
    - endBreak() - resume session
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 13.2 Write property test for break mode session pause

    - **Property 20: Break Mode Session Pause**
    - **Validates: Requirements 9.2**

  - [x] 13.3 Write property test for emergency alert response

    - **Property 21: Emergency Alert Response**
    - **Validates: Requirements 9.6**

- [x] 14. Avatar State Management
  - [x] 14.1 Implement Avatar state service
    - Track interaction states (idle, listening, thinking, explaining)
    - Emit state changes for frontend
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 14.2 Write property test for avatar state consistency
    - **Property 17: Avatar State Consistency**
    - **Validates: Requirements 6.3**

- [x] 15. Interface Preferences Service
  - [x] 15.1 Implement interface customization
    - Dark mode toggle
    - Font size adjustment
    - Contrast and spacing settings
    - Persist to user profile
    - _Requirements: 8.2, 8.4_

  - [ ]* 15.2 Write property test for interface customization application
    - **Property 19: Interface Customization Application**
    - **Validates: Requirements 8.4**

- [x] 16. API Layer Implementation
  - [x] 16.1 Implement REST API endpoints
    - /auth - authentication endpoints
    - /chat - message processing
    - /profile - profile management
    - /content - document upload/management
    - /progress - progress tracking
    - /guardian - guardian features
    - /calm - break and emergency features
    - _Requirements: All_

  - [x] 16.2 Implement WebSocket for real-time chat
    - Connection management
    - Message streaming
    - Avatar state updates
    - _Requirements: 6.3_

- [x] 17. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 30 correctness properties are covered
  - Run full integration test suite

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Frontend implementation (React) recommended as separate spec
