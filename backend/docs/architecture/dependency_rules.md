# Dependency Rules

Frontend

↓

API

↓

Tutor Platform

↓

Teacher Platform

↓

Knowledge Platform

↓

AI Platform

↓

Infrastructure

-------------------------------------------------

Allowed

Teacher Platform

↓

Knowledge Platform

Teacher Platform

↓

Student Platform

Tutor Platform

↓

Teacher Platform

Tutor Platform

↓

Knowledge Platform

Knowledge Factory

↓

Infrastructure

-------------------------------------------------

Not Allowed

Knowledge Platform

↓

Teacher Platform

Student Platform

↓

Teacher Platform

Infrastructure

↓

Teacher Platform

Prompt Builder

↓

Firestore

Teacher Brain

↓

Cloud Storage

-------------------------------------------------

Reason

Dependencies should always point downward.

Lower-level modules should never know about higher-level modules.