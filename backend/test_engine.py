#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.tutor_brain.tutor_engine import TutorEngine

print("Starting test")

# Test the tutor engine
try:
    print("Importing TutorEngine")
    from backend.app.tutor_brain.tutor_engine import TutorEngine
    print("Creating engine")
    engine = TutorEngine()
    print("Processing message")
    response = engine.process("test123", "hi")
    print("Response:", response)
    print("Session state:", engine.sessions["test123"].step)
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()