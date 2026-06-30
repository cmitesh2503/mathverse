
# MathVerse AI - Enterprise Architecture
Version: 1.0
Status: Living Architecture Document

> Single source of truth for MathVerse architecture.

## 1. Vision
MathVerse is an AI JEE Mathematics teacher designed to behave like an experienced Indian coaching teacher—not a chatbot.

Teaching lifecycle:
Observe → Think → Choose Strategy → Teach → Evaluate → Adapt → Repeat

## 2. Product Philosophy
- Teacher-first.
- Adaptive instruction.
- Memory-driven teaching.
- Modular, production-ready architecture.

## 3. High-Level Architecture
Frontend (React/Vite)
- Upload
- Chat
- Voice (future)
- Whiteboard (future)

Backend (FastAPI)
- TutorContext
- TeacherBrain
- TeacherObserver
- StrategyChooser
- PromptBuilder
- AI Gateway
- MemoryExtractor
- MemoryUpdater
- StudentSessionManager

Persistence
- Firestore
- Chat history
- Future StudentProfile

## 4. Core Teaching Pipeline
Student
→ TutorContext
→ TeacherBrain
→ TeacherObserver
→ StrategyChooser
→ PromptBuilder
→ Gemini
→ MemoryExtractor
→ MemoryUpdater
→ TeacherMemory

## 5. Responsibilities
### TeacherBrain
Coordinates services only.
Never owns prompts or persistence.

### TutorContext
Loads question, solution, history and builds conversation.

### TeacherObserver
Detects:
- confused
- asks_why
- needs_hint
- needs_example
- needs_whiteboard
- understood

### StrategyChooser
Chooses:
- EXPLAIN
- SIMPLIFY
- EXAMPLE
- HINT
- WHITEBOARD
- CHECK_UNDERSTANDING

### PromptBuilder
Owns every prompt.

### MemoryExtractor
Extracts:
- current_topic
- explained_topics
- misconceptions
- teaching_methods_used
- learning_status

### MemoryUpdater
Updates TeacherMemory after every AI response.

## 6. Student Session
Tracks:
- question_id
- chapter
- followups
- explanations
- hints
- checks
- confidence
- understanding
- TeacherMemory

## 7. Teacher Memory
Stores:
- current_topic
- explained_topics
- misconceptions
- teaching_methods_used
- learning_status
- student_questions
- teacher_answers
- last_student_question
- last_teacher_response

## 8. Memory Model
TeacherMemory = session only.
StudentProfile = persistent (future, Firestore).

## 9. Prompt Strategies
EXPLAIN
SIMPLIFY
EXAMPLE
HINT
WHITEBOARD
CHECK_UNDERSTANDING

## 10. Development Principles
- One responsibility per service.
- TeacherBrain is orchestrator only.
- Build incrementally.
- Never break working code.
- Review architecture before coding.

## 11. Completed
- TutorContext
- TeacherBrain
- StudentSession
- StudentSessionManager
- TeacherMemory
- MemoryExtractor
- MemoryUpdater
- TeacherObserver
- StrategyChooser
- PromptBuilder

## 12. Next
Day 9:
TeacherReasoner

Then:
TeachingEvaluator
StudentProfile
Whiteboard Engine
Voice Tutor
Knowledge Graph

## 13. Long-term Roadmap
Phase 1 Adaptive Tutor
Phase 2 Adaptive Teacher
Phase 3 Whiteboard AI
Phase 4 Voice Tutor
Phase 5 Student Profile
Phase 6 Curriculum Planner
Phase 7 Exam Simulator
Phase 8 Multi-Agent Teacher

## 14. Rules for Future Development
1. Preserve teaching lifecycle.
2. Never redesign architecture without discussion.
3. Keep services focused.
4. Update this document whenever architecture changes.
