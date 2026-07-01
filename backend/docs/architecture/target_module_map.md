# MathVerse Target Module Map

Version: MVP v1.0

Purpose

This document maps the current codebase to the future MathVerse architecture.

During MVP development, existing files will remain where they are.

New development must follow this mapping.

No large-scale refactoring will be performed until after the MVP.

----------------------------------------------------------

Teacher Platform

Current Modules

app/services/teacher_brain.py

app/services/teacher_observer.py

app/services/teacher_reasoning.py

app/services/strategy_chooser.py

app/services/teacher_evaluator.py

app/services/prompt_builder.py

app/services/memory_updater.py

Future Platform

teacher/

----------------------------------------------------------

Tutor Platform

Current Modules

app/services/tutor_context.py

app/services/tutor_engine.py

app/services/runtime.py

app/services/lesson_planner.py

Future Platform

tutor/

----------------------------------------------------------

Student Platform

Current Modules

student_session_manager.py

student_session_model.py

teacher_memory.py

Future Platform

student/

----------------------------------------------------------

Knowledge Platform

Current Modules

curriculum.py

question_repository.py

pdf_ingestion_service.py

Future Platform

knowledge/

----------------------------------------------------------

Assessment Platform

Current Modules

teacher_evaluator.py

Future Platform

assessment/

----------------------------------------------------------

Analytics Platform

Current Modules

(progress tracking modules)

Future Platform

analytics/

----------------------------------------------------------

AI Platform

Current Modules

ai_gateway.py

Future Platform

ai/

----------------------------------------------------------

Infrastructure Platform

Current Modules

Firestore

Cloud Storage

Terraform

Cloud Functions

Future Platform

infrastructure/

----------------------------------------------------------

Future Rule

All NEW services must be created under their future platform.

Existing services will gradually migrate after MVP.