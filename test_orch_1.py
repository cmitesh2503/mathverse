import sys
import os

# --- SELF-HEALING PATH INJECTION ---
# This ensures Python can find 'app' and 'backend' packages automatically
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
# -----------------------------------

import asyncio
# These imports will now work correctly due to the injection above
from app.agents.orchestrator import Orchestrator
from app.models.session import StudentSession

async def run_validation():
    print("--- Starting Concurrency-Ready Validation ---")
    orchestrator = Orchestrator()
    session_id = "test-session-123"
    
    # Test 1: Teaching Phase
    orchestrator.sessions[session_id] = StudentSession(
        session_id=session_id,
        active_phase="teaching"
    ) 
    
    target = await orchestrator.route_message(session_id, "Can you explain circles?")
    assert target == "tutor_agent", f"Failed Teaching Route. Got: {target}"
    print("✅ Test 1 Passed: Teaching routes to Tutor Agent")

    # Test 2: Practice Phase (Asking for help)
    orchestrator.sessions[session_id].active_phase = "practice"
    
    target = await orchestrator.route_message(session_id, "I need a hint for step 2")
    assert target == "tutor_agent", f"Failed Hint Route. Got: {target}"
    print("✅ Test 2 Passed: Hint requests route to Tutor Agent")

    # Test 3: Practice Phase (Submitting answer)
    target = await orchestrator.route_message(session_id, "My final answer is 42")
    assert target == "diagnostic_agent", f"Failed Diagnostic Route. Got: {target}"
    print("✅ Test 3 Passed: Answer submissions route to Diagnostic Agent")

    print("🎉 All Validations Passed!")

if __name__ == "__main__":
    asyncio.run(run_validation())