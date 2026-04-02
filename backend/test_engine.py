#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.tutor_brain.tutor_engine import TutorEngine

# Test the tutor engine
engine = TutorEngine()
response = engine.process("test123", "hi")
print("Response:", response)
print("Session state:", engine.sessions["test123"].step)