# MathVerse Module Ownership

Version: MVP v1.0

Purpose

This document defines the ownership and responsibilities of every major module in the MathVerse platform.

Every future feature must belong to one module.

No module should have multiple unrelated responsibilities.

---

# 1. Teacher Platform

Purpose

Responsible for teaching decisions.

Responsible For

- Observe student behaviour
- Analyze understanding
- Decide teaching strategy
- Evaluate learning progress
- Build AI teaching prompts
- Update teacher memory

Modules

app/services/teacher_brain.py

app/services/teacher_observer.py

app/services/teacher_reasoning.py

app/services/strategy_chooser.py

app/services/teacher_evaluator.py

app/services/prompt_builder.py

app/services/memory_updater.py

Should NOT

- Read PDFs
- Parse curriculum
- Access Cloud Storage
- Generate curriculum
- Store documents

---

# 2. Tutor Platform

Purpose

Runs the tutoring session.

Responsible For

- Create Tutor Context
- Manage tutoring flow
- Coordinate Teacher Brain
- Coordinate Gemini
- Return responses
- Manage lesson lifecycle

Modules

app/services/tutor_context.py

app/services/tutor_engine.py

app/services/lesson_planner.py

app/services/runtime.py

Should NOT

- Generate analytics
- Parse PDFs
- Maintain curriculum

---

# 3. Student Platform

Purpose

Maintain student state.

Responsible For

- Session management
- Student memory
- Confidence tracking
- Understanding tracking
- Learning history
- Progress

Modules

student_session_manager.py

student_session_model.py

teacher_memory.py

Should NOT

- Generate prompts
- Call Gemini
- Read curriculum

---

# 4. Knowledge Platform

Purpose

Own all educational knowledge.

Responsible For

- Curriculum
- Chapters
- Concepts
- Formula Sheets
- Teacher Scripts
- Whiteboard Scripts
- Revision Notes
- Cheat Sheets
- Question Metadata

Future Modules

curriculum_service.py

knowledge_graph.py

concept_service.py

formula_service.py

teacher_script_service.py

whiteboard_service.py

Should NOT

- Talk to Gemini
- Teach students
- Store sessions

---

# 5. Knowledge Factory

Purpose

Convert educational documents into structured knowledge.

Responsible For

- PDF ingestion
- OCR
- Gemini extraction
- Validation
- Graph building
- Firestore loading

Future Pipeline

Cloud Storage

↓

Cloud Run Function

↓

Knowledge Factory

↓

Firestore

↓

Knowledge Graph

Should NOT

- Teach students
- Generate tutoring responses

---

# 6. Assessment Platform

Purpose

Measure learning.

Responsible For

- Practice evaluation
- Quiz evaluation
- Mini tests
- Learning assessment
- Weak concept detection

Future Modules

assessment_engine.py

evaluation_engine.py

practice_engine.py

---

# 7. Analytics Platform

Purpose

Generate learning analytics.

Responsible For

- Daily study time
- Accuracy
- Retention
- Weak topics
- Learning trends

Future Modules

analytics_service.py

progress_dashboard.py

recommendation_engine.py

---

# 8. AI Platform

Purpose

Provide AI capabilities.

Responsible For

- Vertex AI
- Gemini
- Embeddings
- Prompt execution
- Model configuration

Modules

ai_gateway.py

Future Modules

embedding_service.py

model_router.py

Should NOT

- Own curriculum
- Own teaching strategy

---

# 9. Infrastructure Platform

Purpose

Infrastructure and deployment.

Responsible For

- GKE
- Firestore
- Cloud Storage
- Cloud Run
- Terraform
- IAM
- Secret Manager
- Monitoring

Should NOT

- Implement business logic

---

# Architecture Rule

Every new feature must belong to exactly one platform.

If a feature does not clearly belong to one platform, the architecture should be reviewed before implementation.

No business logic should exist inside API routes.

# Ownership Matrix

| Platform | Owns | Never Owns |
|-----------|------|------------|
| Teacher | Teaching decisions | Infrastructure |
| Tutor | Tutoring workflow | Curriculum |
| Student | Student state | AI prompts |
| Knowledge | Educational content | Teaching logic |
| Knowledge Factory | Data ingestion | Student sessions |
| Assessment | Tests & evaluation | Curriculum |
| Analytics | Reports & insights | Teaching |
| AI | Gemini & Vertex AI | Business rules |
| Infrastructure | Cloud resources | Business logic |